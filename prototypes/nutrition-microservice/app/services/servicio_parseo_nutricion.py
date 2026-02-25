from __future__ import annotations

import json
import re
import time
import uuid
from datetime import date
from typing import Any

import httpx
import yaml

from .configuracion import ConfiguracionMicroservicio
from .servicio_normalizacion_nutricion import plegar_acentos
from .telemetria_llm import ServicioTelemetriaLLM


class ServicioParseoNutricion:
    def __init__(self, configuracion: ConfiguracionMicroservicio, telemetria_llm: ServicioTelemetriaLLM) -> None:
        self._config = configuracion
        self._telemetria = telemetria_llm
        self._prompt_definicion = self._cargar_prompt()

    def _cargar_prompt(self) -> dict[str, Any]:
        if not self._config.ruta_prompt_parseo.exists():
            return {}
        return yaml.safe_load(self._config.ruta_prompt_parseo.read_text(encoding="utf-8")) or {}

    def parsear(self, *, texto_usuario: str, reference_date: str | None, available_combos: list[str], meal_aliases: list[str], trace_id: str) -> dict[str, Any]:
        inicio = time.perf_counter()
        request_id = str(uuid.uuid4())
        errores: list[dict[str, Any]] = []
        if self._config.openrouter_api_key:
            try:
                salida_llm = self._parsear_con_openrouter(
                    texto_usuario=texto_usuario,
                    reference_date=reference_date or date.today().isoformat(),
                    available_combos=available_combos,
                    meal_aliases=meal_aliases,
                )
                latencia_ms = int((time.perf_counter() - inicio) * 1000)
                telemetria = self._telemetria.registrar_llamada(
                    provider="openrouter",
                    model_name=self._config.modelo_parser_openrouter,
                    trace_id=trace_id,
                    request_id=request_id,
                    uso_crudo=salida_llm.get("usage"),
                    exito=True,
                    codigo_error=None,
                    latencia_ms=latencia_ms,
                )
                return {
                    "parser_output": salida_llm["json"],
                    "parser_metadata": {
                        "provider": "openrouter",
                        "model": self._config.modelo_parser_openrouter,
                        "latency_ms": latencia_ms,
                        "fallback_used": False,
                        "token_usage": telemetria,
                    },
                    "parser_raw_output": salida_llm.get("raw_text"),
                }
            except Exception as error:  # noqa: BLE001
                latencia_ms = int((time.perf_counter() - inicio) * 1000)
                self._telemetria.registrar_llamada(
                    provider="openrouter",
                    model_name=self._config.modelo_parser_openrouter,
                    trace_id=trace_id,
                    request_id=request_id,
                    uso_crudo=None,
                    exito=False,
                    codigo_error="PARSER_INVALID_JSON",
                    latencia_ms=latencia_ms,
                )
                errores.append({"code": "PARSER_INVALID_JSON", "detail": str(error)})

        salida_fallback = self._parseador_regex(texto_usuario)
        latencia_ms = int((time.perf_counter() - inicio) * 1000)
        return {
            "parser_output": salida_fallback,
            "parser_metadata": {
                "provider": "local-regex",
                "model": "regex-v1",
                "latency_ms": latencia_ms,
                "fallback_used": True,
                "fallback_reason": errores[0]["detail"] if errores else "No OPENROUTER_API_KEY",
                "token_usage": {},
            },
            "parser_raw_output": json.dumps(salida_fallback, ensure_ascii=False),
            "parser_warnings": errores,
        }

    def _parsear_con_openrouter(self, *, texto_usuario: str, reference_date: str, available_combos: list[str], meal_aliases: list[str]) -> dict[str, Any]:
        sistema = self._construir_prompt_sistema(reference_date, available_combos, meal_aliases)
        cuerpo = {
            "model": self._config.modelo_parser_openrouter,
            "messages": [{"role": "system", "content": sistema}, {"role": "user", "content": texto_usuario}],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self._config.openrouter_api_key}",
            "Content-Type": "application/json",
            "X-Title": "nutrition-microservice-prototype",
            "HTTP-Referer": "http://localhost/nutrition-microservice-prototype",
        }
        with httpx.Client(timeout=self._config.timeout_llm_segundos) as cliente:
            respuesta = cliente.post(self._config.url_openrouter, headers=headers, json=cuerpo)
        respuesta.raise_for_status()
        payload = respuesta.json()
        contenido = ((payload.get("choices") or [{}])[0].get("message") or {}).get("content")
        if isinstance(contenido, list):
            contenido = "".join(x.get("text", "") for x in contenido if isinstance(x, dict))
        if not isinstance(contenido, str):
            raise ValueError("OpenRouter sin contenido string")
        try:
            salida_json = json.loads(contenido)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", contenido, flags=re.DOTALL)
            if not match:
                raise
            salida_json = json.loads(match.group(0))
        return {"json": salida_json, "usage": payload.get("usage"), "raw_text": contenido}

    def _construir_prompt_sistema(self, reference_date: str, available_combos: list[str], meal_aliases: list[str]) -> str:
        base = self._prompt_definicion.get("system_prompt", "")
        ejemplos = self._prompt_definicion.get("examples", [])
        return (
            base.replace("{{reference_date}}", reference_date)
            .replace("{{available_combos}}", json.dumps(available_combos, ensure_ascii=False))
            .replace("{{meal_aliases}}", json.dumps(meal_aliases, ensure_ascii=False))
            .replace("{{examples}}", "\n".join(json.dumps(e, ensure_ascii=False) for e in ejemplos))
        )

    def _parseador_regex(self, texto_usuario: str) -> dict[str, Any]:
        texto_original = texto_usuario.strip()
        texto_plano = plegar_acentos(texto_original.lower())
        date_ref = "tomorrow" if any(p in texto_plano for p in [" mañana", " manana", "para manana", "para mañana"]) else "today"
        meal_hint = "other"
        if "desayuno" in texto_plano:
            meal_hint = "breakfast"
        elif "comida" in texto_plano or "almuerzo" in texto_plano:
            meal_hint = "lunch"
        elif "cena" in texto_plano:
            meal_hint = "dinner"

        patron_gramos = re.search(r"(\d+(?:[.,]\d+)?)\s*g(?:r|ramos)?\s+de\s+(.+)", texto_original, flags=re.IGNORECASE)
        if patron_gramos:
            gramos = float(patron_gramos.group(1).replace(",", "."))
            resto = patron_gramos.group(2).strip()
            food_ref = re.split(r"\s+para\s+(?:hoy|manana|mañana)\b", resto, flags=re.IGNORECASE)[0].strip()
            return {"intent": "log_single_food_grams", "date_ref": date_ref, "meal_hint": meal_hint, "food_ref": food_ref, "grams": gramos}

        operaciones = []
        match_sin = re.search(r"\bsin\s+(.+)", texto_original, flags=re.IGNORECASE)
        if match_sin:
            target = re.split(r"\s+para\s+(?:hoy|manana|mañana)\b|\s+en\s+(?:desayuno|comida|almuerzo|cena)\b", match_sin.group(1), flags=re.IGNORECASE)[0].strip()
            operaciones.append({"op": "remove", "target": target})

        combo_ref = None
        if "ensalada" in texto_plano:
            combo_ref = "Ensalada Base"
        elif "desayuno" in texto_plano and "siempre" in texto_plano:
            combo_ref = "Desayuno"

        if combo_ref:
            return {
                "intent": "log_combo_modified" if operaciones else "log_combo",
                "date_ref": date_ref,
                "meal_hint": meal_hint,
                "combo_ref": combo_ref,
                "operations": operaciones,
            }
        return {"intent": "unknown", "date_ref": date_ref, "meal_hint": meal_hint}

