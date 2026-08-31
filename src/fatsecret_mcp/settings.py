"""Environment-backed server configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _env_path(name: str, default: str) -> Path:
    return Path(os.environ.get(name, default)).expanduser()


@dataclass(frozen=True, slots=True)
class Settings:
    profile: str = "default"
    transport: str = "stdio"
    host: str = "127.0.0.1"
    port: int = 8000
    state_dir: Path = field(
        default_factory=lambda: Path("~/.local/state/fatsecret-mcp").expanduser()
    )
    telemetry_enabled: bool = True
    allow_dynamic_mutations: bool = False
    official_client_id: str | None = None
    official_client_secret: str | None = None
    official_access_token: str | None = None
    official_access_token_secret: str | None = None
    member_username: str | None = None
    member_password: str | None = None

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            profile=os.environ.get("FATSECRET_MCP_PROFILE", "default"),
            transport=os.environ.get("FATSECRET_MCP_TRANSPORT", "stdio"),
            host=os.environ.get("FATSECRET_MCP_HOST", "127.0.0.1"),
            port=int(os.environ.get("FATSECRET_MCP_PORT", "8000")),
            state_dir=_env_path(
                "FATSECRET_MCP_STATE_DIR", "~/.local/state/fatsecret-mcp"
            ),
            telemetry_enabled=os.environ.get("FATSECRET_MCP_TELEMETRY", "1")
            not in {"0", "false", "False"},
            allow_dynamic_mutations=os.environ.get(
                "FATSECRET_MCP_DYNAMIC_MUTATIONS", "0"
            )
            in {"1", "true", "True"},
            official_client_id=os.environ.get("FATSECRET_CLIENT_ID"),
            official_client_secret=os.environ.get("FATSECRET_CLIENT_SECRET"),
            official_access_token=os.environ.get("FATSECRET_ACCESS_TOKEN"),
            official_access_token_secret=os.environ.get(
                "FATSECRET_ACCESS_TOKEN_SECRET"
            ),
            member_username=os.environ.get("FATSECRET_USERNAME"),
            member_password=os.environ.get("FATSECRET_PASSWORD"),
        )

    @property
    def telemetry_path(self) -> Path:
        return self.state_dir / "observability.sqlite3"

    @property
    def operations_path(self) -> Path:
        return self.state_dir / "operations.sqlite3"

    @property
    def credentials_path(self) -> Path:
        return self.state_dir / "credentials.json"
