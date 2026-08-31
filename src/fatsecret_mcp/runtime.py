"""Shared runtime, dispatch, and privacy-safe tool instrumentation."""

from __future__ import annotations

from collections.abc import Callable
from functools import partial
from typing import Any
from uuid import uuid4

from anyio.to_thread import run_sync
from fatsecret.web.errors import (
    FatsecretWebRateLimitError,
    FatsecretWebVerificationError,
)
from mcp.server.mcpserver import Context

from .adapters.auth import AuthAdapter
from .adapters.member import MemberAdapter
from .catalog import BY_NAME, ToolSpec
from .settings import Settings
from .telemetry import EventStore, new_trace_id


class Runtime:
    def __init__(
        self,
        settings: Settings,
        *,
        auth: AuthAdapter | None = None,
        official: Any | None = None,
        member: MemberAdapter | None = None,
        events: EventStore | None = None,
    ) -> None:
        from .adapters.official import OfficialAdapter

        self.settings = settings
        self.auth = auth or AuthAdapter(settings)
        self.official = official or OfficialAdapter(settings, self.auth.store)
        self.member = member or MemberAdapter(settings)
        self.events = events or EventStore(
            settings.telemetry_path if settings.telemetry_enabled else None
        )
        self._process_id = uuid4().hex

    def close(self) -> None:
        self.official.close()

    async def invoke(
        self,
        tool_name: str,
        function: Callable[..., Any],
        arguments: dict[str, Any],
        context: Context | None,
    ) -> Any:
        spec = BY_NAME.get(tool_name)
        session_id = self._session_id(context)
        trace_id = context.request_id if context is not None else new_trace_id()
        with self.events.tool_span(
            session_id=session_id,
            trace_id=trace_id,
            profile=self.settings.profile,
            tool_name=tool_name,
            capability_id=spec.capability_id if spec is not None else tool_name,
        ):
            try:
                return await run_sync(partial(function, **arguments))
            except FatsecretWebRateLimitError as error:
                retry = (
                    str(error.retry_after)
                    if error.retry_after is not None
                    else "unspecified"
                )
                raise RuntimeError(
                    "FatSecret rate limit; "
                    f"retry_after_seconds={retry}; no write was confirmed"
                ) from None
            except FatsecretWebVerificationError as error:
                retry = (
                    str(error.retry_after)
                    if error.retry_after is not None
                    else "unspecified"
                )
                raise RuntimeError(
                    "FatSecret write outcome is ambiguous; "
                    f"retry_after_seconds={retry}; reconcile state before retry"
                ) from None
            except (KeyError, ValueError) as error:
                raise RuntimeError(f"invalid request: {type(error).__name__}") from None
            except RuntimeError as error:
                message = str(error)
                if message.startswith(
                    ("member tools require", "start_oauth_flow", "idempotent operation")
                ):
                    raise
                raise RuntimeError(
                    f"FatSecret operation failed: {type(error).__name__}"
                ) from None
            except Exception as error:  # noqa: BLE001 - sanitize adapter boundary
                raise RuntimeError(
                    f"FatSecret operation failed: {type(error).__name__}"
                ) from None

    def record_resolution(
        self,
        *,
        context: Context | None,
        candidates: list[tuple[ToolSpec, float]],
        selected: list[ToolSpec],
        activated: list[ToolSpec],
        status: str,
    ) -> None:
        self.events.emit(
            "capability.resolved",
            session_id=self._session_id(context),
            trace_id=context.request_id if context is not None else new_trace_id(),
            profile=self.settings.profile,
            status=status,
            attributes={
                "candidate_capability_ids": [
                    item.capability_id for item, _ in candidates
                ],
                "selected_tool_names": [item.name for item in selected],
                "activated_tool_names": [item.name for item in activated],
            },
        )

    def _session_id(self, context: Context | None) -> str:
        if context is None:
            return "in-process"
        return f"{self._process_id}:session-{id(context.session):x}"


__all__ = ["Runtime"]
