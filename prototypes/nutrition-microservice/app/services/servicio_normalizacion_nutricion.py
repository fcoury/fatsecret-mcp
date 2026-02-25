from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, timedelta
from typing import Any

from app.models.schemas import IntencionNormalizada


def normalizar_texto_base(texto: str) -> str:
    return " ".join(texto.lower().strip().split())


def plegar_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


class ServicioNormalizacionNutricion:
    _mapa_alias_comidas = {
        "desayuno": "breakfast",
        "breakfast": "breakfast",
        "comida": "lunch",
        "almuerzo": "lunch",
        "lunch": "lunch",
        "cena": "dinner",
        "dinner": "dinner",
        "otro": "other",
        "otros": "other",
        "other": "other",
    }

    def normalizar_intencion(self, salida_parser: dict[str, Any], reference_date: str | None) -> IntencionNormalizada:
        issues: list[dict[str, Any]] = []
        intent = str(salida_parser.get("intent") or "unknown")
        if intent not in {"log_combo", "log_combo_modified", "log_single_food_grams", "unknown"}:
            issues.append({"code": "PARSER_UNKNOWN_INTENT", "detail": f"Intent no permitido: {intent}"})
            intent = "unknown"

        fecha_resuelta = self._resolver_fecha(salida_parser.get("date_ref"), reference_date, issues)
        tipo_comida = self._resolver_meal_type(salida_parser.get("meal_hint"), issues)

        operaciones_normalizadas = []
        for operacion in salida_parser.get("operations", []) or []:
            if not isinstance(operacion, dict):
                continue
            if operacion.get("op") != "remove" or not operacion.get("target"):
                issues.append({"code": "PARSER_SCHEMA_MISMATCH", "detail": "Operacion no soportada"})
                continue
            objetivo = str(operacion["target"])
            operaciones_normalizadas.append(
                {
                    "op": "remove",
                    "target_raw": objetivo,
                    "target_normalized": plegar_acentos(normalizar_texto_base(objetivo)),
                }
            )

        combo_ref_raw = salida_parser.get("combo_ref")
        food_ref_raw = salida_parser.get("food_ref")
        gramos = salida_parser.get("grams")
        if gramos is not None:
            try:
                gramos = float(gramos)
            except (TypeError, ValueError):
                issues.append({"code": "PARSER_SCHEMA_MISMATCH", "detail": "grams invalido"})
                gramos = None

        return IntencionNormalizada(
            intent=intent,
            date=fecha_resuelta,
            meal_type=tipo_comida,
            combo_ref_raw=combo_ref_raw,
            combo_ref_normalized=plegar_acentos(normalizar_texto_base(combo_ref_raw)) if combo_ref_raw else None,
            food_ref_raw=food_ref_raw,
            food_ref_normalized=plegar_acentos(normalizar_texto_base(food_ref_raw)) if food_ref_raw else None,
            grams=gramos,
            operations=operaciones_normalizadas,
            parser_valid=len(issues) == 0 and intent != "unknown",
            parse_issues=issues,
        )

    def _resolver_fecha(self, date_ref: Any, reference_date: str | None, issues: list[dict[str, Any]]) -> str:
        fecha_base = self._parsear_fecha_base(reference_date, issues)
        valor = str(date_ref or "today").strip().lower()
        valor_plano = plegar_acentos(valor)
        if valor_plano in {"today", "hoy"}:
            return fecha_base.isoformat()
        if valor_plano in {"tomorrow", "manana", "mañana"}:
            return (fecha_base + timedelta(days=1)).isoformat()
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", valor):
            return valor
        issues.append({"code": "NORMALIZER_INVALID_DATE_REF", "detail": f"date_ref invalido: {date_ref}"})
        return fecha_base.isoformat()

    def _parsear_fecha_base(self, reference_date: str | None, issues: list[dict[str, Any]]) -> date:
        if not reference_date:
            return date.today()
        try:
            return datetime.strptime(reference_date, "%Y-%m-%d").date()
        except ValueError:
            issues.append({"code": "NORMALIZER_INVALID_DATE_REF", "detail": f"reference_date invalido: {reference_date}"})
            return date.today()

    def _resolver_meal_type(self, meal_hint: Any, issues: list[dict[str, Any]]) -> str:
        if meal_hint is None:
            return "other"
        clave = plegar_acentos(normalizar_texto_base(str(meal_hint)))
        if clave in self._mapa_alias_comidas:
            return self._mapa_alias_comidas[clave]
        issues.append({"code": "NORMALIZER_INVALID_MEAL_HINT", "detail": f"meal_hint invalido: {meal_hint}"})
        return "other"

