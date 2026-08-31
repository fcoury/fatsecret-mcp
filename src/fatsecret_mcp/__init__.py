"""Curated MCP surface for the FatSecret Python client."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("fatsecret-mcp")
except PackageNotFoundError:
    __version__ = "0.2.0.dev0"

__all__ = ["__version__"]
