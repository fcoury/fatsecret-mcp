from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class RepositorioEstadoLocal:
    def __init__(self, ruta_base_datos: Path) -> None:
        self._ruta_base_datos = ruta_base_datos
        self._inicializar()

    def _conexion(self) -> sqlite3.Connection:
        conexion = sqlite3.connect(self._ruta_base_datos)
        conexion.row_factory = sqlite3.Row
        return conexion

    def _inicializar(self) -> None:
        with self._conexion() as conexion:
            conexion.execute(
                """
                CREATE TABLE IF NOT EXISTS llm_model_pricing (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    effective_from TEXT NOT NULL,
                    effective_to TEXT,
                    currency TEXT NOT NULL DEFAULT 'USD',
                    input_per_million REAL,
                    output_per_million REAL,
                    reasoning_per_million REAL,
                    cached_input_per_million REAL,
                    notes TEXT,
                    source_url TEXT,
                    source_checked_at TEXT
                )
                """
            )
            conexion.execute(
                """
                CREATE TABLE IF NOT EXISTS llm_call_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    project TEXT NOT NULL,
                    service_name TEXT NOT NULL,
                    feature_name TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    request_id TEXT,
                    trace_id TEXT,
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    reasoning_tokens INTEGER,
                    cached_input_tokens INTEGER,
                    total_estimated_cost_usd REAL,
                    cost_estimate_completeness TEXT,
                    raw_usage_json TEXT,
                    success INTEGER NOT NULL,
                    error_code TEXT,
                    latency_ms INTEGER
                )
                """
            )
            conexion.execute(
                """
                CREATE TABLE IF NOT EXISTS pending_nutrition_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    estado_final TEXT NOT NULL,
                    motivo TEXT,
                    texto_usuario TEXT,
                    referencia_fecha TEXT,
                    payload_json TEXT NOT NULL
                )
                """
            )

    def insertar_o_actualizar_precio_modelo(
        self,
        provider: str,
        model_name: str,
        input_per_million: float | None,
        output_per_million: float | None,
        source_url: str | None = None,
        notes: str | None = None,
    ) -> None:
        ahora = datetime.now(timezone.utc).isoformat()
        with self._conexion() as conexion:
            fila = conexion.execute(
                """
                SELECT id FROM llm_model_pricing
                WHERE provider = ? AND model_name = ? AND effective_to IS NULL
                ORDER BY id DESC LIMIT 1
                """,
                (provider, model_name),
            ).fetchone()
            if fila:
                return
            conexion.execute(
                """
                INSERT INTO llm_model_pricing (
                    provider, model_name, effective_from, input_per_million, output_per_million,
                    notes, source_url, source_checked_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (provider, model_name, ahora, input_per_million, output_per_million, notes, source_url, ahora),
            )

    def obtener_precio_modelo(self, provider: str, model_name: str) -> sqlite3.Row | None:
        with self._conexion() as conexion:
            return conexion.execute(
                """
                SELECT * FROM llm_model_pricing
                WHERE provider = ? AND model_name = ? AND effective_to IS NULL
                ORDER BY id DESC LIMIT 1
                """,
                (provider, model_name),
            ).fetchone()

    def registrar_llamada_llm(self, registro: dict[str, Any]) -> None:
        with self._conexion() as conexion:
            conexion.execute(
                """
                INSERT INTO llm_call_log (
                    timestamp, project, service_name, feature_name, provider, model_name,
                    request_id, trace_id, input_tokens, output_tokens, reasoning_tokens, cached_input_tokens,
                    total_estimated_cost_usd, cost_estimate_completeness, raw_usage_json, success, error_code, latency_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    registro.get("timestamp"),
                    registro.get("project", "fatsecret-mcp"),
                    registro.get("service_name", "nutrition-microservice"),
                    registro.get("feature_name", "nutrition_parse"),
                    registro.get("provider"),
                    registro.get("model_name"),
                    registro.get("request_id"),
                    registro.get("trace_id"),
                    registro.get("input_tokens"),
                    registro.get("output_tokens"),
                    registro.get("reasoning_tokens"),
                    registro.get("cached_input_tokens"),
                    registro.get("total_estimated_cost_usd"),
                    registro.get("cost_estimate_completeness"),
                    json.dumps(registro.get("raw_usage_json")) if registro.get("raw_usage_json") is not None else None,
                    1 if registro.get("success", False) else 0,
                    registro.get("error_code"),
                    registro.get("latency_ms"),
                ),
            )

    def registrar_evento_pendiente(
        self,
        estado_final: str,
        motivo: str,
        texto_usuario: str,
        referencia_fecha: str | None,
        payload: dict[str, Any],
    ) -> int:
        ahora = datetime.now(timezone.utc).isoformat()
        with self._conexion() as conexion:
            cursor = conexion.execute(
                """
                INSERT INTO pending_nutrition_events (
                    created_at, estado_final, motivo, texto_usuario, referencia_fecha, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (ahora, estado_final, motivo, texto_usuario, referencia_fecha, json.dumps(payload, ensure_ascii=False)),
            )
            return int(cursor.lastrowid)

