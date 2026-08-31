"""Adapter for reviewed public methods on the official FatSecret client."""

from __future__ import annotations

import json
import threading
from datetime import date
from decimal import Decimal
from hashlib import sha256
from typing import Any, Protocol

from fatsecret import Fatsecret
from fatsecret.web.service import IdempotencyStore

from ..inventory import build_latest_inventory
from ..settings import Settings
from .member import json_value


class CredentialProvider(Protocol):
    def load(self) -> dict[str, str]: ...


class OfficialAdapter:
    def __init__(self, settings: Settings, credentials: CredentialProvider) -> None:
        self.settings = settings
        self.credentials = credentials
        self._client: Fatsecret | None = None
        self._credential_fingerprint: str | None = None
        self._lock = threading.RLock()
        settings.state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._idempotency = IdempotencyStore(settings.operations_path)
        self._latest_methods = {
            (item.resource, item.family): item.method
            for item in build_latest_inventory()
        }

    def _latest(self, resource: str, family: str) -> str:
        try:
            return self._latest_methods[(resource, family)]
        except KeyError as error:
            raise RuntimeError(
                f"reviewed FatSecret operation is unavailable: {resource}.{family}"
            ) from error

    def close(self) -> None:
        with self._lock:
            if self._client is not None:
                self._client.close()
                self._client = None

    def _get_client(self) -> Fatsecret:
        with self._lock:
            values = self.credentials.load()
            fingerprint = sha256(
                "\0".join(
                    values.get(key, "")
                    for key in (
                        "client_id",
                        "client_secret",
                        "access_token",
                        "access_token_secret",
                    )
                ).encode()
            ).hexdigest()
            if self._client is not None and fingerprint != self._credential_fingerprint:
                self._client.close()
                self._client = None
            if self._client is None:
                try:
                    client_id = values["client_id"]
                    client_secret = values["client_secret"]
                except KeyError as error:
                    raise RuntimeError(
                        "official tools require FATSECRET_CLIENT_ID and FATSECRET_CLIENT_SECRET"
                    ) from error
                token = None
                if values.get("access_token") and values.get("access_token_secret"):
                    token = (values["access_token"], values["access_token_secret"])
                self._client = Fatsecret(
                    client_id,
                    client_secret,
                    session_token=token,
                )
                self._credential_fingerprint = fingerprint
            return self._client

    def call(
        self, resource: str, method: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        prepared = {
            key: self._date(value) if key in {"date", "from_date", "to_date"} else value
            for key, value in arguments.items()
            if value is not None
        }
        client = self._get_client()
        result = getattr(getattr(client, resource), method)(**prepared)
        return {"data": json_value(result)}

    def search_foods(
        self, search_expression: str, page_number: int = 0, max_results: int = 20
    ) -> dict[str, Any]:
        return self.call(
            "foods",
            self._latest("foods", "search"),
            {
                "search_expression": search_expression,
                "page_number": page_number,
                "max_results": max_results,
            },
        )

    def get_food(self, food_id: int) -> dict[str, Any]:
        return self.call("foods", self._latest("foods", "get"), {"food_id": food_id})

    def search_recipes(
        self, search_expression: str, page_number: int = 0, max_results: int = 20
    ) -> dict[str, Any]:
        return self.call(
            "recipes",
            self._latest("recipes", "search"),
            {
                "search_expression": search_expression,
                "page_number": page_number,
                "max_results": max_results,
            },
        )

    def get_recipe(self, recipe_id: int) -> dict[str, Any]:
        return self.call(
            "recipes", self._latest("recipes", "get"), {"recipe_id": recipe_id}
        )

    def get_profile(self) -> dict[str, Any]:
        return self.call("profile", self._latest("profile", "get"), {})

    def get_food_entries(self, date: str | None = None) -> dict[str, Any]:
        return self.call("diary", self._latest("diary", "entries_get"), {"date": date})

    def add_food_entry(
        self,
        food_id: int,
        serving_id: int,
        quantity: Decimal,
        meal_type: str,
        idempotency_key: str,
        date: str | None = None,
    ) -> dict[str, Any]:
        food = getattr(self._get_client().foods, self._latest("foods", "get"))(food_id)
        if food is None or not food.food_name:
            raise ValueError(f"food {food_id} was not found")
        arguments = {
            "food_id": food_id,
            "food_entry_name": food.food_name,
            "serving_id": serving_id,
            "number_of_units": float(quantity),
            "meal": "other" if meal_type == "snack" else meal_type,
            "date": date,
        }
        scope = "official.diary.entry.create"
        with self._lock:
            existing = self._idempotency.begin(scope, idempotency_key, arguments)
            if existing is not None:
                if existing["state"] == "completed":
                    return json.loads(existing["response_json"])
                raise RuntimeError(
                    f"idempotent operation is {existing['state']}; reconcile before retry"
                )
            try:
                result = self.call(
                    "diary", self._latest("diary", "entry_create"), arguments
                )
            except Exception as error:
                self._idempotency.mark_unknown(scope, idempotency_key, error)
                raise
            self._idempotency.complete(
                scope, idempotency_key, status_code=201, response=result
            )
            return result

    def get_weight_month(self, date: str | None = None) -> dict[str, Any]:
        return self.call("weight", self._latest("weight", "get_month"), {"date": date})

    @staticmethod
    def _date(value: Any) -> Any:
        if isinstance(value, str):
            return date.fromisoformat(value)
        return value


__all__ = ["OfficialAdapter"]
