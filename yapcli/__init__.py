"""Public package interface for Yet Another Plaid CLI."""

from importlib import metadata

from dotenv import load_dotenv

from yapcli.utils import default_env_file_path


def _load_default_dotenv() -> bool:
    return load_dotenv(dotenv_path=default_env_file_path(), override=False)


_load_default_dotenv()

try:
    __version__ = metadata.version("yapcli")
except metadata.PackageNotFoundError:  # pragma: no cover - defensive fallback
    __version__ = "0.0.0"

__all__ = ["__version__"]
