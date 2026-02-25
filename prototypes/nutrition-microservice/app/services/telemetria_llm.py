from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .repositorio_estado_local import RepositorioEstadoLocal


class ServicioTelemetriaLLM:
    def __init__(self, repositorio: RepositorioEstadoLocal) -> None:
        self._repositorio = repositorio
        self._sembrar_precios()

    def _sembrar_precios(self) -> None:
        self._repositorio.insertar_o_actualizar_precio_modelo(
            provider="openrouter",
            model_name="openai/gpt-4o-mini",
            input_per_million=0.15,
            output_per_million=0.60,
            source_url="https://openrouter.ai",
            notes="Estimación inicial V1 para telemetría local",
        )

    def registrar_llamada(
        self,
        *,
        provider: str,
        model_name: str,
        trace_id: str,
        request_id: str | None,
        uso_crudo: dict[str, Any] | None,
        exito: bool,
        codigo_error: str | None,
        latencia_ms: int,
        feature_name: str = "nutrition_parse",
    ) -> dict[str, Any]:
        uso = self._extraer_uso(uso_crudo)
        costo_info = self._calcular_costo(provider=provider, model_name=model_name, uso=uso)
        registro = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "project": "fatsecret-mcp",
            "service_name": "nutrition-microservice",
            "feature_name": feature_name,
            "provider": provider,
            "model_name": model_name,
            "request_id": request_id,
            "trace_id": trace_id,
            "input_tokens": uso.get("input_tokens"),
            "output_tokens": uso.get("output_tokens"),
            "reasoning_tokens": uso.get("reasoning_tokens"),
            "cached_input_tokens": uso.get("cached_input_tokens"),
            "total_estimated_cost_usd": costo_info.get("total_estimated_cost_usd"),
            "cost_estimate_completeness": costo_info.get("cost_estimate_completeness"),
            "raw_usage_json": uso_crudo,
            "success": exito,
            "error_code": codigo_error,
            "latency_ms": latencia_ms,
        }
        self._repositorio.registrar_llamada_llm(registro)
        return {**uso, **costo_info}

    def _extraer_uso(self, uso_crudo: dict[str, Any] | None) -> dict[str, Any]:
        if not uso_crudo:
            return {
                "input_tokens": None,
                "output_tokens": None,
                "reasoning_tokens": None,
                "cached_input_tokens": None,
            }
        return {
            "input_tokens": uso_crudo.get("prompt_tokens") or uso_crudo.get("input_tokens"),
            "output_tokens": uso_crudo.get("completion_tokens") or uso_crudo.get("output_tokens"),
            "reasoning_tokens": uso_crudo.get("reasoning_tokens"),
            "cached_input_tokens": uso_crudo.get("cached_prompt_tokens") or uso_crudo.get("cached_input_tokens"),
        }

    def _calcular_costo(self, *, provider: str, model_name: str, uso: dict[str, Any]) -> dict[str, Any]:
        precio = self._repositorio.obtener_precio_modelo(provider, model_name)
        if not precio:
            return {"total_estimated_cost_usd": None, "cost_estimate_completeness": "partial"}
        costo = 0.0
        completitud = "full"
        if uso.get("input_tokens") is not None and precio["input_per_million"] is not None:
            costo += (uso["input_tokens"] / 1_000_000) * precio["input_per_million"]
        else:
            completitud = "partial"
        if uso.get("output_tokens") is not None and precio["output_per_million"] is not None:
            costo += (uso["output_tokens"] / 1_000_000) * precio["output_per_million"]
        else:
            completitud = "partial"
        return {"total_estimated_cost_usd": round(costo, 8), "cost_estimate_completeness": completitud}

