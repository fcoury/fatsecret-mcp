from __future__ import annotations

import uuid
from datetime import date
from typing import Any, Callable

from fastapi import APIRouter, Depends

from app.models.schemas import IntencionNormalizada, SobreApi, SolicitudExecute, SolicitudParseAndLog, SolicitudResolver, SolicitudTextoReferencia


def construir_router(obtener_dependencias: Callable[[], dict[str, object]]) -> APIRouter:
    router = APIRouter()

    def sobre(ok: bool, phase: str, data: dict[str, Any], warnings: list[str] | None = None, errors: list[dict[str, Any]] | None = None) -> SobreApi:
        return SobreApi(ok=ok, phase=phase, data=data, warnings=warnings or [], errors=errors or [])

    def meal_aliases() -> list[str]:
        return ["desayuno", "comida", "almuerzo", "cena", "other", "breakfast", "lunch", "dinner"]

    @router.post("/parse", response_model=SobreApi)
    @router.post("/v1/nutrition/parse", response_model=SobreApi, include_in_schema=False)
    def endpoint_parse(solicitud: SolicitudTextoReferencia, deps=Depends(obtener_dependencias)) -> SobreApi:
        trace_id = str(uuid.uuid4())
        reference_date = solicitud.reference_date or date.today().isoformat()
        combos = deps["servicio_contexto"].obtener_nombres_comidas_guardadas()
        resultado_parseo = deps["servicio_parseo"].parsear(
            texto_usuario=solicitud.text,
            reference_date=reference_date,
            available_combos=combos,
            meal_aliases=meal_aliases(),
            trace_id=trace_id,
        )
        intencion = deps["servicio_normalizacion"].normalizar_intencion(resultado_parseo["parser_output"], reference_date)
        return sobre(
            ok=True,
            phase="parse",
            data={
                "trace_id": trace_id,
                "parser_output": resultado_parseo["parser_output"],
                "parser_metadata": resultado_parseo["parser_metadata"],
                "normalized_intent": intencion.model_dump(),
                "parse_issues": intencion.parse_issues,
            },
            warnings=[w.get("code", "warning") for w in resultado_parseo.get("parser_warnings", [])],
        )

    @router.post("/resolve", response_model=SobreApi)
    @router.post("/v1/nutrition/resolve", response_model=SobreApi, include_in_schema=False)
    def endpoint_resolve(solicitud: SolicitudResolver, deps=Depends(obtener_dependencias)) -> SobreApi:
        trace_id = str(uuid.uuid4())
        reference_date = solicitud.reference_date or date.today().isoformat()
        if solicitud.intencion_normalizada:
            intencion = IntencionNormalizada.model_validate(solicitud.intencion_normalizada)
            parser_info = None
        else:
            combos = deps["servicio_contexto"].obtener_nombres_comidas_guardadas()
            resultado_parseo = deps["servicio_parseo"].parsear(
                texto_usuario=solicitud.text or "",
                reference_date=reference_date,
                available_combos=combos,
                meal_aliases=meal_aliases(),
                trace_id=trace_id,
            )
            intencion = deps["servicio_normalizacion"].normalizar_intencion(resultado_parseo["parser_output"], reference_date)
            parser_info = {"parser_output": resultado_parseo["parser_output"], "parser_metadata": resultado_parseo["parser_metadata"]}
        plan = deps["servicio_resolucion"].resolver(intencion)
        return sobre(
            ok=len(plan.get("blocking_issues", [])) == 0,
            phase="resolve",
            data={
                "trace_id": trace_id,
                "normalized_intent": intencion.model_dump(),
                "execution_plan": plan,
                "confidence": plan.get("confidence"),
                "blocking_issues": plan.get("blocking_issues", []),
                "parser": parser_info,
            },
            errors=plan.get("blocking_issues", []),
        )

    @router.post("/execute", response_model=SobreApi)
    @router.post("/v1/nutrition/execute", response_model=SobreApi, include_in_schema=False)
    def endpoint_execute(solicitud: SolicitudExecute, deps=Depends(obtener_dependencias)) -> SobreApi:
        resultado = deps["servicio_ejecucion"].ejecutar_plan(solicitud.plan)
        errores = []
        if resultado["status"] == "partial":
            errores.append({"code": "MCP_PARTIAL_WRITE_FAILURE", "detail": "Escritura parcial"})
        if resultado["status"] == "error":
            errores.append({"code": "MCP_PARTIAL_WRITE_FAILURE", "detail": "Error de escritura"})
        return sobre(ok=resultado["status"] != "error", phase="execute", data={"executor_result": resultado}, errors=errores)

    @router.post("/parse-and-log", response_model=SobreApi)
    @router.post("/v1/nutrition/parse-and-log", response_model=SobreApi, include_in_schema=False)
    def endpoint_parse_and_log(solicitud: SolicitudParseAndLog, deps=Depends(obtener_dependencias)) -> SobreApi:
        trace_id = str(uuid.uuid4())
        reference_date = solicitud.reference_date or date.today().isoformat()
        combos = deps["servicio_contexto"].obtener_nombres_comidas_guardadas()
        resultado_parseo = deps["servicio_parseo"].parsear(
            texto_usuario=solicitud.text,
            reference_date=reference_date,
            available_combos=combos,
            meal_aliases=meal_aliases(),
            trace_id=trace_id,
        )
        intencion = deps["servicio_normalizacion"].normalizar_intencion(resultado_parseo["parser_output"], reference_date)
        plan = deps["servicio_resolucion"].resolver(intencion)

        if plan.get("blocking_issues"):
            id_pendiente = deps["repositorio"].registrar_evento_pendiente(
                estado_final="captured_pending_review",
                motivo=plan["blocking_issues"][0]["code"],
                texto_usuario=solicitud.text,
                referencia_fecha=reference_date,
                payload={"trace_id": trace_id, "parser_output": resultado_parseo["parser_output"], "normalized_intent": intencion.model_dump(), "execution_plan": plan},
            )
            return sobre(
                ok=False,
                phase="parse-and-log",
                data={"trace_id": trace_id, "state": "captured_pending_review", "pending_event_id": id_pendiente, "parser_output": resultado_parseo["parser_output"], "normalized_intent": intencion.model_dump(), "execution_plan": plan},
                errors=plan["blocking_issues"],
            )

        resultado_ejecucion = deps["servicio_ejecucion"].ejecutar_plan(plan) if solicitud.ejecutar_escritura else None
        estado = "captured_pending_review" if not solicitud.ejecutar_escritura else ("synced_to_fatsecret" if resultado_ejecucion and resultado_ejecucion["status"] == "ok" else "captured_pending_sync")
        pending_event_id = None
        if estado != "synced_to_fatsecret":
            pending_event_id = deps["repositorio"].registrar_evento_pendiente(
                estado_final=estado,
                motivo=("MCP_PARTIAL_WRITE_FAILURE" if estado == "captured_pending_sync" else "NO_WRITE_REQUESTED"),
                texto_usuario=solicitud.text,
                referencia_fecha=reference_date,
                payload={"trace_id": trace_id, "parser_output": resultado_parseo["parser_output"], "normalized_intent": intencion.model_dump(), "execution_plan": plan, "executor_result": resultado_ejecucion},
            )
        errores = [] if estado == "synced_to_fatsecret" else [{"code": "MCP_PARTIAL_WRITE_FAILURE" if estado == "captured_pending_sync" else "PENDING_REVIEW", "detail": estado}]
        return sobre(
            ok=estado == "synced_to_fatsecret",
            phase="parse-and-log",
            data={"trace_id": trace_id, "state": estado, "pending_event_id": pending_event_id, "parser_output": resultado_parseo["parser_output"], "parser_metadata": resultado_parseo["parser_metadata"], "normalized_intent": intencion.model_dump(), "execution_plan": plan, "executor_result": resultado_ejecucion},
            errors=errores,
        )

    return router

