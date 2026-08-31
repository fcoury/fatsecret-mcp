"""MCP server construction and transport lifecycle."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from anyio.to_thread import run_sync
from mcp.server import MCPServer

from . import __version__
from .registration import ToolRegistry
from .runtime import Runtime
from .settings import Settings
from .telemetry import new_trace_id


def create_server(
    *, settings: Settings | None = None, runtime: Runtime | None = None
) -> MCPServer:
    configured = settings or Settings.from_env()
    current_runtime = runtime or Runtime(configured)

    @asynccontextmanager
    async def lifespan(_: MCPServer) -> AsyncGenerator[None, None]:
        current_runtime.events.emit(
            "session.started",
            session_id="server-process",
            trace_id=new_trace_id(),
            profile=configured.profile,
            status="ok",
        )
        try:
            yield None
        finally:
            current_runtime.events.emit(
                "session.closed",
                session_id="server-process",
                trace_id=new_trace_id(),
                profile=configured.profile,
                status="ok",
            )
            await run_sync(current_runtime.close)

    server = MCPServer(
        name="fatsecret-mcp",
        title="FatSecret MCP",
        description=(
            "Curated tools for the FatSecret Platform API and the unofficial "
            "authenticated member website adapter."
        ),
        instructions=(
            "Use member tools for recipes owned by the configured account. "
            "Use public get_recipe only for catalog recipes. Exact food IDs are "
            "required for member ingredient mutations. When a needed tool is not "
            "advertised, call resolve_fatsecret_capability."
        ),
        version=__version__,
        lifespan=lifespan,
    )
    # Local allowlisted telemetry is sufficient. Avoid exporting unexpected
    # exception text through the SDK's process-wide OpenTelemetry middleware.
    server.middleware[:] = [
        item
        for item in server.middleware
        if type(item).__name__ != "OpenTelemetryMiddleware"
    ]
    registry = ToolRegistry(server, current_runtime)
    registry.register_profile()
    current_runtime.events.emit(
        "tools.advertised",
        session_id="server-process",
        trace_id=new_trace_id(),
        profile=configured.profile,
        status="ok",
        attributes={"tool_names": sorted(registry.active)},
    )
    return server


def run(settings: Settings | None = None) -> None:
    configured = settings or Settings.from_env()
    server = create_server(settings=configured)
    if configured.transport == "stdio":
        server.run("stdio")
    elif configured.transport == "streamable-http":
        server.run(
            "streamable-http",
            host=configured.host,
            port=configured.port,
            json_response=True,
            stateless_http=False,
        )
    else:
        raise ValueError("transport must be stdio or streamable-http")


__all__ = ["create_server", "run"]
