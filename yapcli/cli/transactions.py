from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import typer

from yapcli.secrets import default_secrets_dir, load_credentials
from yapcli.server import PlaidBackend
from yapcli.utils import (
    DiscoveredInstitution,
    discover_institutions,
    prompt_for_institutions,
    timestamp_for_filename,
)

app = typer.Typer(help="Fetch transactions for a linked institution.")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TRANSACTIONS_OUTPUT_DIR = PROJECT_ROOT / "data" / "transactions"


def get_transactions_for_institution(
    *, institution_id: str, secrets_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """Initialize PlaidBackend from secrets and return /transactions response dict."""

    item_id, access_token = load_credentials(
        institution_id=institution_id, secrets_dir=secrets_dir
    )
    backend = PlaidBackend(access_token=access_token, item_id=item_id)
    return backend.get_transactions()


def _payload_to_dataframe(*, payload: Dict[str, Any], institution_id: str) -> pd.DataFrame:
    transactions = payload.get("latest_transactions")
    if isinstance(transactions, list):
        frame = pd.json_normalize(transactions)
        frame.insert(0, "institution_id", institution_id)
        return frame

    frame = pd.json_normalize(payload)
    frame.insert(0, "institution_id", institution_id)
    return frame


@app.command("transactions")
def get_transactions(
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
        help="Directory to write CSV files into (default: data/transactions).",
        file_okay=False,
        dir_okay=True,
    ),
) -> None:
    """Fetch transactions for one or more saved institutions and write CSV(s)."""

    secrets_path = secrets_dir or default_secrets_dir()

    selected_institutions: List[str]
    if institution_id is None or institution_id.strip() == "":
        available: List[DiscoveredInstitution] = list(
            discover_institutions(secrets_dir=secrets_path)
        )
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

    transactions_out_dir = out_dir or DEFAULT_TRANSACTIONS_OUTPUT_DIR
    transactions_out_dir.mkdir(parents=True, exist_ok=True)

    timestamp = timestamp_for_filename()
    for inst in selected_institutions:
        try:
            payload = get_transactions_for_institution(
                institution_id=inst, secrets_dir=secrets_path
            )
        except (FileNotFoundError, ValueError) as exc:
            payload = {"error": str(exc)}

        frame = _payload_to_dataframe(payload=payload, institution_id=inst)
        out_path = transactions_out_dir / f"{inst}_{timestamp}.csv"
        frame.to_csv(out_path, index=False)
        typer.echo(str(out_path))
