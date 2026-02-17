from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import typer

from yapcli.accounts import DiscoveredAccount, resolve_target_accounts
from yapcli.secrets import default_secrets_dir, load_credentials
from yapcli.server import PlaidBackend
from yapcli.utils import safe_filename_component, timestamp_for_filename

app = typer.Typer(help="Fetch investment holdings for one or more accounts.")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_HOLDINGS_OUTPUT_DIR = PROJECT_ROOT / "data" / "holdings"


def get_holdings_for_institution(
    *,
    institution_id: str,
    secrets_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Initialize PlaidBackend from secrets and return /holdings response dict."""

    item_id, access_token = load_credentials(
        institution_id=institution_id, secrets_dir=secrets_dir
    )
    backend = PlaidBackend(access_token=access_token, item_id=item_id)
    return backend.get_holdings()


def _payload_to_dataframe(
    *,
    payload: Dict[str, Any],
    institution_id: str,
    account: DiscoveredAccount,
) -> pd.DataFrame:
    inner = payload.get("holdings") if isinstance(payload, dict) else None
    holdings_list: Any = None
    if isinstance(inner, dict):
        holdings_list = inner.get("holdings")

    rows: List[Dict[str, Any]]
    if isinstance(holdings_list, list):
        rows = [
            cast_row
            for cast_row in holdings_list
            if isinstance(cast_row, dict)
            and cast_row.get("account_id") == account.account_id
        ]
        frame = pd.json_normalize(rows)
    else:
        frame = pd.json_normalize(payload)

    if "institution_id" not in frame.columns:
        frame.insert(0, "institution_id", institution_id)
    else:
        frame["institution_id"] = institution_id

    if "account_id" not in frame.columns:
        frame.insert(1, "account_id", account.account_id)
    else:
        frame["account_id"] = account.account_id

    frame["account_type"] = account.type
    frame["account_name"] = account.name
    frame["account_subtype"] = account.subtype
    frame["account_mask"] = account.mask
    frame["bank_name"] = account.bank_name
    return frame


@app.command("holdings")
def get_holdings(
    ids: Optional[List[str]] = typer.Argument(
        None,
        help=(
            "One or more institution ids (ins_123) or Plaid account_ids. "
            "If you pass institution ids you'll be prompted to select account(s) unless --all-accounts is set. "
            "If you pass account_ids, no prompt is shown."
        ),
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
    all_accounts: bool = typer.Option(
        False,
        "--all-accounts",
        "--all_accounts",
        help="When passing institution ids, process all accounts without prompting.",
    ),
    out_dir: Optional[Path] = typer.Option(
        None,
        "--out-dir",
        help="Directory to write CSV files into (default: data/holdings).",
        file_okay=False,
        dir_okay=True,
    ),
) -> None:
    """Fetch holdings for one or more eligible accounts and write CSV(s)."""

    secrets_path = secrets_dir or default_secrets_dir()

    selected_accounts = resolve_target_accounts(
        ids=ids,
        secrets_dir=secrets_path,
        all_accounts=all_accounts,
        allowed_account_types={"depository", "investment"},
    )

    holdings_out_dir = out_dir or DEFAULT_HOLDINGS_OUTPUT_DIR
    holdings_out_dir.mkdir(parents=True, exist_ok=True)

    timestamp = timestamp_for_filename()
    payload_by_institution: Dict[str, Dict[str, Any]] = {}

    for account in selected_accounts:
        if account.institution_id not in payload_by_institution:
            try:
                payload_by_institution[account.institution_id] = (
                    get_holdings_for_institution(
                        institution_id=account.institution_id,
                        secrets_dir=secrets_path,
                    )
                )
            except (FileNotFoundError, ValueError) as exc:
                payload_by_institution[account.institution_id] = {"error": str(exc)}

        payload = payload_by_institution[account.institution_id]
        frame = _payload_to_dataframe(
            payload=payload,
            institution_id=account.institution_id,
            account=account,
        )

        inst_component = safe_filename_component(account.institution_id)
        account_component = safe_filename_component(account.mask or account.account_id)
        out_path = (
            holdings_out_dir / f"{inst_component}_{account_component}_{timestamp}.csv"
        )
        frame.to_csv(out_path, index=False)
        typer.echo(str(out_path))
