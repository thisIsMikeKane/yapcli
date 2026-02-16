from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import typer

from yapcli.accounts import DiscoveredAccount, resolve_target_accounts
from yapcli.secrets import default_secrets_dir, load_credentials
from yapcli.server import PlaidBackend
from yapcli.utils import timestamp_for_filename

app = typer.Typer(help="Fetch transactions for a linked institution.")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TRANSACTIONS_OUTPUT_DIR = PROJECT_ROOT / "data" / "transactions"

def _safe_filename_component(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return cleaned or "unknown"

def get_transactions_for_institution(
    *,
    institution_id: str,
    account_id: Optional[str] = None,
    secrets_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Initialize PlaidBackend from secrets and return /transactions response dict."""

    item_id, access_token = load_credentials(
        institution_id=institution_id, secrets_dir=secrets_dir
    )
    backend = PlaidBackend(access_token=access_token, item_id=item_id)
    return backend.get_transactions(account_id=account_id)


def _payload_to_dataframe(
    *,
    payload: Dict[str, Any],
    institution_id: str,
    account: Optional[DiscoveredAccount] = None,
) -> pd.DataFrame:
    transactions = payload.get("latest_transactions")
    if isinstance(transactions, list):
        frame = pd.json_normalize(transactions)
        if "institution_id" not in frame.columns:
            frame.insert(0, "institution_id", institution_id)
        else:
            frame["institution_id"] = institution_id
        if account is not None:
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

    frame = pd.json_normalize(payload)
    if "institution_id" not in frame.columns:
        frame.insert(0, "institution_id", institution_id)
    else:
        frame["institution_id"] = institution_id
    if account is not None:
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

@app.command("transactions")
def get_transactions(
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
        help="Directory to write CSV files into (default: data/transactions).",
        file_okay=False,
        dir_okay=True,
    ),
) -> None:
    """Fetch transactions for one or more accounts and write CSV(s)."""

    secrets_path = secrets_dir or default_secrets_dir()

    selected_accounts = resolve_target_accounts(
        ids=ids,
        secrets_dir=secrets_path,
        all_accounts=all_accounts,
        allowed_account_types={"depository", "credit", "loan", "other"},
    )

    transactions_out_dir = out_dir or DEFAULT_TRANSACTIONS_OUTPUT_DIR
    transactions_out_dir.mkdir(parents=True, exist_ok=True)

    timestamp = timestamp_for_filename()
    for account in selected_accounts:
        try:
            payload = get_transactions_for_institution(
                institution_id=account.institution_id,
                account_id=account.account_id,
                secrets_dir=secrets_path,
            )
        except (FileNotFoundError, ValueError) as exc:
            payload = {"error": str(exc)}

        frame = _payload_to_dataframe(
            payload=payload,
            institution_id=account.institution_id,
            account=account,
        )
        inst_component = _safe_filename_component(account.institution_id)
        account_component = _safe_filename_component(account.mask or account.account_id)
        out_path = (
            transactions_out_dir
            / f"{inst_component}_{account_component}_{timestamp}.csv"
        )
        frame.to_csv(out_path, index=False)
        typer.echo(str(out_path))
