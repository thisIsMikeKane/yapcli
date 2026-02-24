from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, cast

import questionary
import typer

from yapcli.institutions import DiscoveredInstitution
from yapcli.institutions import discover_institutions
from yapcli.secrets import load_credentials
from yapcli.server import PlaidBackend

_INSTITUTION_ID_RE = re.compile(r"ins_\d+")


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
        type = self.type or "unknown"
        subtype = self.subtype or "unknown"
        mask = f"••••{self.mask}" if self.mask else ""
        return f"{bank} - {display_name} ({type}/{subtype}) {mask}".strip()


def _normalize_ids(ids: Optional[Sequence[str]]) -> List[str]:
    return [value for value in (ids or []) if value.strip() != ""]


def _validate_account_types(
    *,
    selected_accounts: List[DiscoveredAccount],
    allowed_types: Optional[Set[str]],
    ids_were_account_ids: bool,
) -> List[DiscoveredAccount]:
    if allowed_types is None:
        return selected_accounts

    def is_allowed(account: DiscoveredAccount) -> bool:
        return account.type in allowed_types

    disallowed = [account for account in selected_accounts if not is_allowed(account)]
    allowed = [account for account in selected_accounts if is_allowed(account)]

    if ids_were_account_ids and disallowed:
        parts: List[str] = []
        for account in disallowed:
            parts.append(
                f"{account.account_id} (type={account.type or 'unknown'}, institution={account.institution_id})"
            )
        raise typer.BadParameter(
            "Account(s) not eligible for this command: "
            + ", ".join(parts)
            + ". Allowed types: "
            + ", ".join(sorted(allowed_types))
        )

    if not allowed:
        raise typer.BadParameter(
            "No eligible accounts found. Allowed types: "
            + ", ".join(sorted(allowed_types))
        )

    return allowed


def _eligible_accounts(
    *,
    accounts: List[DiscoveredAccount],
    allowed_types: Optional[Set[str]],
) -> List[DiscoveredAccount]:
    if allowed_types is None:
        return accounts

    eligible = [account for account in accounts if account.type in allowed_types]
    if not eligible:
        raise typer.BadParameter(
            "No eligible accounts found. Allowed types: "
            + ", ".join(sorted(allowed_types))
        )
    return eligible


def resolve_target_accounts(
    *,
    ids: Optional[Sequence[str]],
    secrets_dir: Path,
    all_accounts: bool,
    allowed_account_types: Optional[Set[str]] = None,
) -> List[DiscoveredAccount]:
    """Resolve accounts to process.

    Preserves the institution_id/account_id argument semantics from the
    `transactions` CLI command and adds an optional account-type validation.
    """

    discovered_institutions = discover_institutions(secrets_dir=secrets_dir)

    ids_list = _normalize_ids(ids)
    is_institution_id = [
        bool(_INSTITUTION_ID_RE.fullmatch(value)) for value in ids_list
    ]

    selected_accounts: List[DiscoveredAccount]

    # No ids: discover institutions and prompt for accounts unless --all-accounts.
    if not ids_list:
        accounts = _discover_accounts(
            institutions=discovered_institutions,
            secrets_dir=secrets_dir,
        )
        if not accounts:
            raise typer.BadParameter("No accounts found for saved institutions")

        accounts = _eligible_accounts(
            accounts=accounts, allowed_types=allowed_account_types
        )

        if all_accounts:
            selected_accounts = accounts
        else:
            try:
                selected_accounts = _prompt_for_accounts(accounts)
            except ValueError as exc:
                raise typer.BadParameter(str(exc)) from exc

        return selected_accounts

    # All ids match institution id pattern: treat as institutions.
    if all(is_institution_id):
        institutions_by_id = {
            inst.institution_id: inst for inst in discovered_institutions
        }
        unknown = [value for value in ids_list if value not in institutions_by_id]
        if unknown:
            raise typer.BadParameter(
                "Unknown institution(s): " + ", ".join(sorted(set(unknown)))
            )

        institutions = [institutions_by_id[value] for value in ids_list]
        accounts = _discover_accounts(
            institutions=institutions, secrets_dir=secrets_dir
        )
        if not accounts:
            raise typer.BadParameter("No accounts found for provided institutions")

        accounts = _eligible_accounts(
            accounts=accounts, allowed_types=allowed_account_types
        )

        if all_accounts:
            selected_accounts = accounts
        else:
            try:
                selected_accounts = _prompt_for_accounts(accounts)
            except ValueError as exc:
                raise typer.BadParameter(str(exc)) from exc

        return selected_accounts

    # Mixed institutions + account ids is ambiguous.
    if any(is_institution_id):
        raise typer.BadParameter(
            "Pass either institution ids (ins_123) or account_ids, not a mix."
        )

    # Otherwise treat as a list of account_ids.
    if all_accounts:
        raise typer.BadParameter(
            "--all-accounts is only valid when passing institution ids."
        )

    accounts = _discover_accounts(
        institutions=discovered_institutions,
        secrets_dir=secrets_dir,
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

    ambiguous = [value for value in ids_list if len(accounts_by_id.get(value, [])) > 1]
    if ambiguous:
        raise typer.BadParameter(
            "Ambiguous account_id(s) (match multiple institutions): "
            + ", ".join(sorted(set(ambiguous)))
        )

    selected_accounts = [accounts_by_id[value][0] for value in ids_list]
    return _validate_account_types(
        selected_accounts=selected_accounts,
        allowed_types=allowed_account_types,
        ids_were_account_ids=True,
    )


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
