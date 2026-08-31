"""Command-line entry point for an installed FatSecret MCP server."""

from __future__ import annotations

import argparse
import json
from dataclasses import replace

from . import __version__
from .analytics import build_report
from .catalog import PROFILE_CATEGORIES
from .server import run
from .settings import Settings


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="fatsecret-mcp")
    result.add_argument("--version", action="version", version=__version__)
    result.add_argument("--profile", choices=sorted(PROFILE_CATEGORIES))
    result.add_argument(
        "--transport", choices=("stdio", "streamable-http"), default=None
    )
    result.add_argument("--host")
    result.add_argument("--port", type=int)
    result.add_argument(
        "--observability-report",
        action="store_true",
        help="print aggregate tool and inferred-goal metrics, then exit",
    )
    return result


def main() -> None:
    arguments = parser().parse_args()
    settings = Settings.from_env()
    if arguments.observability_report:
        print(
            json.dumps(build_report(settings.telemetry_path), indent=2, sort_keys=True)
        )
        return
    overrides = {
        key: value
        for key, value in vars(arguments).items()
        if key in {"profile", "transport", "host", "port"} and value is not None
    }
    run(replace(settings, **overrides))


if __name__ == "__main__":
    main()
