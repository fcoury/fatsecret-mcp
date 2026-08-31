"""Stable tool catalog, profiles, and capability resolution metadata."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum


class ToolCategory(str, Enum):
    AUTHENTICATION = "authentication"
    CATALOG = "catalog"
    DIARY = "diary"
    MEMBER_READ = "member-read"
    MEMBER_WRITE = "member-write"
    MEMBER_COPY = "member-copy"
    RESOLVER = "resolver"


@dataclass(frozen=True, slots=True)
class ToolSpec:
    name: str
    category: ToolCategory
    capability_id: str
    handler: str
    operation_id: str | None = None
    source: str = "mcp"
    version: int | None = None
    access_requirement: str | None = None
    read_only: bool = True
    destructive: bool = False
    idempotent: bool = True
    bootstrap_restricted: bool = False
    keywords: tuple[str, ...] = ()


def _spec(
    name: str,
    category: ToolCategory,
    capability_id: str,
    handler: str,
    *,
    operation_id: str | None = None,
    source: str = "mcp",
    version: int | None = None,
    access_requirement: str | None = None,
    read_only: bool = True,
    destructive: bool = False,
    idempotent: bool = True,
    bootstrap_restricted: bool = False,
    keywords: tuple[str, ...] = (),
) -> ToolSpec:
    return ToolSpec(
        name=name,
        category=category,
        capability_id=capability_id,
        handler=handler,
        operation_id=operation_id,
        source=source,
        version=version,
        access_requirement=access_requirement,
        read_only=read_only,
        destructive=destructive,
        idempotent=idempotent,
        bootstrap_restricted=bootstrap_restricted,
        keywords=keywords,
    )


TOOLS: tuple[ToolSpec, ...] = (
    _spec(
        "set_credentials",
        ToolCategory.AUTHENTICATION,
        "auth.credentials.set",
        "auth.set_credentials",
        read_only=False,
        bootstrap_restricted=True,
        keywords=("client key secret",),
    ),
    _spec(
        "start_oauth_flow",
        ToolCategory.AUTHENTICATION,
        "auth.oauth.start",
        "auth.start_oauth",
        read_only=False,
        bootstrap_restricted=True,
        keywords=("authorize login",),
    ),
    _spec(
        "complete_oauth_flow",
        ToolCategory.AUTHENTICATION,
        "auth.oauth.complete",
        "auth.complete_oauth",
        read_only=False,
        bootstrap_restricted=True,
        keywords=("verifier pin token",),
    ),
    _spec(
        "authenticate_with_password",
        ToolCategory.AUTHENTICATION,
        "auth.password",
        "auth.password",
        read_only=False,
        bootstrap_restricted=True,
        keywords=("username password login",),
    ),
    _spec(
        "check_auth_status",
        ToolCategory.AUTHENTICATION,
        "auth.status",
        "auth.status",
        keywords=("authentication configured account",),
    ),
    _spec(
        "search_foods",
        ToolCategory.CATALOG,
        "foods.search",
        "official.search_foods",
        operation_id="foods_search_v5",
        source="official-oas",
        version=5,
        access_requirement="premier",
        keywords=("find food database",),
    ),
    _spec(
        "get_food",
        ToolCategory.CATALOG,
        "food.get",
        "official.get_food",
        operation_id="food_get_v5",
        source="official-oas",
        version=5,
        access_requirement="premier",
        keywords=("food id nutrition servings",),
    ),
    _spec(
        "search_recipes",
        ToolCategory.CATALOG,
        "recipes.search",
        "official.search_recipes",
        operation_id="recipes_search_v3",
        source="official-oas",
        version=3,
        access_requirement="premier",
        keywords=("find public recipe",),
    ),
    _spec(
        "get_recipe",
        ToolCategory.CATALOG,
        "recipe.get",
        "official.get_recipe",
        operation_id="recipe_get_v2",
        source="official-oas",
        version=2,
        access_requirement="premier",
        keywords=("public recipe id",),
    ),
    _spec(
        "get_user_profile",
        ToolCategory.DIARY,
        "profile.get",
        "official.get_profile",
        operation_id="profile_get_v1",
        source="official-oas",
        version=1,
        keywords=("user profile account",),
    ),
    _spec(
        "get_user_food_entries",
        ToolCategory.DIARY,
        "food_entries.get",
        "official.get_food_entries",
        operation_id="food_entries_get_v2",
        source="official-oas",
        version=2,
        keywords=("diary entries date",),
    ),
    _spec(
        "add_food_entry",
        ToolCategory.DIARY,
        "food_entry.create",
        "official.add_food_entry",
        operation_id="food_entry_create_v1",
        source="official-oas",
        version=1,
        read_only=False,
        idempotent=True,
        keywords=("log add diary food idempotency",),
    ),
    _spec(
        "get_weight_month",
        ToolCategory.DIARY,
        "weights.get_month",
        "official.get_weight_month",
        operation_id="weights_get_month_v2",
        source="official-oas",
        version=2,
        keywords=("weight history month",),
    ),
    _spec(
        "get_member_rdi",
        ToolCategory.MEMBER_READ,
        "member.rdi.get",
        "member.get_rdi",
        operation_id="getMemberRdi",
        source="member-web-oas",
        keywords=("calorie target rdi",),
    ),
    _spec(
        "set_member_rdi",
        ToolCategory.MEMBER_WRITE,
        "member.rdi.replace",
        "member.set_rdi",
        operation_id="replaceMemberRdi",
        source="member-web-oas",
        read_only=False,
        keywords=("set calorie target rdi",),
    ),
    _spec(
        "list_member_recipes",
        ToolCategory.MEMBER_READ,
        "member.recipes.list",
        "member.list_recipes",
        operation_id="listMemberRecipes",
        source="member-web-oas",
        keywords=("owned cookbook recipes",),
    ),
    _spec(
        "get_member_recipe",
        ToolCategory.MEMBER_READ,
        "member.recipe.get",
        "member.get_recipe",
        operation_id="getMemberRecipe",
        source="member-web-oas",
        keywords=("owned recipe ingredients",),
    ),
    _spec(
        "create_member_recipe",
        ToolCategory.MEMBER_WRITE,
        "member.recipe.create",
        "member.create_recipe",
        operation_id="createMemberRecipe",
        source="member-web-oas",
        read_only=False,
        idempotent=False,
        keywords=("new owned recipe",),
    ),
    _spec(
        "replace_member_recipe",
        ToolCategory.MEMBER_WRITE,
        "member.recipe.replace",
        "member.replace_recipe",
        operation_id="replaceMemberRecipe",
        source="member-web-oas",
        read_only=False,
        keywords=("update servings directions metadata",),
    ),
    _spec(
        "delete_member_recipe",
        ToolCategory.MEMBER_WRITE,
        "member.recipe.delete",
        "member.delete_recipe",
        operation_id="deleteMemberRecipe",
        source="member-web-oas",
        read_only=False,
        destructive=True,
        keywords=("remove owned recipe",),
    ),
    _spec(
        "list_member_food_portions",
        ToolCategory.MEMBER_READ,
        "member.food.portions.list",
        "member.list_portions",
        operation_id="listMemberFoodPortions",
        source="member-web-oas",
        keywords=("food id units grams serving portion",),
    ),
    _spec(
        "add_member_recipe_ingredient",
        ToolCategory.MEMBER_WRITE,
        "member.recipe.ingredient.add",
        "member.add_ingredient",
        operation_id="addMemberRecipeIngredient",
        source="member-web-oas",
        read_only=False,
        idempotent=False,
        keywords=("add exact food id ingredient grams",),
    ),
    _spec(
        "replace_member_recipe_ingredient",
        ToolCategory.MEMBER_WRITE,
        "member.recipe.ingredient.replace",
        "member.replace_ingredient",
        operation_id="replaceMemberRecipeIngredient",
        source="member-web-oas",
        read_only=False,
        keywords=("update exact food id ingredient amount",),
    ),
    _spec(
        "delete_member_recipe_ingredient",
        ToolCategory.MEMBER_WRITE,
        "member.recipe.ingredient.delete",
        "member.delete_ingredient",
        operation_id="deleteMemberRecipeIngredient",
        source="member-web-oas",
        read_only=False,
        destructive=True,
        keywords=("remove recipe ingredient",),
    ),
    _spec(
        "copy_member_recipe",
        ToolCategory.MEMBER_COPY,
        "member.recipe.copy",
        "member.copy_recipe",
        operation_id="copyMemberRecipe",
        source="member-web-oas",
        read_only=False,
        idempotent=False,
        keywords=("duplicate clone owned recipe",),
    ),
    _spec(
        "get_member_operation",
        ToolCategory.MEMBER_READ,
        "member.operation.get",
        "member.get_operation",
        operation_id="getMemberOperation",
        source="member-web-oas",
        keywords=("copy status retry waiting",),
    ),
    _spec(
        "resume_member_operation",
        ToolCategory.MEMBER_COPY,
        "member.operation.resume",
        "member.resume_operation",
        operation_id="resumeMemberOperation",
        source="member-web-oas",
        read_only=False,
        keywords=("continue copy retry waiting",),
    ),
    _spec(
        "resolve_fatsecret_capability",
        ToolCategory.RESOLVER,
        "mcp.capability.resolve",
        "resolver.resolve",
        keywords=("find reach activate unavailable tool operation",),
    ),
)

BY_NAME = {item.name: item for item in TOOLS}
BY_CAPABILITY = {item.capability_id: item for item in TOOLS}

PROFILE_CATEGORIES: dict[str, frozenset[ToolCategory]] = {
    "default": frozenset(
        {
            ToolCategory.MEMBER_READ,
            ToolCategory.MEMBER_WRITE,
            ToolCategory.MEMBER_COPY,
            ToolCategory.RESOLVER,
        }
    ),
    "member": frozenset(
        {
            ToolCategory.MEMBER_READ,
            ToolCategory.MEMBER_WRITE,
            ToolCategory.MEMBER_COPY,
            ToolCategory.RESOLVER,
        }
    ),
    "discovery": frozenset({ToolCategory.CATALOG, ToolCategory.RESOLVER}),
    "diary": frozenset({ToolCategory.DIARY, ToolCategory.RESOLVER}),
    "bootstrap": frozenset({ToolCategory.AUTHENTICATION, ToolCategory.RESOLVER}),
    "full": frozenset(ToolCategory),
}

PROFILE_INCLUDES: dict[str, frozenset[str]] = {
    "default": frozenset({"check_auth_status"}),
    "member": frozenset({"check_auth_status"}),
    "discovery": frozenset({"check_auth_status"}),
    "diary": frozenset({"check_auth_status"}),
}


def tools_for_profile(profile: str) -> tuple[ToolSpec, ...]:
    try:
        categories = PROFILE_CATEGORIES[profile]
    except KeyError as error:
        raise ValueError(f"unknown tool profile: {profile}") from error
    included = PROFILE_INCLUDES.get(profile, frozenset())
    return tuple(
        item for item in TOOLS if item.category in categories or item.name in included
    )


def resolve_capabilities(
    request: str, *, limit: int = 5
) -> list[tuple[ToolSpec, float]]:
    """Return deterministic lexical matches without exposing every tool schema."""

    terms = set(re.findall(r"[a-z0-9]+", request.lower()))
    if not terms:
        return []
    scored: list[tuple[ToolSpec, float]] = []
    for item in TOOLS:
        if item.category is ToolCategory.RESOLVER:
            continue
        haystack = " ".join(
            (item.name, item.capability_id, item.operation_id or "", *item.keywords)
        )
        words = set(re.findall(r"[a-z0-9]+", haystack.lower()))
        overlap = terms & words
        if overlap:
            scored.append((item, len(overlap) / len(terms)))
    return sorted(scored, key=lambda pair: (-pair[1], pair[0].name))[:limit]


def validate_catalog(items: Iterable[ToolSpec] = TOOLS) -> None:
    values = tuple(items)
    for attribute in ("name", "capability_id", "handler"):
        found = [getattr(item, attribute) for item in values]
        if len(found) != len(set(found)):
            raise ValueError(f"duplicate catalog {attribute}")


validate_catalog()
