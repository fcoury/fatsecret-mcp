from __future__ import annotations

import pytest

from fatsecret_mcp.catalog import (
    BY_NAME,
    TOOLS,
    resolve_capabilities,
    tools_for_profile,
    validate_catalog,
)
from fatsecret_mcp.inventory import build_latest_inventory, search_inventory

EXAMPLE = {
    "set_credentials",
    "start_oauth_flow",
    "complete_oauth_flow",
    "authenticate_with_password",
    "check_auth_status",
    "search_foods",
    "get_food",
    "search_recipes",
    "get_recipe",
    "get_user_profile",
    "get_user_food_entries",
    "add_food_entry",
    "get_weight_month",
}
MEMBER = {
    "get_member_rdi",
    "set_member_rdi",
    "list_member_recipes",
    "get_member_recipe",
    "create_member_recipe",
    "replace_member_recipe",
    "delete_member_recipe",
    "list_member_food_portions",
    "add_member_recipe_ingredient",
    "replace_member_recipe_ingredient",
    "delete_member_recipe_ingredient",
    "copy_member_recipe",
    "get_member_operation",
    "resume_member_operation",
}


def names(profile: str) -> set[str]:
    return {item.name for item in tools_for_profile(profile)}


def test_catalog_is_exact_requested_surface_plus_resolver() -> None:
    assert len(TOOLS) == 28
    assert set(BY_NAME) == EXAMPLE | MEMBER | {"resolve_fatsecret_capability"}


def test_profiles_are_isolated() -> None:
    assert names("default") == MEMBER | {
        "check_auth_status",
        "resolve_fatsecret_capability",
    }
    assert names("discovery") == {
        "search_foods",
        "get_food",
        "search_recipes",
        "get_recipe",
        "check_auth_status",
        "resolve_fatsecret_capability",
    }
    assert names("full") == set(BY_NAME)
    with pytest.raises(ValueError, match="unknown tool profile"):
        tools_for_profile("missing")


def test_catalog_duplicate_validation() -> None:
    with pytest.raises(ValueError, match="duplicate catalog name"):
        validate_catalog((TOOLS[0], TOOLS[0]))


def test_curated_resolution_is_deterministic() -> None:
    first = resolve_capabilities("replace member recipe ingredient")
    second = resolve_capabilities("replace member recipe ingredient")
    assert first == second
    assert first[0][0].name == "replace_member_recipe_ingredient"


def test_latest_library_inventory_has_one_version_per_family() -> None:
    inventory = build_latest_inventory()
    ids = [item.capability_id for item in inventory]
    assert len(ids) == len(set(ids))
    selected = {item.capability_id: item for item in inventory}
    assert selected["official.foods.search"].method == "search_v5"
    assert selected["official.recipes.search"].method == "search_v3"
    assert selected["official.diary.entries.get"].method == "entries_get_v2"
    assert len(selected) == 48
    assert selected["official.exercises.entries.commit.day"].mutation is True
    assert selected["official.exercises.entries.save.template"].mutation is True
    assert selected["official.feedback.submit"].mutation is True


def test_library_resolution_prefers_food_diary_over_exercises() -> None:
    matches = search_inventory(
        "update an existing diary food entry quantity", build_latest_inventory()
    )
    assert matches[0][0].capability_id == "official.diary.entry.edit"
