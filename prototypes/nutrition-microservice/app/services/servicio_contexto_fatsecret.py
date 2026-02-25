from __future__ import annotations

import time
from typing import Any

from .servicio_ejecucion_fatsecret import ServicioEjecucionFatSecret


def _asegurar_lista(valor: Any) -> list[Any]:
    if valor is None:
        return []
    if isinstance(valor, list):
        return valor
    return [valor]


class ServicioContextoFatSecret:
    def __init__(self, servicio_ejecucion: ServicioEjecucionFatSecret, ttl_segundos: int = 120) -> None:
        self._ejecutor = servicio_ejecucion
        self._ttl_segundos = ttl_segundos
        self._cache_comidas_guardadas: tuple[float, list[dict[str, Any]]] | None = None

    def obtener_comidas_guardadas(self, usar_cache: bool = True) -> list[dict[str, Any]]:
        ahora = time.time()
        if usar_cache and self._cache_comidas_guardadas:
            ts, datos = self._cache_comidas_guardadas
            if ahora - ts < self._ttl_segundos:
                return datos
        respuesta = self._ejecutor.ejecutar_herramienta("get_saved_meals", {})
        payload = respuesta["payload"]
        comidas = _asegurar_lista(payload.get("saved_meals", {}).get("saved_meal"))
        self._cache_comidas_guardadas = (ahora, comidas)
        return comidas

    def obtener_nombres_comidas_guardadas(self) -> list[str]:
        return [str(c.get("saved_meal_name", "")).strip() for c in self.obtener_comidas_guardadas() if c.get("saved_meal_name")]

