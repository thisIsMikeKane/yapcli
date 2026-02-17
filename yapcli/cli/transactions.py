from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
import re

import pandas as pd
import typer

from yapcli.accounts import DiscoveredAccount, resolve_target_accounts
from yapcli.secrets import default_secrets_dir, load_credentials
from yapcli.server import PlaidBackend
from yapcli.utils import safe_filename_component, timestamp_for_filename

app = typer.Typer(help="Fetch transactions for a linked institution.")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TRANSACTIONS_OUTPUT_DIR = PROJECT_ROOT / "data" / "transactions"


def build_transactions_csv_path(
    *,
    out_dir: Path,
    account: DiscoveredAccount,
    timestamp: str,
    cursor: Optional[str],
    kind: Optional[str] = None,
) -> Path:
    inst_component = safe_filename_component(
        str(account.institution_id) + "_" + str(account.bank_name)
    )
    account_component = safe_filename_component(
        str(account.account_id) + "_" + (account.mask or "0000") + "_" + str(account.name)
    )

    cursor_component = ""
    if isinstance(cursor, str) and cursor.strip() != "":
        cursor_component = cursor.strip()
        if len(cursor_component) > 128:
            raise ValueError(f"Expected cursor length up to 128, got {len(cursor_component)}")
        if re.fullmatch(r"[A-Za-z0-9=]+", cursor_component) is None:
            raise ValueError(
                "Cursor contains unexpected characters; expected only A-Za-z0-9._=-"
                + f"Got cursor: {cursor_component}"
            )

    kind_component = ""
    if isinstance(kind, str) and kind.strip() != "":
        kind_component = safe_filename_component(kind.strip())

    filename = f"{timestamp}.csv"
    if kind_component:
        filename = f"{timestamp}_{kind_component}.csv"
    if cursor_component:
        if kind_component:
            filename = f"{timestamp}_{kind_component}_{cursor_component}.csv"
        else:
            filename = f"{timestamp}_{cursor_component}.csv"

    return out_dir / inst_component / account_component / filename

def get_transactions_for_institution(
    *,
    institution_id: str,
    account_id: Optional[str] = None,
    cursor: Optional[str] = None,
    secrets_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Initialize PlaidBackend from secrets and return /transactions response dict."""

    item_id, access_token = load_credentials(
        institution_id=institution_id, secrets_dir=secrets_dir
    )
    backend = PlaidBackend(access_token=access_token, item_id=item_id)
    if cursor is not None:
        return backend.get_transactions(account_id=account_id, cursor=cursor)
    return backend.get_transactions(account_id=account_id)


def _payload_to_dataframe(
    *,
    payload: Dict[str, Any],
    institution_id: str,
    account: Optional[DiscoveredAccount] = None,
) -> pd.DataFrame:
    transactions = payload.get("transactions")
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
    cursor: Optional[str] = typer.Option(
        None,
        "--cursor",
        help=(
            "Start the Plaid transactions/sync from this cursor. Only valid when you pass exactly one account_id argument."
        ),
    ),
) -> None:
    """Fetch transactions for one or more accounts and write CSV(s)."""

    secrets_path = secrets_dir or default_secrets_dir()

    ids_list = [value for value in (ids or []) if value.strip() != ""]
    if cursor is not None:
        if all_accounts:
            raise typer.BadParameter(
                "--cursor is only valid when passing exactly one account_id argument."
            )
        if len(ids_list) != 1:
            raise typer.BadParameter(
                "--cursor is only valid when passing exactly one account_id argument."
            )
        if re.fullmatch(r"ins_\d+", ids_list[0]) is not None:
            raise typer.BadParameter(
                "--cursor is only valid when passing an account_id, not an institution id."
            )

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

        # Get transactions
        try:
            payload = get_transactions_for_institution(
                institution_id=account.institution_id,
                account_id=account.account_id,
                cursor=cursor,
                secrets_dir=secrets_path,
            )
        except (FileNotFoundError, ValueError) as exc:
            payload = {"error": str(exc)}

        # Format and save added transactions
        frame = _payload_to_dataframe(
            payload=payload,
            institution_id=account.institution_id,
            account=account,
        )

        out_path = build_transactions_csv_path(
            out_dir=transactions_out_dir,
            account=account,
            timestamp=timestamp,
            cursor=payload.get("cursor"),
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(out_path, index=False)
        typer.echo(str(out_path))

        # Handle modified/removed transactions if present, writing separate CSVs for each kind
        modified = payload.get("modified")
        removed = payload.get("removed")
        modified_count = len(modified) if isinstance(modified, list) else 0
        removed_count = len(removed) if isinstance(removed, list) else 0
        if modified_count or removed_count:
            typer.echo(
                f"WARNING: Plaid sync returned modified={modified_count} removed={removed_count} for account_id={account.account_id}. "
                + "Writing separate CSVs for modified/removed."
            )

        if isinstance(modified, list) and modified:
            modified_frame = _payload_to_dataframe(
                payload={"transactions": modified},
                institution_id=account.institution_id,
                account=account,
            )
            modified_path = build_transactions_csv_path(
                out_dir=transactions_out_dir,
                account=account,
                timestamp=timestamp,
                kind="modified",
                cursor=payload.get("cursor"),
            )
            modified_path.parent.mkdir(parents=True, exist_ok=True)
            modified_frame.to_csv(modified_path, index=False)
            typer.echo(str(modified_path))

        if isinstance(removed, list) and removed:
            removed_frame = _payload_to_dataframe(
                payload={"transactions": removed},
                institution_id=account.institution_id,
                account=account,
            )
            removed_path = build_transactions_csv_path(
                out_dir=transactions_out_dir,
                account=account,
                timestamp=timestamp,
                kind="removed",
                cursor=payload.get("cursor"),
            )
            removed_path.parent.mkdir(parents=True, exist_ok=True)
            removed_frame.to_csv(removed_path, index=False)
            typer.echo(str(removed_path))
