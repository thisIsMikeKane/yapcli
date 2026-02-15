from __future__ import annotations

from pathlib import Path
from typing import List


def discover_institutions(*, secrets_dir: Path) -> List[str]:
    """Return institution ids that have both *_access_token and *_item_id files."""

    institutions: List[str] = []
    for access_file in secrets_dir.glob("*_access_token"):
        identifier = access_file.name[: -len("_access_token")]
        if not identifier:
            continue
        item_file = secrets_dir / f"{identifier}_item_id"
        if item_file.exists():
            institutions.append(identifier)

    return sorted(set(institutions))
