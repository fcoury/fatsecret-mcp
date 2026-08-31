from __future__ import annotations

import sqlite3

import pytest

from fatsecret_mcp.telemetry import EventStore


def rows(path):
    with sqlite3.connect(path) as connection:
        return connection.execute(
            "SELECT event_name, status, attributes_json FROM events ORDER BY timestamp"
        ).fetchall()


def test_disabled_store_is_noop() -> None:
    EventStore(None).emit(
        "tool.completed", session_id="s", trace_id="t", profile="default"
    )


def test_events_persist_without_secret_attributes(tmp_path) -> None:
    path = tmp_path / "events.sqlite3"
    store = EventStore(path)
    store.emit(
        "capability.resolved",
        session_id="s",
        trace_id="t",
        profile="default",
        status="ok",
        attributes={
            "selected_tool_names": ["get_food"],
            "password": "do-not-store",
            "token": "no",
        },
    )
    event = rows(path)[0]
    assert event[:2] == ("capability.resolved", "ok")
    assert "get_food" in event[2]
    assert "do-not-store" not in event[2]
    assert '"token"' not in event[2]


def test_tool_span_records_success_and_error(tmp_path) -> None:
    path = tmp_path / "events.sqlite3"
    store = EventStore(path)
    with store.tool_span(
        session_id="s",
        trace_id="one",
        profile="default",
        tool_name="get_food",
        capability_id="food.get",
    ):
        pass
    with (
        pytest.raises(ValueError),
        store.tool_span(
            session_id="s",
            trace_id="two",
            profile="default",
            tool_name="get_food",
            capability_id="food.get",
        ),
    ):
        raise ValueError("private detail")
    assert [row[1] for row in rows(path)] == ["ok", "error"]
