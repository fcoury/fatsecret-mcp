"""Aggregate privacy-safe events for profile and tool-catalog review."""

from __future__ import annotations

import sqlite3
from collections import Counter, defaultdict
from itertools import pairwise
from pathlib import Path
from typing import Any


def _goal(tool_names: list[str]) -> tuple[str, float]:
    names = set(tool_names)
    if any("rdi" in name for name in names):
        return "rdi_management", 0.9
    if any(
        "copy_member_recipe" in name or "member_operation" in name for name in names
    ):
        return "recipe_copy", 0.9
    if any("ingredient" in name or "replace_member_recipe" in name for name in names):
        return "recipe_edit", 0.8
    if any("member_recipe" in name for name in names):
        return "recipe_review", 0.7
    if any("food_entry" in name or "food_entries" in name for name in names):
        return "diary_logging", 0.8
    if any("search" in name or name in {"get_food", "get_recipe"} for name in names):
        return "catalog_discovery", 0.7
    if any("auth" in name or "credential" in name or "oauth" in name for name in names):
        return "authentication", 0.8
    return "unknown", 0.0


def build_report(path: Path) -> dict[str, Any]:
    """Build frequency, sequence, and coarse inferred-goal aggregates."""

    if not path.exists():
        return {"sessions": 0, "tool_frequency": {}, "transitions": {}, "goals": {}}
    with sqlite3.connect(path) as connection:
        rows = connection.execute(
            """
            SELECT session_id, tool_name, status
            FROM events
            WHERE event_name = 'tool.completed' AND tool_name IS NOT NULL
            ORDER BY timestamp, event_id
            """
        ).fetchall()
    sessions: dict[str, list[str]] = defaultdict(list)
    status_counts: Counter[str] = Counter()
    for session_id, tool_name, status in rows:
        sessions[session_id].append(tool_name)
        status_counts[f"{tool_name}:{status or 'unknown'}"] += 1
    frequency = Counter(tool for tools in sessions.values() for tool in tools)
    transitions = Counter(
        f"{left} -> {right}"
        for tools in sessions.values()
        for left, right in pairwise(tools)
    )
    goals = Counter(_goal(tools)[0] for tools in sessions.values())
    inferred = [
        {
            "session_id": session_id,
            "goal": _goal(tools)[0],
            "confidence": _goal(tools)[1],
            "tool_count": len(tools),
        }
        for session_id, tools in sorted(sessions.items())
    ]
    return {
        "sessions": len(sessions),
        "tool_frequency": dict(frequency.most_common()),
        "tool_status_frequency": dict(status_counts.most_common()),
        "transitions": dict(transitions.most_common()),
        "goals": dict(goals.most_common()),
        "inferred_sessions": inferred,
    }


__all__ = ["build_report"]
