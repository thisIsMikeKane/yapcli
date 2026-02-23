from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import re

import pandas as pd
import typer

from yapcli.accounts import DiscoveredAccount, resolve_target_accounts
from yapcli.secrets import load_credentials
from yapcli.server import PlaidBackend
from yapcli.utils import (
    default_output_dir,
    default_secrets_dir,
    safe_filename_component,
    timestamp_for_filename,
)

app = typer.Typer(help="Fetch transactions for a linked institution.")


_META_FILENAME_RE = re.compile(r"(?P<ts>\d{8}T\d{6}Z)_meta\.json$")


def build_transactions_account_dir(
    *, out_dir: Path, account: DiscoveredAccount
) -> Path:
    inst_component = safe_filename_component(
        str(account.institution_id) + "_" + str(account.bank_name)
    )
    account_component = safe_filename_component(
        (account.mask or "0000") + "_" + str(account.name)
    )
    return out_dir / inst_component / account_component


def _load_latest_meta_cursor(
    *, out_dir: Path, account: DiscoveredAccount
) -> Optional[str]:
    account_dir = build_transactions_account_dir(out_dir=out_dir, account=account)
    if not account_dir.exists():
        return None

    meta_paths = [p for p in account_dir.glob("*_meta.json") if p.is_file()]
    if not meta_paths:
        return None

    def sort_key(path: Path) -> tuple[str, float]:
        match = _META_FILENAME_RE.search(path.name)
        ts = match.group("ts") if match else ""
        try:
            mtime = path.stat().st_mtime
        except OSError:
            mtime = 0.0
        return (ts, mtime)

    latest_meta = sorted(meta_paths, key=sort_key, reverse=True)[0]
    try:
        meta = json.loads(latest_meta.read_text())
    except OSError as exc:
        raise typer.BadParameter(
            f"Unable to read meta file: {latest_meta} ({exc})"
        ) from exc
    except json.JSONDecodeError as exc:
        raise typer.BadParameter(
            f"Invalid JSON in meta file: {latest_meta} ({exc})"
        ) from exc

    if not isinstance(meta, dict):
        raise typer.BadParameter(
            f"Invalid meta file format (expected object): {latest_meta}"
        )

    meta_account_id = meta.get("account_id")
    if meta_account_id != account.account_id:
        raise typer.BadParameter(
            f"Meta account_id mismatch for {latest_meta}: expected {account.account_id}, got {meta_account_id}"
        )

    meta_cursor = meta.get("cursor")
    if not isinstance(meta_cursor, str) or meta_cursor.strip() == "":
        raise typer.BadParameter(f"Meta file missing non-empty cursor: {latest_meta}")

    return meta_cursor.strip()


def build_transactions_csv_path(
    *,
    out_dir: Path,
    account: DiscoveredAccount,
    timestamp: str,
    kind: Optional[str] = None,
) -> Path:
    inst_component = safe_filename_component(
        str(account.institution_id) + "_" + str(account.bank_name)
    )
    account_component = safe_filename_component(
        (account.mask or "0000") + "_" + str(account.name)
    )

    kind_component = ""
    if isinstance(kind, str) and kind.strip() != "":
        kind_component = safe_filename_component(kind.strip())

    if not kind_component:
        raise ValueError("Expected kind to build transactions CSV path")

    filename = f"{timestamp}_{kind_component}.csv"

    return out_dir / inst_component / account_component / filename


def build_transactions_meta_path(
    *,
    out_dir: Path,
    account: DiscoveredAccount,
    timestamp: str,
) -> Path:
    # Single meta file per run/timestamp, stored alongside the CSVs
    # within the account output directory.
    csv_path = build_transactions_csv_path(
        out_dir=out_dir,
        account=account,
        timestamp=timestamp,
        kind="transactions",
    )
    return csv_path.with_name(f"{timestamp}_meta.json")


def get_transactions_for_institution(
    *,
    institution_id: str,
    account_id: Optional[str] = None,
    cursor: Optional[str] = None,
) -> Dict[str, Any]:
    """Initialize PlaidBackend from secrets and return /transactions response dict."""

    item_id, access_token = load_credentials(institution_id=institution_id)
    backend = PlaidBackend(access_token=access_token, item_id=item_id)
    if isinstance(cursor, str) and cursor.strip() != "":
        return backend.get_transactions(account_id=account_id, cursor=cursor.strip())
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
    all_accounts: bool = typer.Option(
        False,
        "--all-accounts",
        "--all_accounts",
        help="When passing institution ids, process all accounts without prompting.",
    ),
    out_dir: Optional[Path] = typer.Option(
        None,
        "--out-dir",
        help="Directory to write CSV files into (default: <output>/transactions).",
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
    sync: bool = typer.Option(
        False,
        "--sync",
        help=(
            "Use the most recent *_meta.json for each account to resume from its saved cursor. "
            "Looks in the account's output directory under --out-dir."
        ),
    ),
) -> None:
    """Fetch transactions for one or more accounts and write CSV(s)."""

    secrets_path = default_secrets_dir()

    ids_list = [value for value in (ids or []) if value.strip() != ""]
    if sync and cursor is not None:
        raise typer.BadParameter("--sync cannot be used together with --cursor")
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

    transactions_out_dir = out_dir or (default_output_dir() / "transactions")
    transactions_out_dir.mkdir(parents=True, exist_ok=True)

    timestamp = timestamp_for_filename()
    for account in selected_accounts:

        effective_cursor = cursor
        if sync and effective_cursor is None:
            effective_cursor = _load_latest_meta_cursor(
                out_dir=transactions_out_dir,
                account=account,
            )

        # Get transactions
        try:
            payload = get_transactions_for_institution(
                institution_id=account.institution_id,
                account_id=account.account_id,
                cursor=effective_cursor,
            )
        except (FileNotFoundError, ValueError) as exc:
            payload = {"error": str(exc)}

        payload_error = payload.get("error")
        if payload_error is not None:
            message = None
            if isinstance(payload_error, dict):
                error_code = payload_error.get("error_code")
                display_message = payload_error.get("display_message")
                if isinstance(error_code, str) and error_code.strip() != "":
                    message = (
                        f"{error_code}: {display_message}"
                        if display_message
                        else error_code
                    )
                elif isinstance(display_message, str) and display_message.strip() != "":
                    message = display_message
            elif isinstance(payload_error, str) and payload_error.strip() != "":
                message = payload_error.strip()

            if message:
                typer.echo(
                    f"WARNING: transactions sync returned an error for account_id={account.account_id}: {message}",
                    err=True,
                )
            else:
                typer.echo(
                    f"WARNING: transactions sync returned an error for account_id={account.account_id}",
                    err=True,
                )

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
            kind="transactions",
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(out_path, index=False)
        typer.echo(str(out_path))

        meta_path = build_transactions_meta_path(
            out_dir=transactions_out_dir,
            account=account,
            timestamp=timestamp,
        )
        meta_path.parent.mkdir(parents=True, exist_ok=True)

        error_value = payload.get("error")
        if error_value is not None and not isinstance(error_value, (dict, str)):
            error_value = str(error_value)
        meta_path.write_text(
            json.dumps(
                {
                    "account_id": account.account_id,
                    "cursor": payload.get("cursor"),
                    "error": error_value,
                },
                indent=2,
                sort_keys=True,
            )
        )

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
            )
            removed_path.parent.mkdir(parents=True, exist_ok=True)
            removed_frame.to_csv(removed_path, index=False)
            typer.echo(str(removed_path))
