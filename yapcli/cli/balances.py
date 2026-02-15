from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import typer

from yapcli.server import PlaidBackend

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


@app.command("balances")
def get_balances(
    institution_id: str = typer.Argument(
        ..., help="Institution identifier used in secrets filenames (e.g. ins_109511)."
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

    try:
        payload = get_accounts_for_institution(
            institution_id=institution_id, secrets_dir=secrets_dir
        )
    except (FileNotFoundError, ValueError) as exc:
        raise typer.BadParameter(str(exc)) from exc

    typer.echo(json.dumps(payload, indent=2, sort_keys=True, default=str))
