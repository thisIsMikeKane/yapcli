from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, cast

import questionary

from yapcli.institutions import DiscoveredInstitution
from yapcli.secrets import load_credentials
from yapcli.server import PlaidBackend


@dataclass(frozen=True)
class DiscoveredAccount:
    institution_id: str
    bank_name: Optional[str]
    account_id: str
    type: Optional[str]
    name: Optional[str]
    subtype: Optional[str]
    mask: Optional[str]

    def choice_title(self) -> str:
        bank = self.bank_name or self.institution_id
        display_name = self.name or "(unnamed)"
        subtype = self.subtype or "unknown"
        mask = f"••••{self.mask}" if self.mask else ""
        return f"{bank} - {display_name} ({subtype}) {mask}".strip()


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

            account_type = account.get("type")
            name = account.get("name") or account.get("official_name")
            subtype = account.get("subtype")
            mask = account.get("mask")

            results.append(
                DiscoveredAccount(
                    institution_id=inst.institution_id,
                    bank_name=inst.bank_name,
                    account_id=account_id,
                    type=str(account_type) if account_type is not None else None,
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
