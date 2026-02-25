from __future__ import annotations
import datetime as dt
from pathlib import Path
from typing import Any, Dict, List, Optional

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

app = typer.Typer(help="Fetch investment transactions for one or more accounts.")


def get_investments_transactions_for_institution(
    *,
    institution_id: str,
    start_date: Optional[dt.date] = None,
    end_date: Optional[dt.date] = None,
) -> Dict[str, Any]:
    """Initialize PlaidBackend from secrets and return /investments_transactions response dict."""

    item_id, access_token = load_credentials(institution_id=institution_id)
    backend = PlaidBackend(access_token=access_token, item_id=item_id)
    request_kwargs: Dict[str, Any] = {}
    if start_date is not None:
        request_kwargs["start_date"] = start_date
    if end_date is not None:
        request_kwargs["end_date"] = end_date
    return backend.get_investments_transactions(**request_kwargs)


def _payload_to_dataframe(
    *,
    payload: Dict[str, Any],
    institution_id: str,
    account: DiscoveredAccount,
) -> pd.DataFrame:
    inner = (
        payload.get("investments_transactions") if isinstance(payload, dict) else None
    )
    txns_list: Any = None
    if isinstance(inner, dict):
        txns_list = inner.get("investment_transactions")

    rows: List[Dict[str, Any]]
    if isinstance(txns_list, list):
        rows = [
            cast_row
            for cast_row in txns_list
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


@app.command("investment_transactions")
def get_investment_transactions(
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
        help="Directory to write CSV files into (default: <output>/investment_transactions).",
        file_okay=False,
        dir_okay=True,
    ),
    start_date: Optional[str] = typer.Option(
        None,
        "--start_date",
        help="Start date for investment transactions (YYYY-MM-DD).",
    ),
    end_date: Optional[str] = typer.Option(
        None,
        "--end_date",
        help="End date for investment transactions (YYYY-MM-DD).",
    ),
) -> None:
    """Fetch investment transactions for one or more eligible accounts and write CSV(s)."""

    secrets_path = default_secrets_dir()

    parsed_start_date: Optional[dt.date] = None
    parsed_end_date: Optional[dt.date] = None
    if isinstance(start_date, str):
        try:
            parsed_start_date = dt.date.fromisoformat(start_date)
        except ValueError as exc:
            raise typer.BadParameter(
                "--start_date must be in YYYY-MM-DD format"
            ) from exc
    if isinstance(end_date, str):
        try:
            parsed_end_date = dt.date.fromisoformat(end_date)
        except ValueError as exc:
            raise typer.BadParameter(
                "--end_date must be in YYYY-MM-DD format"
            ) from exc

    if (
        parsed_start_date is not None
        and parsed_end_date is not None
        and parsed_start_date > parsed_end_date
    ):
        raise typer.BadParameter("--start_date cannot be after --end_date")

    selected_accounts = resolve_target_accounts(
        ids=ids,
        secrets_dir=secrets_path,
        all_accounts=all_accounts,
        allowed_account_types={"depository", "investment"},
    )

    out_base = out_dir or (default_output_dir() / "investment_transactions")
    out_base.mkdir(parents=True, exist_ok=True)

    timestamp = timestamp_for_filename()
    payload_by_institution: Dict[str, Dict[str, Any]] = {}

    for account in selected_accounts:
        if account.institution_id not in payload_by_institution:
            try:
                payload_by_institution[account.institution_id] = (
                    get_investments_transactions_for_institution(
                        institution_id=account.institution_id,
                        start_date=parsed_start_date,
                        end_date=parsed_end_date,
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
        out_path = out_base / f"{inst_component}_{account_component}_{timestamp}.csv"
        frame.to_csv(out_path, index=False)
        typer.echo(str(out_path))
