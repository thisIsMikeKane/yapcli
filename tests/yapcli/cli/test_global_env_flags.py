from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

import pytest
import questionary
from typer.testing import CliRunner

from yapcli import cli


def test_production_flag_overrides_plaid_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    runner = CliRunner()

    # Ensure we're not relying on an external environment.
    monkeypatch.delenv("PLAID_ENV", raising=False)

    secrets_dir = tmp_path / "secrets"
    secrets_dir.mkdir()
    (secrets_dir / "ins_1_item_id").write_text("item-1")
    (secrets_dir / "ins_1_access_token").write_text("access-1")

    seen_env: list[str] = []

    class FakeBackend:
        def __init__(
            self,
            *,
            access_token: str | None = None,
            item_id: str | None = None,
            env=None,
        ) -> None:
            # The whole point: this should be set by the global CLI flag
            seen_env.append(os.environ.get("PLAID_ENV") or "")
            self.access_token = access_token
            self.item_id = item_id

        def get_accounts(self) -> Dict[str, Any]:
            return {
                "accounts": [
                    {
                        "account_id": f"acct-{self.access_token}",
                        "type": "depository",
                        "name": "Checking",
                        "subtype": "checking",
                        "mask": "0000",
                    }
                ]
            }

        def get_transactions(self, *, account_id: str | None = None) -> Dict[str, Any]:
            return {
                "transactions": [
                    {
                        "transaction_id": f"txn-{self.access_token}",
                        "account_id": account_id,
                        "amount": 1.23,
                        "date": "2026-02-15",
                    }
                ]
            }

        def get_item(self) -> Dict[str, Any]:
            return {"error": None, "item": {}, "institution": {"name": "Test Bank"}}

    import yapcli.cli.transactions as transactions
    import yapcli.accounts as accounts
    import yapcli.institutions as institutions

    monkeypatch.setattr(transactions, "PlaidBackend", FakeBackend)
    monkeypatch.setattr(accounts, "PlaidBackend", FakeBackend)
    monkeypatch.setattr(institutions, "PlaidBackend", FakeBackend)

    def fail_checkbox(*args, **kwargs):
        raise AssertionError("questionary.checkbox should not be called")

    monkeypatch.setattr(questionary, "checkbox", fail_checkbox)

    out_dir = tmp_path / "out"

    monkeypatch.setenv("PLAID_SECRETS_DIR", str(secrets_dir))

    result = runner.invoke(
        cli.app,
        [
            "--production",
            "transactions",
            "--all-accounts",
            "--out-dir",
            str(out_dir),
        ],
    )

    assert result.exit_code == 0
    assert "production" in seen_env


def test_sandbox_flag_overrides_existing_plaid_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    runner = CliRunner()

    # Start with production, then force sandbox via flag.
    monkeypatch.setenv("PLAID_ENV", "production")

    secrets_dir = tmp_path / "secrets"
    secrets_dir.mkdir()
    (secrets_dir / "ins_1_item_id").write_text("item-1")
    (secrets_dir / "ins_1_access_token").write_text("access-1")

    seen_env: list[str] = []

    class FakeBackend:
        def __init__(
            self,
            *,
            access_token: str | None = None,
            item_id: str | None = None,
            env=None,
        ) -> None:
            seen_env.append(os.environ.get("PLAID_ENV") or "")
            self.access_token = access_token
            self.item_id = item_id

        def get_accounts(self) -> Dict[str, Any]:
            return {
                "accounts": [
                    {
                        "account_id": f"acct-{self.access_token}",
                        "type": "depository",
                        "name": "Checking",
                        "subtype": "checking",
                        "mask": "0000",
                    }
                ]
            }

        def get_transactions(self, *, account_id: str | None = None) -> Dict[str, Any]:
            return {
                "transactions": [
                    {
                        "transaction_id": f"txn-{self.access_token}",
                        "account_id": account_id,
                        "amount": 1.23,
                        "date": "2026-02-15",
                    }
                ]
            }

        def get_item(self) -> Dict[str, Any]:
            return {"error": None, "item": {}, "institution": {"name": "Test Bank"}}

    import yapcli.cli.transactions as transactions
    import yapcli.accounts as accounts
    import yapcli.institutions as institutions

    monkeypatch.setattr(transactions, "PlaidBackend", FakeBackend)
    monkeypatch.setattr(accounts, "PlaidBackend", FakeBackend)
    monkeypatch.setattr(institutions, "PlaidBackend", FakeBackend)

    def fail_checkbox(*args, **kwargs):
        raise AssertionError("questionary.checkbox should not be called")

    monkeypatch.setattr(questionary, "checkbox", fail_checkbox)

    out_dir = tmp_path / "out"

    monkeypatch.setenv("PLAID_SECRETS_DIR", str(secrets_dir))

    result = runner.invoke(
        cli.app,
        [
            "--sandbox",
            "transactions",
            "--all-accounts",
            "--out-dir",
            str(out_dir),
        ],
    )

    assert result.exit_code == 0
    assert "sandbox" in seen_env
