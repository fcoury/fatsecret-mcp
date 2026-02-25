from __future__ import annotations

import difflib
from typing import Any

from app.models.schemas import IntencionNormalizada
from .servicio_contexto_fatsecret import ServicioContextoFatSecret
from .servicio_ejecucion_fatsecret import ServicioEjecucionFatSecret
from .servicio_normalizacion_nutricion import normalizar_texto_base, plegar_acentos


def _asegurar_lista(valor: Any) -> list[Any]:
    if valor is None:
        return []
    if isinstance(valor, list):
        return valor
    return [valor]


class ServicioResolucionNutricion:
    def __init__(self, servicio_contexto: ServicioContextoFatSecret, servicio_ejecucion: ServicioEjecucionFatSecret) -> None:
        self._contexto = servicio_contexto
        self._ejecutor = servicio_ejecucion

    def resolver(self, intencion: IntencionNormalizada) -> dict[str, Any]:
        if not intencion.parser_valid:
            return self._plan_bloqueado(intencion, "PARSER_SCHEMA_MISMATCH", "La intención contiene errores de parseo")
        if intencion.intent in {"log_combo", "log_combo_modified"}:
            return self._resolver_combo(intencion)
        if intencion.intent == "log_single_food_grams":
            return self._resolver_alimento_en_gramos(intencion)
        return self._plan_bloqueado(intencion, "PARSER_UNKNOWN_INTENT", "Intent no soportado")

    def _resolver_combo(self, intencion: IntencionNormalizada) -> dict[str, Any]:
        comidas = self._contexto.obtener_comidas_guardadas()
        coincidencias = self._resolver_combo_por_nombre(comidas, intencion.combo_ref_normalized or "")
        if not coincidencias:
            return self._plan_bloqueado(intencion, "RESOLVER_COMBO_NOT_FOUND", f"No se encontró combo: {intencion.combo_ref_raw}")
        if len(coincidencias) > 1 and coincidencias[0]["score"] - coincidencias[1]["score"] < 0.05:
            return self._plan_bloqueado(
                intencion,
                "RESOLVER_COMBO_AMBIGUOUS",
                "Combo ambiguo",
                extras={"combo_candidates": coincidencias[:3]},
            )

        combo = coincidencias[0]
        detalles = self._ejecutor.ejecutar_herramienta("get_meal_details", {"mealId": str(combo["saved_meal_id"])})
        items = _asegurar_lista(detalles["payload"].get("saved_meal_items", {}).get("saved_meal_item"))
        items_filtrados, excluidos, errores_ops = self._aplicar_operaciones_remover(items=items, operaciones=intencion.operations)
        if errores_ops:
            return self._plan_bloqueado(
                intencion,
                errores_ops[0]["code"],
                errores_ops[0]["detail"],
                extras={"operation_errors": errores_ops},
            )

        resolved_items = [
            {
                "food_id": str(item["food_id"]),
                "food_entry_name": item.get("saved_meal_item_name", "Item"),
                "serving_id": str(item["serving_id"]),
                "number_of_units": float(item["number_of_units"]),
                "rule_applied": "combo_reuse_serving_and_units",
            }
            for item in items_filtrados
        ]

        return {
            "plan_type": "fatsecret_write_batch",
            "date": intencion.date,
            "meal_type": intencion.meal_type,
            "combo_match": {
                "saved_meal_id": str(combo["saved_meal_id"]),
                "saved_meal_name": combo["saved_meal_name"],
                "score": round(combo["score"], 4),
            },
            "resolved_items": resolved_items,
            "excluded_items": excluidos,
            "confidence": {"overall": round(min(combo["score"], 0.99), 4), "combo_match": round(combo["score"], 4), "unit_resolution": 1.0},
            "needs_confirmation": False,
            "blocking_issues": [],
            "trace": {"read_before_write": ["get_saved_meals", "get_meal_details"]},
        }

    def _resolver_alimento_en_gramos(self, intencion: IntencionNormalizada) -> dict[str, Any]:
        if not intencion.food_ref_raw or not intencion.grams or intencion.grams <= 0:
            return self._plan_bloqueado(intencion, "PARSER_SCHEMA_MISMATCH", "Falta food_ref o grams")
        busqueda = self._ejecutor.ejecutar_herramienta(
            "search_foods",
            {"searchExpression": intencion.food_ref_raw, "maxResults": 10, "pageNumber": 0},
        )
        resultados = _asegurar_lista(busqueda["payload"].get("foods", {}).get("food"))
        candidatos = self._rankear_alimentos(resultados, intencion.food_ref_normalized or "")
        if not candidatos:
            return self._plan_bloqueado(intencion, "RESOLVER_COMBO_NOT_FOUND", f"No se encontró alimento: {intencion.food_ref_raw}")

        mejor = candidatos[0]
        detalle_alimento = self._ejecutor.ejecutar_herramienta("get_food", {"foodId": str(mejor["food_id"])})
        servings = _asegurar_lista(detalle_alimento["payload"].get("food", {}).get("servings", {}).get("serving"))
        seleccion = self._seleccionar_serving_para_gramos(servings, float(intencion.grams))
        if not seleccion["ok"]:
            return self._plan_bloqueado(intencion, "RESOLVER_UNSAFE_UNIT_CONVERSION", seleccion["detail"])

        return {
            "plan_type": "fatsecret_write_batch",
            "date": intencion.date,
            "meal_type": intencion.meal_type,
            "combo_match": None,
            "resolved_items": [
                {
                    "food_id": str(mejor["food_id"]),
                    "food_entry_name": mejor.get("food_name") or intencion.food_ref_raw,
                    "serving_id": str(seleccion["serving"]["serving_id"]),
                    "number_of_units": seleccion["number_of_units"],
                    "rule_applied": seleccion["rule_applied"],
                }
            ],
            "excluded_items": [],
            "confidence": {
                "overall": round(min(mejor["score"], seleccion["confidence"]), 4),
                "combo_match": 0.0,
                "unit_resolution": round(seleccion["confidence"], 4),
            },
            "needs_confirmation": False,
            "blocking_issues": [],
            "trace": {"resolution": ["search_foods", "get_food"]},
        }

    def _resolver_combo_por_nombre(self, comidas: list[dict[str, Any]], referencia: str) -> list[dict[str, Any]]:
        resultados = []
        for combo in comidas:
            nombre = str(combo.get("saved_meal_name", "")).strip()
            normalizado = plegar_acentos(normalizar_texto_base(nombre))
            if referencia and referencia == normalizado:
                score = 0.99
            elif referencia and referencia in normalizado:
                score = 0.92
            elif normalizado and referencia and normalizado in referencia:
                score = 0.88
            else:
                score = difflib.SequenceMatcher(None, referencia, normalizado).ratio()
            resultados.append({**combo, "_nombre_normalizado": normalizado, "score": score})
        resultados.sort(key=lambda x: x["score"], reverse=True)
        return [r for r in resultados if r["score"] >= 0.6]

    def _aplicar_operaciones_remover(self, *, items: list[dict[str, Any]], operaciones: list[Any]) -> tuple[list[dict[str, Any]], list[str], list[dict[str, Any]]]:
        items_restantes = list(items)
        excluidos: list[str] = []
        errores: list[dict[str, Any]] = []
        for operacion in operaciones:
            if getattr(operacion, "op", None) != "remove":
                continue
            objetivo = getattr(operacion, "target_normalized", None)
            coincidencias = []
            for item in items_restantes:
                nombre = str(item.get("saved_meal_item_name", ""))
                normalizado = plegar_acentos(normalizar_texto_base(nombre))
                if objetivo and (objetivo == normalizado or objetivo in normalizado):
                    coincidencias.append(item)
            if not coincidencias:
                errores.append({"code": "RESOLVER_INGREDIENT_NOT_FOUND_IN_COMBO", "detail": f"No existe ingrediente '{getattr(operacion, 'target_raw', '')}' en combo"})
                continue
            if len(coincidencias) > 1:
                errores.append({"code": "RESOLVER_INGREDIENT_AMBIGUOUS", "detail": f"Ingrediente ambiguo '{getattr(operacion, 'target_raw', '')}'"})
                continue
            item_remover = coincidencias[0]
            items_restantes = [i for i in items_restantes if i is not item_remover]
            excluidos.append(str(item_remover.get("saved_meal_item_name", "")))
        return items_restantes, excluidos, errores

    def _rankear_alimentos(self, resultados: list[dict[str, Any]], referencia: str) -> list[dict[str, Any]]:
        tokens_ref = [t for t in referencia.split() if t]
        candidatos = []
        for item in resultados:
            nombre = str(item.get("food_name", ""))
            normalizado = plegar_acentos(normalizar_texto_base(nombre))
            score = difflib.SequenceMatcher(None, referencia, normalizado).ratio()
            if referencia and referencia in normalizado:
                score = max(score, 0.9)
            solapes = sum(1 for t in tokens_ref if t in normalizado)
            score = min(score + min(solapes * 0.03, 0.09), 0.99)
            candidatos.append({**item, "score": score})
        candidatos.sort(key=lambda x: x["score"], reverse=True)
        return [c for c in candidatos if c["score"] >= 0.55]

    def _seleccionar_serving_para_gramos(self, servings: list[dict[str, Any]], gramos: float) -> dict[str, Any]:
        for serving in servings:
            if str(serving.get("measurement_description", "")).strip().lower() == "g":
                return {
                    "ok": True,
                    "serving": serving,
                    "number_of_units": float(gramos),
                    "rule_applied": "measurement_description=g => grams exact",
                    "confidence": 1.0,
                }
        for serving in servings:
            if str(serving.get("metric_serving_unit", "")).strip().lower() != "g":
                continue
            try:
                gramos_base = float(serving.get("metric_serving_amount"))
                unidades_base = float(serving.get("number_of_units"))
            except (TypeError, ValueError):
                continue
            if gramos_base <= 0 or unidades_base <= 0:
                continue
            return {
                "ok": True,
                "serving": serving,
                "number_of_units": round((gramos / gramos_base) * unidades_base, 6),
                "rule_applied": "metric_serving_amount_g_scaling",
                "confidence": 0.9,
            }
        return {"ok": False, "detail": "No hay serving seguro en gramos para este alimento"}

    def _plan_bloqueado(self, intencion: IntencionNormalizada, codigo: str, detalle: str, extras: dict[str, Any] | None = None) -> dict[str, Any]:
        plan = {
            "plan_type": "fatsecret_write_batch",
            "date": intencion.date,
            "meal_type": intencion.meal_type,
            "combo_match": None,
            "resolved_items": [],
            "excluded_items": [],
            "confidence": {"overall": 0.0, "combo_match": 0.0, "unit_resolution": 0.0},
            "needs_confirmation": True,
            "blocking_issues": [{"code": codigo, "detail": detalle}],
        }
        if extras:
            plan.update(extras)
        return plan

