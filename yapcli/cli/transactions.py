from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

import pandas as pd
import questionary
import typer

from yapcli.secrets import default_secrets_dir, load_credentials
from yapcli.server import PlaidBackend
from yapcli.utils import (
    DiscoveredInstitution,
    discover_institutions,
    timestamp_for_filename,
)

app = typer.Typer(help="Fetch transactions for a linked institution.")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TRANSACTIONS_OUTPUT_DIR = PROJECT_ROOT / "data" / "transactions"

_INSTITUTION_ID_RE = re.compile(r"ins_\d+")


def _safe_filename_component(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return cleaned or "unknown"


@dataclass(frozen=True)
class DiscoveredAccount:
    institution_id: str
    bank_name: Optional[str]
    account_id: str
    name: Optional[str]
    subtype: Optional[str]
    mask: Optional[str]

    def choice_title(self) -> str:
        bank = self.bank_name or self.institution_id
        display_name = self.name or "(unnamed)"
        subtype = self.subtype or "unknown"
        mask = f"••••{self.mask}" if self.mask else ""
        return f"{bank} - {display_name} ({subtype}) {mask}".strip()


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
        frame["account_name"] = account.name
        frame["account_subtype"] = account.subtype
        frame["account_mask"] = account.mask
        frame["bank_name"] = account.bank_name
    return frame


def _discover_accounts(
    *, institutions: List[DiscoveredInstitution], secrets_dir: Path
) -> List[DiscoveredAccount]:
    results: List[DiscoveredAccount] = []
    for inst in institutions:
        try:
            item_id, access_token = load_credentials(
                institution_id=inst.institution_id, secrets_dir=secrets_dir
            )
            backend = PlaidBackend(access_token=access_token, item_id=item_id)
            payload = backend.get_accounts()
        except (FileNotFoundError, ValueError):
            continue

        accounts = payload.get("accounts") if isinstance(payload, dict) else None
        if not isinstance(accounts, list):
            continue

        for account in accounts:
            if not isinstance(account, dict):
                continue
            account_id = account.get("account_id")
            if not isinstance(account_id, str) or not account_id:
                continue

            name = account.get("name") or account.get("official_name")
            subtype = account.get("subtype")
            mask = account.get("mask")

            results.append(
                DiscoveredAccount(
                    institution_id=inst.institution_id,
                    bank_name=inst.bank_name,
                    account_id=account_id,
                    name=str(name) if name is not None else None,
                    subtype=str(subtype) if subtype is not None else None,
                    mask=str(mask) if mask is not None else None,
                )
            )

    return results


def _prompt_for_accounts(accounts: List[DiscoveredAccount]) -> List[DiscoveredAccount]:
    if not accounts:
        raise ValueError("No accounts available")

    account_by_key: Dict[str, DiscoveredAccount] = {}
    choices: List[questionary.Choice] = []
    for idx, account in enumerate(accounts):
        key = f"{account.institution_id}|{account.account_id}"
        account_by_key[key] = account
        choices.append(
            questionary.Choice(
                title=account.choice_title(),
                value=key,
                checked=(idx == 0),
            )
        )

    try:
        selected_keys_raw = questionary.checkbox(
            "Select account(s)",
            choices=choices,
        ).ask()
    except KeyboardInterrupt as exc:
        raise ValueError("Selection cancelled") from exc

    if not selected_keys_raw:
        raise ValueError("No accounts selected")

    selected_keys = cast(List[str], selected_keys_raw)

    selected: List[DiscoveredAccount] = []
    for key in selected_keys:
        maybe_account = account_by_key.get(key)
        if maybe_account is not None:
            selected.append(maybe_account)
    return selected


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

    discovered_institutions = discover_institutions(secrets_dir=secrets_path)

    ids_list = [value for value in (ids or []) if value.strip() != ""]

    is_institution_id = [
        bool(_INSTITUTION_ID_RE.fullmatch(value)) for value in ids_list
    ]

    selected_accounts: List[DiscoveredAccount]

    # No ids: preserve existing behavior (discover institutions and prompt for accounts).
    if not ids_list:
        accounts = _discover_accounts(
            institutions=discovered_institutions,
            secrets_dir=secrets_path,
        )
        if not accounts:
            raise typer.BadParameter("No accounts found for saved institutions")

        if all_accounts:
            selected_accounts = accounts
        else:
            try:
                selected_accounts = _prompt_for_accounts(accounts)
            except ValueError as exc:
                raise typer.BadParameter(str(exc)) from exc

    # All ids match institution id pattern: treat as institutions.
    elif all(is_institution_id):
        institutions_by_id = {
            inst.institution_id: inst for inst in discovered_institutions
        }
        unknown = [value for value in ids_list if value not in institutions_by_id]
        if unknown:
            raise typer.BadParameter(
                "Unknown institution(s): " + ", ".join(sorted(set(unknown)))
            )

        institutions = [institutions_by_id[value] for value in ids_list]
        accounts = _discover_accounts(institutions=institutions, secrets_dir=secrets_path)
        if not accounts:
            raise typer.BadParameter("No accounts found for provided institutions")

        if all_accounts:
            selected_accounts = accounts
        else:
            try:
                selected_accounts = _prompt_for_accounts(accounts)
            except ValueError as exc:
                raise typer.BadParameter(str(exc)) from exc

    # Mixed institutions + account ids is ambiguous.
    elif any(is_institution_id):
        raise typer.BadParameter(
            "Pass either institution ids (ins_123) or account_ids, not a mix."
        )

    # Otherwise treat as a list of account_ids.
    else:
        if all_accounts:
            raise typer.BadParameter(
                "--all-accounts is only valid when passing institution ids."
            )

        accounts = _discover_accounts(
            institutions=discovered_institutions,
            secrets_dir=secrets_path,
        )
        if not accounts:
            raise typer.BadParameter("No accounts found for saved institutions")

        accounts_by_id: Dict[str, List[DiscoveredAccount]] = {}
        for account in accounts:
            accounts_by_id.setdefault(account.account_id, []).append(account)

        missing = [value for value in ids_list if value not in accounts_by_id]
        if missing:
            raise typer.BadParameter(
                "Unknown account_id(s): " + ", ".join(sorted(set(missing)))
            )

        ambiguous = [
            value for value in ids_list if len(accounts_by_id.get(value, [])) > 1
        ]
        if ambiguous:
            raise typer.BadParameter(
                "Ambiguous account_id(s) (match multiple institutions): "
                + ", ".join(sorted(set(ambiguous)))
            )

        selected_accounts = [accounts_by_id[value][0] for value in ids_list]

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
