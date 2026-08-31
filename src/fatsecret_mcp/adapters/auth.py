"""Bootstrap-only credential and OAuth operations."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any, Protocol, cast

import keyring
from fatsecret import Fatsecret

from ..settings import Settings


class KeyringBackend(Protocol):
    def get_password(self, service_name: str, username: str) -> str | None: ...

    def set_password(self, service_name: str, username: str, password: str) -> None: ...


class CredentialStore:
    SERVICE_NAME = "fatsecret-mcp"

    def __init__(
        self, settings: Settings, backend: KeyringBackend | None = None
    ) -> None:
        self.settings = settings
        self.backend = backend or keyring
        self._lock = threading.Lock()

    def load(self) -> dict[str, str]:
        values = {
            "client_id": self.settings.official_client_id,
            "client_secret": self.settings.official_client_secret,
            "access_token": self.settings.official_access_token,
            "access_token_secret": self.settings.official_access_token_secret,
        }
        values = {
            key: value or self.backend.get_password(self.SERVICE_NAME, key)
            for key, value in values.items()
        }
        return {key: value for key, value in values.items() if value}

    def update(self, **changes: str) -> None:
        with self._lock:
            for key, value in changes.items():
                if value:
                    self.backend.set_password(self.SERVICE_NAME, key, value)


class AuthAdapter:
    def __init__(
        self, settings: Settings, store: CredentialStore | None = None
    ) -> None:
        self.settings = settings
        self.store = store or CredentialStore(settings)
        self._pending: dict[str, tuple[float, Fatsecret]] = {}
        self._pending_lock = threading.Lock()

    def set_credentials(self, client_id: str, client_secret: str) -> dict[str, bool]:
        self.store.update(client_id=client_id, client_secret=client_secret)
        return {"configured": True}

    def start_oauth(self, flow_id: str, callback_url: str = "oob") -> dict[str, str]:
        credentials = self.store.load()
        client = Fatsecret(
            credentials["client_id"], credentials["client_secret"], retries=False
        )
        authorize_url = client.get_authorize_url(callback_url)
        with self._pending_lock:
            self._expire_pending()
            previous = self._pending.pop(flow_id, None)
            if previous is not None:
                previous[1].close()
            self._pending[flow_id] = (time.monotonic() + 600, client)
        return {"authorize_url": authorize_url, "callback_url": callback_url}

    def complete_oauth(self, flow_id: str, verifier: str) -> dict[str, bool]:
        with self._pending_lock:
            self._expire_pending()
            pending = self._pending.pop(flow_id, None)
        if pending is None:
            raise RuntimeError("start_oauth_flow must run in this server process first")
        client = pending[1]
        try:
            token, secret = client.authenticate(verifier)
            self.store.update(access_token=token, access_token_secret=secret)
        finally:
            client.close()
        return {"authenticated": True}

    def _expire_pending(self) -> None:
        now = time.monotonic()
        expired = [
            key for key, (deadline, _) in self._pending.items() if deadline <= now
        ]
        for key in expired:
            self._pending.pop(key)[1].close()

    def password(self, username: str, password: str) -> dict[str, bool]:
        credentials = self.store.load()
        authenticate = cast(
            Callable[[str, str, str, str], Any],
            getattr(Fatsecret, "fatsecret_authenticate"),  # noqa: B009
        )
        client = authenticate(
            username,
            password,
            credentials["client_id"],
            credentials["client_secret"],
        )
        if client is None or not client.access_token or not client.access_token_secret:
            raise RuntimeError("FatSecret password authentication failed")
        self.store.update(
            access_token=client.access_token,
            access_token_secret=client.access_token_secret,
        )
        client.close()
        return {"authenticated": True}

    def status(self) -> dict[str, Any]:
        credentials = self.store.load()
        return {
            "official_credentials_configured": all(
                key in credentials for key in ("client_id", "client_secret")
            ),
            "official_user_authenticated": all(
                key in credentials for key in ("access_token", "access_token_secret")
            ),
            "member_credentials_configured": bool(
                self.settings.member_username and self.settings.member_password
            ),
            "profile": self.settings.profile,
        }


__all__ = ["AuthAdapter", "CredentialStore"]
