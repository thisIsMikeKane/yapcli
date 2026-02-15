"""Public package interface for Yet Another Plaid CLI."""

from importlib import metadata

try:
    __version__ = metadata.version("yapcli")
except metadata.PackageNotFoundError:  # pragma: no cover - defensive fallback
    __version__ = "0.0.0"

__all__ = ["__version__"]
