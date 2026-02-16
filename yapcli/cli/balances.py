from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import questionary
import typer

from yapcli.secrets import default_secrets_dir, load_credentials
from yapcli.server import PlaidBackend
from yapcli.utils import DiscoveredInstitution, discover_institutions

app = typer.Typer(help="Fetch account/balance information for a linked institution.")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BALANCES_OUTPUT_DIR = PROJECT_ROOT / "data" / "balances"


def _timestamp_for_filename() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _payload_to_dataframe(*, payload: Dict[str, Any], institution_id: str) -> pd.DataFrame:
    accounts = payload.get("accounts")
    if isinstance(accounts, list):
        frame = pd.json_normalize(accounts)
        frame.insert(0, "institution_id", institution_id)
        request_id = payload.get("request_id")
        if request_id is not None:
            frame["request_id"] = request_id
        return frame

    frame = pd.json_normalize(payload)
    frame.insert(0, "institution_id", institution_id)
    return frame


def get_accounts_for_institution(
    *, institution_id: str, secrets_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """Initialize PlaidBackend from secrets and return /accounts response dict."""

    item_id, access_token = load_credentials(
        institution_id=institution_id, secrets_dir=secrets_dir
    )
    backend = PlaidBackend(access_token=access_token, item_id=item_id)
    return backend.get_accounts()


def prompt_for_institutions(available: List[DiscoveredInstitution]) -> List[str]:
    """Prompt user to select institution ids using questionary."""

    if not available:
        raise ValueError("No saved institutions available")

    choices: List[questionary.Choice] = []
    for idx, entry in enumerate(available):
        title = (
            f"{entry.institution_id} ({entry.bank_name})"
            if entry.bank_name
            else entry.institution_id
        )
        choices.append(
            questionary.Choice(
                title=title,
                value=entry.institution_id,
                checked=(idx == 0),
            )
        )

    try:
        selected = questionary.checkbox(
            "Select institution(s)",
            choices=choices,
        ).ask()
    except KeyboardInterrupt as exc:
        raise ValueError("Selection cancelled") from exc

    if not selected:
        raise ValueError("No institutions selected")

    return list(selected)


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
    out_dir: Optional[Path] = typer.Option(
        None,
        "--out-dir",
        help="Directory to write CSV files into (default: data/balances).",
        file_okay=False,
        dir_okay=True,
    ),
) -> None:
    """Print the Plaid /accounts response for a saved institution."""

    secrets_path = secrets_dir or default_secrets_dir()

    selected_institutions: List[str]
    if institution_id is None or institution_id.strip() == "":
        discovered = discover_institutions(secrets_dir=secrets_path)
        available: List[DiscoveredInstitution] = list(discovered)
        if not available:
            raise typer.BadParameter(
                f"No saved institutions found in secrets dir: {secrets_path}"
            )

        try:
            selected_institutions = prompt_for_institutions(available)
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc
    else:
        selected_institutions = [institution_id]

    balances_out_dir = out_dir or DEFAULT_BALANCES_OUTPUT_DIR
    balances_out_dir.mkdir(parents=True, exist_ok=True)

    timestamp = _timestamp_for_filename()
    for inst in selected_institutions:
        try:
            payload = get_accounts_for_institution(
                institution_id=inst, secrets_dir=secrets_path
            )
        except (FileNotFoundError, ValueError) as exc:
            payload = {"error": str(exc)}

        frame = _payload_to_dataframe(payload=payload, institution_id=inst)
        out_path = balances_out_dir / f"{inst}_{timestamp}.csv"
        frame.to_csv(out_path, index=False)
        typer.echo(str(out_path))
