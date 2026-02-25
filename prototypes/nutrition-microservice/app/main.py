from __future__ import annotations

from functools import lru_cache

from fastapi import FastAPI

from app.api.routes import construir_router
from app.services.configuracion import cargar_configuracion
from app.services.repositorio_estado_local import RepositorioEstadoLocal
from app.services.servicio_contexto_fatsecret import ServicioContextoFatSecret
from app.services.servicio_ejecucion_fatsecret import ServicioEjecucionFatSecret
from app.services.servicio_normalizacion_nutricion import ServicioNormalizacionNutricion
from app.services.servicio_parseo_nutricion import ServicioParseoNutricion
from app.services.servicio_resolucion_nutricion import ServicioResolucionNutricion
from app.services.telemetria_llm import ServicioTelemetriaLLM


@lru_cache(maxsize=1)
def obtener_dependencias() -> dict[str, object]:
    configuracion = cargar_configuracion()
    repositorio = RepositorioEstadoLocal(configuracion.ruta_base_datos_local)
    telemetria = ServicioTelemetriaLLM(repositorio)
    servicio_ejecucion = ServicioEjecucionFatSecret(configuracion)
    servicio_contexto = ServicioContextoFatSecret(servicio_ejecucion, ttl_segundos=configuracion.ttl_cache_contexto_segundos)
    servicio_parseo = ServicioParseoNutricion(configuracion, telemetria)
    servicio_normalizacion = ServicioNormalizacionNutricion()
    servicio_resolucion = ServicioResolucionNutricion(servicio_contexto, servicio_ejecucion)
    return {
        "configuracion": configuracion,
        "repositorio": repositorio,
        "telemetria": telemetria,
        "servicio_ejecucion": servicio_ejecucion,
        "servicio_contexto": servicio_contexto,
        "servicio_parseo": servicio_parseo,
        "servicio_normalizacion": servicio_normalizacion,
        "servicio_resolucion": servicio_resolucion,
    }


app = FastAPI(title="Nutrition Deterministic Microservice Prototype", version="0.1.0")
app.include_router(construir_router(obtener_dependencias))

