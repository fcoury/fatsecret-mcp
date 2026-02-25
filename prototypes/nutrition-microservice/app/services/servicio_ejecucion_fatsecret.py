from __future__ import annotations

import json
import subprocess
from typing import Any

from .configuracion import ConfiguracionMicroservicio


class ErrorMCP(Exception):
    def __init__(self, codigo: str, mensaje: str, detalle: Any | None = None) -> None:
        super().__init__(mensaje)
        self.codigo = codigo
        self.detalle = detalle


class ServicioEjecucionFatSecret:
    def __init__(self, configuracion: ConfiguracionMicroservicio) -> None:
        self._config = configuracion
        self._cache_discovery: dict[str, Any] | None = None

    def discovery(self) -> dict[str, Any]:
        respuesta = self._llamar_jsonrpc(
            {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "discovery", "arguments": {}}, "id": 1}
        )
        contenido = self._extraer_texto_resultado(respuesta)
        self._cache_discovery = {"texto": contenido, "respuesta_cruda": respuesta}
        return self._cache_discovery

    def ejecutar_herramienta(self, nombre_herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]:
        ultimo_error: ErrorMCP | None = None
        for intento in (1, 2):
            try:
                respuesta = self._llamar_jsonrpc(
                    {
                        "jsonrpc": "2.0",
                        "method": "tools/call",
                        "params": {"name": "execute", "arguments": {"tool": nombre_herramienta, "arguments": argumentos}},
                        "id": 1,
                    }
                )
                texto = self._extraer_texto_resultado(respuesta)
                return {
                    "ok": True,
                    "tool": nombre_herramienta,
                    "arguments": argumentos,
                    "payload": self._intentar_parsear_json_texto(texto),
                    "raw_text": texto,
                    "raw_jsonrpc": respuesta,
                }
            except ErrorMCP as error:
                ultimo_error = error
                if error.codigo == "MCP_TOOL_NOT_FOUND" and intento == 1:
                    self.discovery()
                    continue
                raise
        raise ultimo_error or ErrorMCP("MCP_TRANSPORT_ERROR", "Error MCP")

    def ejecutar_plan(self, plan_ejecucion: dict[str, Any]) -> dict[str, Any]:
        entradas: list[dict[str, Any]] = []
        fallos: list[dict[str, Any]] = []
        for item in plan_ejecucion.get("resolved_items", []):
            argumentos = {
                "foodId": str(item["food_id"]),
                "foodEntryName": item["food_entry_name"],
                "servingId": str(item["serving_id"]),
                "numberOfUnits": float(item["number_of_units"]),
                "mealType": plan_ejecucion["meal_type"],
                "date": plan_ejecucion["date"],
            }
            try:
                resultado = self.ejecutar_herramienta("add_food_entry", argumentos)
                entradas.append(
                    {
                        "food_entry_name": item["food_entry_name"],
                        "food_entry_id": self._extraer_id_entrada(resultado.get("payload")),
                        "serving_id": str(item["serving_id"]),
                        "number_of_units": str(item["number_of_units"]),
                    }
                )
            except Exception as error:  # noqa: BLE001
                fallos.append({"food_entry_name": item.get("food_entry_name"), "error": str(error)})

        return {
            "status": "ok" if not fallos else ("partial" if entradas else "error"),
            "date": plan_ejecucion["date"],
            "meal_type": plan_ejecucion["meal_type"],
            "executed_count": len(entradas),
            "failed_count": len(fallos),
            "entries": entradas,
            "partial_failures": fallos,
        }

    def _llamar_jsonrpc(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self._config.ruta_mcp_node.exists():
            raise ErrorMCP("MCP_TRANSPORT_ERROR", f"No existe {self._config.ruta_mcp_node}")
        try:
            proceso = subprocess.run(
                ["node", str(self._config.ruta_mcp_node)],
                input=(json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self._config.ruta_raiz_repo),
                timeout=self._config.timeout_mcp_segundos,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            raise ErrorMCP("MCP_TRANSPORT_ERROR", "Timeout llamando MCP") from error

        salida = proceso.stdout.decode("utf-8", errors="replace")
        respuesta = self._extraer_jsonrpc_desde_salida(salida)
        if not respuesta:
            raise ErrorMCP(
                "MCP_TRANSPORT_ERROR",
                "No se pudo parsear JSON-RPC del stdout del MCP",
                {"stdout": salida[:1500], "stderr": proceso.stderr.decode("utf-8", errors="replace")[:500]},
            )
        if "error" in respuesta:
            mensaje = json.dumps(respuesta["error"], ensure_ascii=False)
            codigo = "MCP_TRANSPORT_ERROR"
            if "not found" in mensaje.lower():
                codigo = "MCP_TOOL_NOT_FOUND"
            elif "schema" in mensaje.lower() or "invalid" in mensaje.lower():
                codigo = "MCP_SCHEMA_ERROR"
            raise ErrorMCP(codigo, mensaje, respuesta["error"])
        return respuesta

    def _extraer_jsonrpc_desde_salida(self, salida: str) -> dict[str, Any] | None:
        for linea in salida.splitlines():
            linea = linea.strip()
            if not linea.startswith("{"):
                continue
            try:
                candidato = json.loads(linea)
            except json.JSONDecodeError:
                continue
            if isinstance(candidato, dict) and "jsonrpc" in candidato:
                return candidato
        return None

    def _extraer_texto_resultado(self, respuesta_jsonrpc: dict[str, Any]) -> str:
        for item in respuesta_jsonrpc.get("result", {}).get("content", []):
            if item.get("type") == "text":
                return item.get("text", "")
        raise ErrorMCP("MCP_TRANSPORT_ERROR", "Respuesta sin result.content.text")

    def _intentar_parsear_json_texto(self, texto: str) -> Any:
        texto = texto.strip()
        if not texto:
            return {}
        try:
            return json.loads(texto)
        except json.JSONDecodeError:
            return {"raw_text": texto}

    def _extraer_id_entrada(self, payload: Any) -> str | None:
        if not isinstance(payload, dict):
            return None
        candidatos = [
            payload.get("food_entry_id"),
            payload.get("created_food_entry_id"),
            payload.get("api_response", {}).get("food_entry_id", {}).get("value")
            if isinstance(payload.get("api_response"), dict)
            and isinstance(payload.get("api_response", {}).get("food_entry_id"), dict)
            else None,
            payload.get("food_entry", {}).get("food_entry_id") if isinstance(payload.get("food_entry"), dict) else None,
        ]
        for candidato in candidatos:
            if candidato:
                return str(candidato)
        return None
