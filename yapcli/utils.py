from __future__ import annotations

import datetime as dt
import os
import re
from pathlib import Path

from yapcli.institutions import (  # re-exported for backward compatibility
    DiscoveredInstitution,
    discover_institutions,
    prompt_for_institutions,
)

__all__ = [
    "DiscoveredInstitution",
    "discover_institutions",
    "prompt_for_institutions",
    "safe_filename_component",
    "default_data_dir",
    "timestamp_for_filename",
]


_PROJECT_ROOT = Path(__file__).resolve().parents[1]


def default_data_dir() -> Path:
    """Default data directory.

    Uses `sandbox/data` when PLAID_ENV=sandbox, otherwise `data`.
    """

    plaid_env = os.getenv("PLAID_ENV")
    if plaid_env == "sandbox":
        return _PROJECT_ROOT / "sandbox" / "data"
    return _PROJECT_ROOT / "data"


def timestamp_for_filename() -> str:
    """UTC timestamp suitable for filenames (e.g. 20260215T032018Z)."""

    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def safe_filename_component(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return cleaned or "unknown"
