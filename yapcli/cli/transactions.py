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
    """Fetch transactions for one or more accounts and write CSV(s)."""

    secrets_path = secrets_dir or default_secrets_dir()

    institutions = discover_institutions(secrets_dir=secrets_path)

    if institution_id is not None and institution_id.strip() != "":
        institutions = [
            inst for inst in institutions if inst.institution_id == institution_id
        ]
        if not institutions:
            raise typer.BadParameter(
                f"Unknown institution: {institution_id}"
            )

    accounts = _discover_accounts(institutions=institutions, secrets_dir=secrets_path)
    if not accounts:
        raise typer.BadParameter("No accounts found for saved institutions")

    try:
        selected_accounts = _prompt_for_accounts(accounts)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

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
