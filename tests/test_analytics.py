from __future__ import annotations

from fatsecret_mcp.analytics import build_report
from fatsecret_mcp.telemetry import EventStore


def emit(store: EventStore, session: str, tool: str) -> None:
    store.emit(
        "tool.completed",
        session_id=session,
        trace_id=f"trace-{tool}",
        profile="default",
        tool_name=tool,
        capability_id=tool,
        status="ok",
    )


def test_report_aggregates_frequency_transitions_and_goals(tmp_path) -> None:
    path = tmp_path / "events.sqlite3"
    store = EventStore(path)
    emit(store, "recipe-session", "get_member_recipe")
    emit(store, "recipe-session", "replace_member_recipe_ingredient")
    emit(store, "rdi-session", "get_member_rdi")
    report = build_report(path)
    assert report["sessions"] == 2
    assert report["tool_frequency"]["get_member_recipe"] == 1
    assert report["transitions"] == {
        "get_member_recipe -> replace_member_recipe_ingredient": 1
    }
    assert report["goals"] == {"recipe_edit": 1, "rdi_management": 1}


def test_report_for_missing_store_is_empty(tmp_path) -> None:
    assert build_report(tmp_path / "missing.sqlite3")["sessions"] == 0
