from __future__ import annotations

from typing import Any, Dict, List

import typer
from rich.console import Console

from yapcli.institutions import DiscoveredInstitution, discover_institutions
from yapcli.secrets import load_credentials
from yapcli.server import PlaidBackend
from yapcli.utils import default_secrets_dir

console = Console()
app = typer.Typer(help="List linked institutions and accounts.")


def _fetch_accounts(*, institution: DiscoveredInstitution) -> List[Dict[str, Any]]:
    secrets_dir = default_secrets_dir()
    item_id, access_token = load_credentials(
        institution_id=institution.institution_id,
        secrets_dir=secrets_dir,
    )
    backend = PlaidBackend(access_token=access_token, item_id=item_id)
    payload = backend.get_accounts()
    accounts = payload.get("accounts") if isinstance(payload, dict) else None
    if not isinstance(accounts, list):
        return []
    return [account for account in accounts if isinstance(account, dict)]


@app.command("list")
def list_linked() -> None:
    """Show linked institutions and discovered accounts."""

    secrets_dir = default_secrets_dir()
    try:
        institutions = discover_institutions(secrets_dir=secrets_dir)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

    for institution in institutions:
        bank_label = f" ({institution.bank_name})" if institution.bank_name else ""
        console.print(f"[bold]{institution.institution_id}[/]{bank_label}")

        try:
            accounts = _fetch_accounts(institution=institution)
        except Exception:
            console.print("  [yellow](unable to load accounts)[/]")
            continue

        if not accounts:
            console.print("  [dim](no accounts found)[/]")
            continue

        for account in accounts:
            account_id = str(account.get("account_id") or "unknown")
            name = str(account.get("name") or account.get("official_name") or "unnamed")
            account_type = str(account.get("type") or "unknown")
            subtype = str(account.get("subtype") or "unknown")
            mask = account.get("mask")
            suffix = f" ••••{mask}" if mask else ""
            console.print(
                f"  - {name} ({account_type}/{subtype}) account_id={account_id}{suffix}"
            )
