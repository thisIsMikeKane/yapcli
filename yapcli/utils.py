from __future__ import annotations

import datetime as dt

from yapcli.institutions import (  # re-exported for backward compatibility
    DiscoveredInstitution,
    discover_institutions,
    prompt_for_institutions,
)

__all__ = [
    "DiscoveredInstitution",
    "discover_institutions",
    "prompt_for_institutions",
    "timestamp_for_filename",
]


def timestamp_for_filename() -> str:
    """UTC timestamp suitable for filenames (e.g. 20260215T032018Z)."""

    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
