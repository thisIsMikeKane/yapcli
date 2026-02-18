from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import typer

from yapcli.secrets import default_secrets_dir, load_credentials
from yapcli.server import PlaidBackend
from yapcli.institutions import (
    DiscoveredInstitution,
    discover_institutions,
    prompt_for_institutions,
)
from yapcli.utils import default_data_dir, timestamp_for_filename

app = typer.Typer(help="Fetch account/balance information for a linked institution.")


def _payload_to_dataframe(
    *, payload: Dict[str, Any], institution_id: str
) -> pd.DataFrame:
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

    balances_out_dir = out_dir or (default_data_dir() / "balances")
    balances_out_dir.mkdir(parents=True, exist_ok=True)

    timestamp = timestamp_for_filename()
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
