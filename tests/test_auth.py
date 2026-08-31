from __future__ import annotations

from fatsecret_mcp.adapters.auth import AuthAdapter, CredentialStore
from fatsecret_mcp.settings import Settings


class FakeKeyring:
    def __init__(self) -> None:
        self.values: dict[tuple[str, str], str] = {}

    def get_password(self, service_name: str, username: str) -> str | None:
        return self.values.get((service_name, username))

    def set_password(self, service_name: str, username: str, password: str) -> None:
        self.values[(service_name, username)] = password


def test_credentials_use_keyring_and_environment_takes_precedence(tmp_path) -> None:
    backend = FakeKeyring()
    settings = Settings(state_dir=tmp_path, official_client_id="environment-id")
    store = CredentialStore(settings, backend)
    store.update(client_id="stored-id", client_secret="stored-secret")
    assert store.load() == {
        "client_id": "environment-id",
        "client_secret": "stored-secret",
    }


def test_auth_status_never_returns_secret_values(tmp_path) -> None:
    backend = FakeKeyring()
    settings = Settings(
        state_dir=tmp_path, member_username="member", member_password="secret"
    )
    store = CredentialStore(settings, backend)
    store.update(
        client_id="id",
        client_secret="client-secret",
        access_token="token",
        access_token_secret="token-secret",
    )
    result = AuthAdapter(settings, store).status()
    assert result["official_credentials_configured"] is True
    assert result["official_user_authenticated"] is True
    assert result["member_credentials_configured"] is True
    assert "secret" not in repr(result)
