from __future__ import annotations

from typing import Any, cast

import pytest
from mcp import Client

from fatsecret_mcp.runtime import Runtime
from fatsecret_mcp.server import create_server
from fatsecret_mcp.settings import Settings
from fatsecret_mcp.telemetry import EventStore


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_default_profile_over_protocol(tmp_path) -> None:
    server = create_server(
        settings=Settings(state_dir=tmp_path, telemetry_enabled=False)
    )
    async with Client(server, raise_exceptions=True) as client:
        listed = await client.list_tools()
    names = [tool.name for tool in listed.tools]
    assert len(names) == 16
    assert "get_member_recipe" in names
    assert "search_foods" not in names
    assert "resolve_fatsecret_capability" in names


@pytest.mark.anyio
async def test_resolver_activates_only_selected_library_tool(tmp_path) -> None:
    server = create_server(
        settings=Settings(state_dir=tmp_path, telemetry_enabled=True)
    )
    async with Client(server, raise_exceptions=True) as client:
        before = await client.list_tools()
        result = await client.call_tool(
            "resolve_fatsecret_capability",
            {"request": "autocomplete food suggestions", "max_tools": 1},
        )
        after = await client.list_tools()
    assert result.is_error is False
    assert result.structured_content["activated"] == ["fatsecret_foods_autocomplete"]
    assert len(after.tools) == len(before.tools) + 1
    assert "fatsecret_foods_autocomplete" in {tool.name for tool in after.tools}


class FakeAdapter:
    def __init__(self) -> None:
        self.calls = []

    def call(self, resource, method, arguments):
        self.calls.append((resource, method, arguments))
        return {"data": [{"food_name": "Apple"}]}

    def close(self) -> None:
        pass


@pytest.mark.anyio
async def test_reached_tool_dispatches_to_selected_latest_method(tmp_path) -> None:
    settings = Settings(state_dir=tmp_path, telemetry_enabled=True)
    fake = FakeAdapter()
    runtime = Runtime(
        settings,
        auth=cast(Any, FakeAdapter()),
        official=fake,
        member=cast(Any, FakeAdapter()),
        events=EventStore(settings.telemetry_path),
    )
    server = create_server(settings=settings, runtime=runtime)
    async with Client(server, raise_exceptions=True) as client:
        await client.call_tool(
            "resolve_fatsecret_capability",
            {"request": "autocomplete food suggestions"},
        )
        result = await client.call_tool(
            "fatsecret_foods_autocomplete", {"expression": "app"}
        )
    assert result.is_error is False
    assert result.structured_content == {"data": [{"food_name": "Apple"}]}
    assert fake.calls == [("foods", "autocomplete_v2", {"expression": "app"})]


@pytest.mark.anyio
async def test_dynamic_mutation_requires_curated_wrapper(tmp_path) -> None:
    server = create_server(
        settings=Settings(
            state_dir=tmp_path,
            telemetry_enabled=False,
            allow_dynamic_mutations=True,
        )
    )
    async with Client(server, raise_exceptions=True) as client:
        result = await client.call_tool(
            "resolve_fatsecret_capability",
            {"request": "commit exercise entries for a day", "max_tools": 1},
        )
    assert result.structured_content["activated"] == []
    assert result.structured_content["blocked"] == [
        {
            "tool_name": "fatsecret_exercises_entries_commit_day",
            "reason": "reviewed_wrapper_required",
        }
    ]
