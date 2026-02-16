from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import typer

from yapcli.server import PlaidBackend
from yapcli.utils import DiscoveredInstitution, discover_institutions

app = typer.Typer(help="Fetch account/balance information for a linked institution.")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SECRETS_DIR = PROJECT_ROOT / "secrets"


def _default_secrets_dir() -> Path:
    override = os.getenv("PLAID_SECRETS_DIR")
    if override:
        return Path(override)
    return DEFAULT_SECRETS_DIR


def _read_secret(path: Path, *, label: str) -> str:
    try:
        value = path.read_text().strip()
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Missing {label} file: {path}") from exc

    if not value:
        raise ValueError(f"Empty {label} in file: {path}")

    return value


def load_credentials(
    *, institution_id: str, secrets_dir: Optional[Path] = None
) -> Tuple[str, str]:
    """Load (item_id, access_token) for an institution_id from secrets files."""

    secrets_path = secrets_dir or _default_secrets_dir()
    access_path = secrets_path / f"{institution_id}_access_token"
    item_path = secrets_path / f"{institution_id}_item_id"

    item_id = _read_secret(item_path, label="item_id")
    access_token = _read_secret(access_path, label="access_token")

    return item_id, access_token


def get_accounts_for_institution(
    *, institution_id: str, secrets_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """Initialize PlaidBackend from secrets and return /accounts response dict."""

    item_id, access_token = load_credentials(
        institution_id=institution_id, secrets_dir=secrets_dir
    )
    backend = PlaidBackend(access_token=access_token, item_id=item_id)
    return backend.get_accounts()


def parse_institution_selection(selection: str, institutions: List[str]) -> List[str]:
    """Parse comma-separated indices or institution ids.

    Supports: "all" / "*" or "1,3" or "ins_123".
    """

    cleaned = selection.strip()
    if not cleaned:
        raise ValueError("Selection cannot be empty")

    lowered = cleaned.lower()
    if lowered in {"all", "*"}:
        return list(institutions)

    tokens = [token.strip() for token in cleaned.split(",") if token.strip()]
    if not tokens:
        raise ValueError("Selection cannot be empty")

    selected: List[str] = []
    for token in tokens:
        if token.isdigit():
            idx = int(token)
            if idx < 1 or idx > len(institutions):
                raise ValueError(f"Selection index out of range: {idx}")
            chosen = institutions[idx - 1]
        else:
            if token not in institutions:
                raise ValueError(f"Unknown institution: {token}")
            chosen = token

        if chosen not in selected:
            selected.append(chosen)

    return selected


@app.command("balances")
def get_balances(
    institution_id: Optional[str] = typer.Argument(
        None,
        help="Institution identifier used in secrets filenames (e.g. ins_109511). If omitted, you'll be prompted to select from saved institutions.",
    ),
    secrets_dir: Optional[Path] = typer.Option(
        None,
        "--secrets-dir",
        help="Directory containing *_access_token and *_item_id files.",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
    ),
) -> None:
    """Print the Plaid /accounts response for a saved institution."""

    secrets_path = secrets_dir or _default_secrets_dir()

    selected_institutions: List[str]
    if institution_id is None or institution_id.strip() == "":
        discovered = discover_institutions(secrets_dir=secrets_path)
        available: List[DiscoveredInstitution] = list(discovered)
        if not available:
            raise typer.BadParameter(
                f"No saved institutions found in secrets dir: {secrets_path}"
            )

        available_ids = [entry.institution_id for entry in available]

        typer.echo("Saved institutions:")
        for idx, entry in enumerate(available, start=1):
            if entry.bank_name:
                typer.echo(f"  {idx}. {entry.institution_id} ({entry.bank_name})")
            else:
                typer.echo(f"  {idx}. {entry.institution_id}")

        selection = typer.prompt(
            "Select institution(s) (comma-separated numbers, 'all')",
            default="1",
            show_default=True,
        )
        try:
            selected_institutions = parse_institution_selection(selection, available_ids)
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc
    else:
        selected_institutions = [institution_id]

    results: Dict[str, Any]
    if len(selected_institutions) == 1:
        try:
            payload = get_accounts_for_institution(
                institution_id=selected_institutions[0], secrets_dir=secrets_path
            )
        except (FileNotFoundError, ValueError) as exc:
            raise typer.BadParameter(str(exc)) from exc
        typer.echo(json.dumps(payload, indent=2, sort_keys=True, default=str))
        return

    results = {}
    for inst in selected_institutions:
        try:
            results[inst] = get_accounts_for_institution(
                institution_id=inst, secrets_dir=secrets_path
            )
        except (FileNotFoundError, ValueError) as exc:
            results[inst] = {"error": str(exc)}

    typer.echo(json.dumps(results, indent=2, sort_keys=True, default=str))
