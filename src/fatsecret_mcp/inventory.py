"""Reviewed discovery of latest public operations in the installed backend."""

from __future__ import annotations

import inspect
import re
from dataclasses import dataclass
from typing import Any, get_type_hints

from fatsecret import resources

_VERSIONED = re.compile(r"^(?P<family>[a-z][a-z0-9_]*)_v(?P<version>[1-9][0-9]*)$")

# This is the exposure source of truth. Reflection selects versions and schemas
# only after a resource/family pair has been reviewed and added here.
REVIEWED_FAMILIES = frozenset(
    {
        ("classification", "brands_get"),
        ("classification", "categories_get"),
        ("classification", "sub_categories_get"),
        ("diary", "entries_copy"),
        ("diary", "entries_copy_saved_meal"),
        ("diary", "entries_get"),
        ("diary", "entries_get_month"),
        ("diary", "entry_create"),
        ("diary", "entry_delete"),
        ("diary", "entry_edit"),
        ("exercises", "entries_commit_day"),
        ("exercises", "entries_get"),
        ("exercises", "entries_get_month"),
        ("exercises", "entries_save_template"),
        ("exercises", "entry_edit"),
        ("exercises", "list"),
        ("feedback", "submit"),
        ("foods", "autocomplete"),
        ("foods", "find_id_for_barcode"),
        ("foods", "get"),
        ("foods", "search"),
        ("meals", "create"),
        ("meals", "delete"),
        ("meals", "edit"),
        ("meals", "get"),
        ("meals", "item_add"),
        ("meals", "item_delete"),
        ("meals", "item_edit"),
        ("meals", "items_get"),
        ("native", "image_recognition"),
        ("native", "natural_language_processing"),
        ("profile", "create"),
        ("profile", "get"),
        ("profile", "get_auth"),
        ("profile_foods", "add_favorite"),
        ("profile_foods", "create"),
        ("profile_foods", "delete_favorite"),
        ("profile_foods", "get_favorites"),
        ("profile_foods", "get_most_eaten"),
        ("profile_foods", "get_recently_eaten"),
        ("recipes", "add_favorite"),
        ("recipes", "delete_favorite"),
        ("recipes", "get"),
        ("recipes", "get_favorites"),
        ("recipes", "search"),
        ("recipes", "types_get"),
        ("weight", "get_month"),
        ("weight", "update"),
    }
)

MUTATING_FAMILIES = frozenset(
    {
        ("diary", "entries_copy"),
        ("diary", "entries_copy_saved_meal"),
        ("diary", "entry_create"),
        ("diary", "entry_delete"),
        ("diary", "entry_edit"),
        ("exercises", "entries_commit_day"),
        ("exercises", "entries_save_template"),
        ("exercises", "entry_edit"),
        ("feedback", "submit"),
        ("meals", "create"),
        ("meals", "delete"),
        ("meals", "edit"),
        ("meals", "item_add"),
        ("meals", "item_delete"),
        ("meals", "item_edit"),
        ("profile", "create"),
        ("profile_foods", "add_favorite"),
        ("profile_foods", "create"),
        ("profile_foods", "delete_favorite"),
        ("recipes", "add_favorite"),
        ("recipes", "delete_favorite"),
        ("weight", "update"),
    }
)

RESOURCE_TYPES: dict[str, type[Any]] = {
    "classification": resources.ClassificationResource,
    "diary": resources.DiaryResource,
    "exercises": resources.ExercisesResource,
    "feedback": resources.FeedbackResource,
    "foods": resources.FoodsResource,
    "meals": resources.MealsResource,
    "native": resources.NativeResource,
    "profile_foods": resources.ProfileFoodsResource,
    "profile": resources.ProfileResource,
    "recipes": resources.RecipesResource,
    "weight": resources.WeightResource,
}


@dataclass(frozen=True, slots=True)
class LibraryCapability:
    capability_id: str
    tool_name: str
    resource: str
    family: str
    method: str
    version: int
    description: str
    signature: inspect.Signature
    mutation: bool
    destructive: bool
    access_requirement: str | None


def build_latest_inventory() -> tuple[LibraryCapability, ...]:
    """Select one highest numeric version for each public resource family."""

    selected: dict[tuple[str, str], tuple[int, str, Any]] = {}
    for resource_name, resource_type in RESOURCE_TYPES.items():
        for method_name, function in inspect.getmembers(
            resource_type, inspect.isfunction
        ):
            match = _VERSIONED.fullmatch(method_name)
            if match is None:
                continue
            if "DEPRECATED upstream" in (inspect.getdoc(function) or ""):
                continue
            family = match.group("family")
            if (resource_name, family) not in REVIEWED_FAMILIES:
                continue
            version = int(match.group("version"))
            key = (resource_name, family)
            if key not in selected or version > selected[key][0]:
                selected[key] = (version, method_name, function)

    capabilities = []
    for (resource_name, family), (version, method_name, function) in selected.items():
        raw_signature = inspect.signature(function)
        hints = get_type_hints(function, include_extras=True)
        signature = raw_signature.replace(
            parameters=[
                parameter.replace(annotation=hints.get(name, parameter.annotation))
                for name, parameter in raw_signature.parameters.items()
                if name != "self"
            ],
            return_annotation=hints.get("return", raw_signature.return_annotation),
        )
        doc = inspect.getdoc(function) or ""
        destructive = "delete" in family.split("_")
        access_requirement = "premier" if "Premier-only" in doc else None
        capabilities.append(
            LibraryCapability(
                capability_id=f"official.{resource_name}.{family.replace('_', '.')}",
                tool_name=f"fatsecret_{resource_name}_{family}",
                resource=resource_name,
                family=family,
                method=method_name,
                version=version,
                description=(doc or f"Call {resource_name}.{method_name}").split(
                    "\n\n", 1
                )[0],
                signature=signature,
                mutation=(resource_name, family) in MUTATING_FAMILIES,
                destructive=destructive,
                access_requirement=access_requirement,
            )
        )
    return tuple(sorted(capabilities, key=lambda item: item.capability_id))


def search_inventory(
    request: str,
    inventory: tuple[LibraryCapability, ...],
    *,
    limit: int = 5,
) -> list[tuple[LibraryCapability, float]]:
    terms = set(re.findall(r"[a-z0-9]+", request.lower()))
    if not terms:
        return []
    matches = []
    for item in inventory:
        words = set(
            re.findall(
                r"[a-z0-9]+",
                f"{item.capability_id} {item.tool_name} {item.resource} "
                f"{item.method} {item.description}".lower(),
            )
        )
        overlap = terms & words
        if overlap:
            weighted = float(len(overlap))
            if item.resource == "diary" and terms & {"diary", "meal"}:
                weighted += 2
            if item.resource == "exercises" and "food" in terms:
                weighted -= 2
            if "update" in terms and "edit" in item.method:
                weighted += 1
            matches.append((item, max(0.0, weighted) / len(terms)))
    return sorted(matches, key=lambda pair: (-pair[1], pair[0].tool_name))[:limit]


__all__ = [
    "MUTATING_FAMILIES",
    "REVIEWED_FAMILIES",
    "LibraryCapability",
    "build_latest_inventory",
    "search_inventory",
]
