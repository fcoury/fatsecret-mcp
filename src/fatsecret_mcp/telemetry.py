"""Privacy-preserving local observability for tool and capability decisions."""

from __future__ import annotations

import json
import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

_EVENT_ATTRIBUTES: dict[str, frozenset[str]] = {
    "tools.advertised": frozenset({"tool_names"}),
    "capability.resolved": frozenset(
        {
            "candidate_capability_ids",
            "candidate_rankings",
            "selected_tool_names",
            "activated_tool_names",
            "blocked_reason_codes",
            "intent_fingerprint",
        }
    ),
    "tools.list_changed_published": frozenset(
        {"activated_tool_names", "schema_bytes_added"}
    ),
}


class EventStore:
    def __init__(self, path: Path | None) -> None:
        self.path = path
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            with self._connect() as connection:
                connection.execute("PRAGMA journal_mode=WAL")
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS events (
                        event_id TEXT PRIMARY KEY,
                        timestamp TEXT NOT NULL,
                        session_id TEXT NOT NULL,
                        trace_id TEXT NOT NULL,
                        event_name TEXT NOT NULL,
                        tool_name TEXT,
                        capability_id TEXT,
                        profile TEXT NOT NULL,
                        duration_ms REAL,
                        status TEXT,
                        attributes_json TEXT NOT NULL
                    )
                    """
                )
                connection.execute(
                    "CREATE INDEX IF NOT EXISTS idx_events_name_time ON events(event_name, timestamp)"
                )
            path.chmod(0o600)

    def _connect(self) -> sqlite3.Connection:
        if self.path is None:
            raise RuntimeError("telemetry is disabled")
        return sqlite3.connect(self.path, timeout=30)

    def emit(
        self,
        event_name: str,
        *,
        session_id: str,
        trace_id: str,
        profile: str,
        tool_name: str | None = None,
        capability_id: str | None = None,
        duration_ms: float | None = None,
        status: str | None = None,
        attributes: dict[str, object] | None = None,
    ) -> None:
        if self.path is None:
            return
        allowed = _EVENT_ATTRIBUTES.get(event_name, frozenset())
        safe_attributes = {
            key: value for key, value in (attributes or {}).items() if key in allowed
        }
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    str(uuid4()),
                    datetime.now(UTC).isoformat(),
                    session_id,
                    trace_id,
                    event_name,
                    tool_name,
                    capability_id,
                    profile,
                    duration_ms,
                    status,
                    json.dumps(safe_attributes, sort_keys=True, default=str),
                ),
            )

    @contextmanager
    def tool_span(
        self,
        *,
        session_id: str,
        trace_id: str,
        profile: str,
        tool_name: str,
        capability_id: str,
    ) -> Iterator[None]:
        started = time.perf_counter()
        status = "ok"
        try:
            yield
        except Exception:
            status = "error"
            raise
        finally:
            self.emit(
                "tool.completed",
                session_id=session_id,
                trace_id=trace_id,
                profile=profile,
                tool_name=tool_name,
                capability_id=capability_id,
                duration_ms=(time.perf_counter() - started) * 1000,
                status=status,
            )


def new_trace_id() -> str:
    return str(uuid4())
