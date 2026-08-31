"""Typed MCP tool registration and on-demand capability reaching."""

from __future__ import annotations

import inspect
import json
import re
from collections.abc import Callable
from hashlib import sha256
from typing import Any

from fatsecret.web.models import WebIngredientWrite, WebMealType, WebRecipeWrite
from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp.types import ToolAnnotations

from .catalog import BY_NAME, ToolSpec, resolve_capabilities, tools_for_profile
from .inputs import (
    CaloriesPerDay,
    IdempotencyKey,
    ISODate,
    MaxResults,
    MealType,
    NonNegativeMinutes,
    PageNumber,
    PositiveAmount,
    PositiveId,
    ResolverLimit,
)
from .inventory import LibraryCapability, build_latest_inventory, search_inventory
from .runtime import Runtime

_CURATED_OFFICIAL_CAPABILITIES = frozenset(
    {
        "official.foods.search",
        "official.foods.get",
        "official.recipes.search",
        "official.recipes.get",
        "official.profile.get",
        "official.diary.entries.get",
        "official.diary.entry.create",
        "official.weight.get.month",
    }
)


class ToolRegistry:
    def __init__(self, server: MCPServer, runtime: Runtime) -> None:
        self.server = server
        self.runtime = runtime
        self.functions = _curated_functions(runtime, self)
        self.inventory = tuple(
            item
            for item in build_latest_inventory()
            if item.capability_id not in _CURATED_OFFICIAL_CAPABILITIES
        )
        self.active: set[str] = set()
        self.dynamic_count = 0

    def register_profile(self) -> None:
        for spec in tools_for_profile(self.runtime.settings.profile):
            self.activate_curated(spec)

    def activate_curated(self, spec: ToolSpec) -> bool:
        if spec.name in self.active:
            return False
        self._add(spec, self.functions[spec.name])
        return True

    def activate_library(self, capability: LibraryCapability) -> bool:
        if capability.tool_name in self.active:
            return False
        function = self._make_library_function(capability)
        self.server.add_tool(
            function,
            name=capability.tool_name,
            description=capability.description,
            annotations=ToolAnnotations(
                read_only_hint=not capability.mutation,
                destructive_hint=capability.destructive,
                idempotent_hint=not capability.mutation,
                open_world_hint=True,
            ),
            meta={
                "fatsecret": {
                    "capabilityId": capability.capability_id,
                    "resource": capability.resource,
                    "pythonMethod": capability.method,
                    "selectedVersion": capability.version,
                    "accessRequirement": capability.access_requirement,
                    "exposure": "on-demand",
                }
            },
            structured_output=True,
        )
        self.active.add(capability.tool_name)
        self.dynamic_count += 1
        return True

    def _add(self, spec: ToolSpec, function: Callable[..., Any]) -> None:
        self.server.add_tool(
            function,
            name=spec.name,
            description=inspect.getdoc(function),
            annotations=ToolAnnotations(
                read_only_hint=spec.read_only,
                destructive_hint=spec.destructive,
                idempotent_hint=spec.idempotent,
                open_world_hint=True,
            ),
            meta={
                "fatsecret": {
                    "capabilityId": spec.capability_id,
                    "category": spec.category.value,
                    "operationId": spec.operation_id,
                    "source": spec.source,
                    "selectedVersion": spec.version,
                    "accessRequirement": spec.access_requirement,
                }
            },
            structured_output=True,
        )
        self.active.add(spec.name)

    def _make_library_function(
        self, capability: LibraryCapability
    ) -> Callable[..., Any]:
        async def invoke(ctx: Context | None = None, **kwargs: Any) -> dict[str, Any]:
            return await self.runtime.invoke(
                capability.tool_name,
                lambda **arguments: self.runtime.official.call(
                    capability.resource,
                    capability.method,
                    {
                        key: value
                        for key, value in arguments.items()
                        if value is not None
                    },
                ),
                kwargs,
                ctx,
            )

        invoke.__name__ = capability.tool_name
        invoke.__qualname__ = capability.tool_name
        invoke.__doc__ = capability.description
        invoke.__signature__ = capability.signature.replace(  # type: ignore[attr-defined]
            parameters=[
                *capability.signature.parameters.values(),
                inspect.Parameter(
                    "ctx",
                    inspect.Parameter.KEYWORD_ONLY,
                    default=None,
                    annotation=Context | None,
                ),
            ],
            return_annotation=dict[str, Any],
        )
        return invoke

    async def resolve(
        self, request: str, max_tools: int, context: Context | None
    ) -> dict[str, Any]:
        if context is None:
            raise RuntimeError("MCP request context is unavailable")
        max_tools = max(1, min(max_tools, 5))
        curated = resolve_capabilities(request, limit=max_tools)
        library = search_inventory(request, self.inventory, limit=max_tools)
        combined: list[tuple[str, str, float, ToolSpec | LibraryCapability]] = []
        for item, score in curated:
            combined.append((item.capability_id, item.name, score + 0.01, item))
        for item, score in library:
            combined.append((item.capability_id, item.tool_name, score, item))
        combined.sort(key=lambda row: (-row[2], row[1]))
        selected = combined[:max_tools]
        activated: list[str] = []
        blocked: list[dict[str, str]] = []

        can_activate = self.runtime.settings.transport == "stdio"
        for capability_id, tool_name, _score, item in selected:
            if tool_name in self.active:
                continue
            if not can_activate:
                blocked.append({"tool_name": tool_name, "reason": "restart_required"})
                continue
            if self.dynamic_count >= 8:
                blocked.append(
                    {"tool_name": tool_name, "reason": "session_activation_limit"}
                )
                continue
            if isinstance(item, ToolSpec):
                if item.bootstrap_restricted:
                    blocked.append(
                        {"tool_name": tool_name, "reason": "bootstrap_restricted"}
                    )
                    continue
                if (
                    not item.read_only
                    and not self.runtime.settings.allow_dynamic_mutations
                ):
                    blocked.append(
                        {
                            "tool_name": tool_name,
                            "reason": "mutation_activation_disabled",
                        }
                    )
                    continue
                if self.activate_curated(item):
                    activated.append(tool_name)
                    self.dynamic_count += 1
            else:
                # Dynamic writes bypass operation-specific idempotency and
                # reconciliation. Add a curated wrapper before exposing one.
                if item.mutation:
                    blocked.append(
                        {
                            "tool_name": tool_name,
                            "reason": "reviewed_wrapper_required",
                        }
                    )
                    continue
                if self.activate_library(item):
                    activated.append(tool_name)

        status = "activated" if activated else ("matched" if selected else "not_found")
        normalized_intent = " ".join(re.findall(r"[a-z0-9]+", request.lower()))
        intent_fingerprint = sha256(
            f"{self.runtime._process_id}\0{normalized_intent}".encode()
        ).hexdigest()[:24]
        self.runtime.events.emit(
            "capability.resolved",
            session_id=self.runtime._session_id(context),
            trace_id=context.request_id,
            profile=self.runtime.settings.profile,
            status=status,
            attributes={
                "candidate_capability_ids": [row[0] for row in combined],
                "candidate_rankings": [
                    {
                        "rank": rank,
                        "capability_id": row[0],
                        "score": round(row[2], 3),
                        "active_before": row[1] in self.active
                        and row[1] not in activated,
                    }
                    for rank, row in enumerate(combined, start=1)
                ],
                "selected_tool_names": [row[1] for row in selected],
                "activated_tool_names": activated,
                "blocked_reason_codes": [item["reason"] for item in blocked],
                "intent_fingerprint": intent_fingerprint,
            },
        )
        if activated:
            advertised = {tool.name: tool for tool in await self.server.list_tools()}
            schema_bytes = sum(
                len(
                    json.dumps(
                        advertised[name].input_schema,
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode()
                )
                for name in activated
            )
            await context.notify_tools_changed()
            self.runtime.events.emit(
                "tools.list_changed_published",
                session_id=self.runtime._session_id(context),
                trace_id=context.request_id,
                profile=self.runtime.settings.profile,
                status="ok",
                attributes={
                    "activated_tool_names": activated,
                    "schema_bytes_added": schema_bytes,
                },
            )
        return {
            "status": status,
            "selected": [
                {
                    "capability_id": capability_id,
                    "tool_name": tool_name,
                    "confidence": round(score, 3),
                    "access_requirement": _item.access_requirement,
                }
                for capability_id, tool_name, score, _item in selected
            ],
            "activated": activated,
            "blocked": blocked,
            "refresh_required": bool(activated),
        }


def _curated_functions(
    runtime: Runtime, registry: ToolRegistry
) -> dict[str, Callable[..., Any]]:
    async def set_credentials(
        client_id: str, client_secret: str, ctx: Context
    ) -> dict[str, Any]:
        """Set FatSecret Platform client credentials in the protected local store."""
        return await runtime.invoke(
            "set_credentials",
            runtime.auth.set_credentials,
            locals_without_context(locals()),
            ctx,
        )

    async def start_oauth_flow(
        callback_url: str = "oob", ctx: Context | None = None
    ) -> dict[str, Any]:
        """Start delegated FatSecret OAuth and return its authorization URL."""
        return await runtime.invoke(
            "start_oauth_flow",
            runtime.auth.start_oauth,
            {
                "flow_id": runtime._session_id(ctx),
                "callback_url": callback_url,
            },
            ctx,
        )

    async def complete_oauth_flow(verifier: str, ctx: Context) -> dict[str, Any]:
        """Complete the pending delegated OAuth flow with its verifier."""
        return await runtime.invoke(
            "complete_oauth_flow",
            runtime.auth.complete_oauth,
            {"flow_id": runtime._session_id(ctx), "verifier": verifier},
            ctx,
        )

    async def authenticate_with_password(
        username: str, password: str, ctx: Context
    ) -> dict[str, Any]:
        """Bootstrap delegated OAuth using FatSecret member credentials."""
        return await runtime.invoke(
            "authenticate_with_password",
            runtime.auth.password,
            locals_without_context(locals()),
            ctx,
        )

    async def check_auth_status(ctx: Context) -> dict[str, Any]:
        """Report configured authentication modes without returning secrets."""
        return await runtime.invoke("check_auth_status", runtime.auth.status, {}, ctx)

    async def search_foods(
        search_expression: str,
        page_number: PageNumber = 0,
        max_results: MaxResults = 20,
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        """Search the FatSecret food catalog using the latest reviewed endpoint."""
        return await runtime.invoke(
            "search_foods",
            runtime.official.search_foods,
            locals_without_context(locals()),
            ctx,
        )

    async def get_food(food_id: PositiveId, ctx: Context) -> dict[str, Any]:
        """Get one public FatSecret food by exact food ID."""
        return await runtime.invoke(
            "get_food", runtime.official.get_food, locals_without_context(locals()), ctx
        )

    async def search_recipes(
        search_expression: str,
        page_number: PageNumber = 0,
        max_results: MaxResults = 20,
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        """Search the public FatSecret recipe catalog."""
        return await runtime.invoke(
            "search_recipes",
            runtime.official.search_recipes,
            locals_without_context(locals()),
            ctx,
        )

    async def get_recipe(recipe_id: PositiveId, ctx: Context) -> dict[str, Any]:
        """Get one public catalog recipe by exact recipe ID."""
        return await runtime.invoke(
            "get_recipe",
            runtime.official.get_recipe,
            locals_without_context(locals()),
            ctx,
        )

    async def get_user_profile(ctx: Context) -> dict[str, Any]:
        """Get the delegated FatSecret Platform user profile."""
        return await runtime.invoke(
            "get_user_profile", runtime.official.get_profile, {}, ctx
        )

    async def get_user_food_entries(
        date: ISODate | None = None, ctx: Context | None = None
    ) -> dict[str, Any]:
        """Get delegated user food diary entries for an ISO date."""
        return await runtime.invoke(
            "get_user_food_entries",
            runtime.official.get_food_entries,
            locals_without_context(locals()),
            ctx,
        )

    async def add_food_entry(
        food_id: PositiveId,
        serving_id: PositiveId,
        quantity: PositiveAmount,
        meal_type: MealType,
        idempotency_key: IdempotencyKey,
        date: ISODate | None = None,
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        """Idempotently add an exact food and serving to the user's diary."""
        return await runtime.invoke(
            "add_food_entry",
            runtime.official.add_food_entry,
            locals_without_context(locals()),
            ctx,
        )

    async def get_weight_month(
        date: ISODate | None = None, ctx: Context | None = None
    ) -> dict[str, Any]:
        """Get delegated user weight entries for the month containing an ISO date."""
        return await runtime.invoke(
            "get_weight_month",
            runtime.official.get_weight_month,
            locals_without_context(locals()),
            ctx,
        )

    async def get_member_rdi(ctx: Context) -> dict[str, Any]:
        """Get the member website's saved recommended daily intake."""
        return await runtime.invoke("get_member_rdi", runtime.member.get_rdi, {}, ctx)

    async def set_member_rdi(
        calories_per_day: CaloriesPerDay, ctx: Context
    ) -> dict[str, Any]:
        """Replace and verify the member website's daily calorie target."""
        return await runtime.invoke(
            "set_member_rdi",
            runtime.member.set_rdi,
            locals_without_context(locals()),
            ctx,
        )

    async def list_member_recipes(ctx: Context) -> dict[str, Any]:
        """List recipes owned by the authenticated member account."""
        return await runtime.invoke(
            "list_member_recipes", runtime.member.list_recipes, {}, ctx
        )

    async def get_member_recipe(recipe_id: PositiveId, ctx: Context) -> dict[str, Any]:
        """Get an owned recipe with metadata and hydrated ingredients."""
        return await runtime.invoke(
            "get_member_recipe",
            runtime.member.get_recipe,
            locals_without_context(locals()),
            ctx,
        )

    async def create_member_recipe(
        title: str,
        description: str,
        servings: PositiveAmount,
        prep_minutes: NonNegativeMinutes,
        cook_minutes: NonNegativeMinutes,
        idempotency_key: IdempotencyKey,
        meal_types: list[WebMealType] | None = None,
        directions: list[str] | None = None,
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        """Create and verify an owned recipe using a durable idempotency key."""
        recipe = WebRecipeWrite(
            title=title,
            description=description,
            servings=servings,
            prep_minutes=prep_minutes,
            cook_minutes=cook_minutes,
            meal_types=meal_types or [],
            directions=directions or [],
        )
        return await runtime.invoke(
            "create_member_recipe",
            runtime.member.create_recipe,
            {"recipe": recipe, "idempotency_key": idempotency_key},
            ctx,
        )

    async def replace_member_recipe(
        recipe_id: PositiveId,
        title: str,
        description: str,
        servings: PositiveAmount,
        prep_minutes: NonNegativeMinutes,
        cook_minutes: NonNegativeMinutes,
        meal_types: list[WebMealType] | None = None,
        directions: list[str] | None = None,
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        """Fully replace and verify writable metadata for an owned recipe."""
        recipe = WebRecipeWrite(
            title=title,
            description=description,
            servings=servings,
            prep_minutes=prep_minutes,
            cook_minutes=cook_minutes,
            meal_types=meal_types or [],
            directions=directions or [],
        )
        return await runtime.invoke(
            "replace_member_recipe",
            runtime.member.replace_recipe,
            {"recipe_id": recipe_id, "recipe": recipe},
            ctx,
        )

    async def delete_member_recipe(
        recipe_id: PositiveId, ctx: Context
    ) -> dict[str, Any]:
        """Delete an owned recipe and verify that it is absent."""
        return await runtime.invoke(
            "delete_member_recipe",
            runtime.member.delete_recipe,
            locals_without_context(locals()),
            ctx,
        )

    async def list_member_food_portions(
        recipe_id: PositiveId, food_id: PositiveId, ctx: Context
    ) -> dict[str, Any]:
        """List member-site portions for an exact food ID in a recipe context."""
        return await runtime.invoke(
            "list_member_food_portions",
            runtime.member.list_portions,
            locals_without_context(locals()),
            ctx,
        )

    async def add_member_recipe_ingredient(
        recipe_id: PositiveId,
        food_id: PositiveId,
        amount: PositiveAmount,
        idempotency_key: IdempotencyKey,
        portion_id: int | None = None,
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        """Add and verify an exact food ID as an owned recipe ingredient."""
        ingredient = WebIngredientWrite(
            food_id=food_id, amount=amount, portion_id=portion_id
        )
        return await runtime.invoke(
            "add_member_recipe_ingredient",
            runtime.member.add_ingredient,
            {
                "recipe_id": recipe_id,
                "ingredient": ingredient,
                "idempotency_key": idempotency_key,
            },
            ctx,
        )

    async def replace_member_recipe_ingredient(
        recipe_id: PositiveId,
        entry_id: PositiveId,
        food_id: PositiveId,
        amount: PositiveAmount,
        portion_id: int | None = None,
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        """Replace and verify an owned recipe ingredient using an exact food ID."""
        ingredient = WebIngredientWrite(
            food_id=food_id, amount=amount, portion_id=portion_id
        )
        return await runtime.invoke(
            "replace_member_recipe_ingredient",
            runtime.member.replace_ingredient,
            {"recipe_id": recipe_id, "entry_id": entry_id, "ingredient": ingredient},
            ctx,
        )

    async def delete_member_recipe_ingredient(
        recipe_id: PositiveId, entry_id: PositiveId, ctx: Context
    ) -> dict[str, Any]:
        """Delete an owned recipe ingredient and verify that it is absent."""
        return await runtime.invoke(
            "delete_member_recipe_ingredient",
            runtime.member.delete_ingredient,
            locals_without_context(locals()),
            ctx,
        )

    async def copy_member_recipe(
        recipe_id: PositiveId, title: str, idempotency_key: IdempotencyKey, ctx: Context
    ) -> dict[str, Any]:
        """Start or resume a durable exact copy of an owned recipe."""
        return await runtime.invoke(
            "copy_member_recipe",
            runtime.member.copy_recipe,
            locals_without_context(locals()),
            ctx,
        )

    async def get_member_operation(operation_id: str, ctx: Context) -> dict[str, Any]:
        """Get durable member recipe-copy operation status."""
        return await runtime.invoke(
            "get_member_operation",
            runtime.member.get_operation,
            locals_without_context(locals()),
            ctx,
        )

    async def resume_member_operation(
        operation_id: str, ctx: Context
    ) -> dict[str, Any]:
        """Resume a durable member operation when its retry deadline permits."""
        return await runtime.invoke(
            "resume_member_operation",
            runtime.member.resume_operation,
            locals_without_context(locals()),
            ctx,
        )

    async def resolve_fatsecret_capability(
        request: str, max_tools: ResolverLimit = 1, ctx: Context | None = None
    ) -> dict[str, Any]:
        """Reach the reviewed backend inventory and activate only the selected tools."""
        return await registry.resolve(request, max_tools, ctx)

    return {name: value for name, value in locals().items() if name in BY_NAME}


def locals_without_context(values: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value for key, value in values.items() if key not in {"ctx", "context"}
    }


__all__ = ["ToolRegistry"]
