"""Application adapter for unofficial FatSecret member-site operations."""

from __future__ import annotations

import threading
from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from fatsecret import FatsecretWebClient
from fatsecret.web.models import (
    WebIngredientWrite,
    WebRecipeDetail,
    WebRecipeIngredient,
    WebRecipeWrite,
)
from fatsecret.web.service import (
    IdempotencyStore,
    RecipeCopyService,
    RecipeOperationStore,
)
from filelock import FileLock

from ..settings import Settings


def json_value(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, (list, tuple)):
        return [json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): json_value(item) for key, item in value.items()}
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return json_value(value.value)
    return value


class MemberAdapter:
    """Own durable state while creating short-lived authenticated web clients."""

    def __init__(
        self,
        settings: Settings,
        *,
        client_factory: Callable[[], FatsecretWebClient] | None = None,
    ) -> None:
        self.settings = settings
        settings.state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._client_factory = client_factory or self._new_client
        self._mutation_lock = threading.Lock()
        self._process_lock = FileLock(settings.state_dir / "member-mutations.lock")
        self._idempotency = IdempotencyStore(settings.operations_path)
        self._copy = RecipeCopyService(
            self._new_copy_client if client_factory is None else self._client_factory,
            RecipeOperationStore(settings.operations_path),
            mutation_lock=self._mutation_lock,
        )

    def _new_client(self) -> FatsecretWebClient:
        username, password = self._require_credentials()
        return FatsecretWebClient(username, password)

    def _new_copy_client(self) -> FatsecretWebClient:
        username, password = self._require_credentials()
        # RecipeCopyService persists the authoritative retry deadline and
        # resumes later; sleeping here would hide that durable waiting state.
        return FatsecretWebClient(username, password, wait_on_rate_limit=False)

    def _require_credentials(self) -> tuple[str, str]:
        username = self.settings.member_username
        password = self.settings.member_password
        if not username or not password:
            raise RuntimeError(
                "member tools require FATSECRET_USERNAME and FATSECRET_PASSWORD"
            )
        return username, password

    def _call(self, method: str, *args: object) -> Any:
        with self._client_factory() as client:
            return json_value(getattr(client, method)(*args))

    def get_rdi(self) -> Any:
        return self._call("get_rdi")

    def set_rdi(self, calories_per_day: int) -> Any:
        with self._process_lock, self._mutation_lock:
            return self._call("set_rdi", calories_per_day)

    def list_recipes(self) -> Any:
        items = self._call("list_recipes")
        return {"items": items, "count": len(items)}

    def get_recipe(self, recipe_id: int) -> Any:
        return self._call("get_recipe", recipe_id)

    def create_recipe(self, recipe: WebRecipeWrite, idempotency_key: str) -> Any:
        return self._idempotent_create(
            scope="member.recipe.create",
            key=idempotency_key,
            payload=recipe,
            model=WebRecipeDetail,
            status_code=201,
            callback=lambda: self._call("create_recipe", recipe),
        )

    def replace_recipe(self, recipe_id: int, recipe: WebRecipeWrite) -> Any:
        with self._process_lock, self._mutation_lock:
            return self._call("replace_recipe", recipe_id, recipe)

    def delete_recipe(self, recipe_id: int) -> Any:
        with self._process_lock, self._mutation_lock:
            return self._call("delete_recipe", recipe_id)

    def list_portions(self, recipe_id: int, food_id: int) -> Any:
        return self._call("list_food_portions", recipe_id, food_id)

    def add_ingredient(
        self,
        recipe_id: int,
        ingredient: WebIngredientWrite,
        idempotency_key: str,
    ) -> Any:
        return self._idempotent_create(
            scope=f"member.recipe.{recipe_id}.ingredient.add",
            key=idempotency_key,
            payload=ingredient,
            model=WebRecipeIngredient,
            status_code=201,
            callback=lambda: self._call("add_recipe_ingredient", recipe_id, ingredient),
        )

    def replace_ingredient(
        self, recipe_id: int, entry_id: int, ingredient: WebIngredientWrite
    ) -> Any:
        with self._process_lock, self._mutation_lock:
            return self._call(
                "replace_recipe_ingredient", recipe_id, entry_id, ingredient
            )

    def delete_ingredient(self, recipe_id: int, entry_id: int) -> Any:
        with self._process_lock, self._mutation_lock:
            return {
                "recipe_id": recipe_id,
                "entry_id": entry_id,
                "deleted": self._call("delete_recipe_ingredient", recipe_id, entry_id),
            }

    def copy_recipe(self, recipe_id: int, title: str, idempotency_key: str) -> Any:
        with self._process_lock:
            operation = self._copy.start_copy(recipe_id, title, idempotency_key)
            return json_value(self._copy.run_copy(operation.operation_id))

    def get_operation(self, operation_id: str) -> Any:
        operation = self._copy.get_copy(operation_id)
        if operation is None:
            raise KeyError(f"member operation {operation_id} was not found")
        return json_value(operation)

    def resume_operation(self, operation_id: str) -> Any:
        if self._copy.get_copy(operation_id) is None:
            raise KeyError(f"member operation {operation_id} was not found")
        with self._process_lock:
            return json_value(self._copy.run_copy(operation_id))

    def _idempotent_create(
        self,
        *,
        scope: str,
        key: str,
        payload: object,
        model: type[WebRecipeDetail | WebRecipeIngredient],
        status_code: int,
        callback: Callable[[], Any],
    ) -> Any:
        payload_json = json_value(payload)
        self._require_credentials()
        with self._process_lock, self._mutation_lock:
            existing = self._idempotency.begin(scope, key, payload_json)
            if existing is not None:
                if existing["state"] == "completed":
                    return model.model_validate_json(
                        existing["response_json"]
                    ).model_dump(mode="json")
                raise RuntimeError(
                    f"idempotent operation is {existing['state']}; reconcile before retry"
                )
            try:
                result = callback()
            except Exception as error:
                self._idempotency.mark_unknown(scope, key, error)
                raise
            self._idempotency.complete(
                scope,
                key,
                status_code=status_code,
                response=result,
            )
            return result


__all__ = ["MemberAdapter", "json_value"]
