from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from yapcli.secrets import read_secret_required
from yapcli.server import PlaidBackend


@dataclass(frozen=True)
class DiscoveredInstitution:
    institution_id: str
    bank_name: Optional[str] = None


def discover_institutions(*, secrets_dir: Path) -> List[DiscoveredInstitution]:
    """Discover saved institutions and (best-effort) resolve their bank names.

    Institutions are discovered by locating identifiers that have both
    `*_access_token` and `*_item_id` files in `secrets_dir`.

    Bank name resolution uses PlaidBackend.get_item() and may return None if
    credentials are missing/invalid or Plaid is not configured.
    """

    identifiers: List[str] = []
    for access_file in secrets_dir.glob("*_access_token"):
        identifier = access_file.name[: -len("_access_token")]
        if not identifier:
            continue
        item_file = secrets_dir / f"{identifier}_item_id"
        if item_file.exists():
            identifiers.append(identifier)

    results: List[DiscoveredInstitution] = []
    for identifier in sorted(set(identifiers)):
        try:
            access_token = read_secret_required(
                secrets_dir / f"{identifier}_access_token", label="access_token"
            )
            item_id = read_secret_required(
                secrets_dir / f"{identifier}_item_id", label="item_id"
            )
        except (FileNotFoundError, ValueError):
            access_token = None
            item_id = None

        bank_name: Optional[str] = None
        if access_token and item_id:
            try:
                backend = PlaidBackend(access_token=access_token, item_id=item_id)
                payload = backend.get_item()
                institution = (
                    payload.get("institution") if isinstance(payload, dict) else None
                )
                if isinstance(institution, dict):
                    bank_name = institution.get("name")
            except Exception:
                bank_name = None

        results.append(
            DiscoveredInstitution(institution_id=identifier, bank_name=bank_name)
        )

    return results
