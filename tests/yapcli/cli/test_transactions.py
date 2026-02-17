from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pytest
import questionary
from typer.testing import CliRunner

from yapcli import cli


def test_transactions_without_institution_prompts_and_writes_csv(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    runner = CliRunner()

    secrets_dir = tmp_path / "secrets"
    secrets_dir.mkdir()
    (secrets_dir / "ins_1_item_id").write_text("item-1")
    (secrets_dir / "ins_1_access_token").write_text("access-1")
    (secrets_dir / "ins_2_item_id").write_text("item-2")
    (secrets_dir / "ins_2_access_token").write_text("access-2")

    class FakeBackend:
        def __init__(
            self,
            *,
            access_token: str | None = None,
            item_id: str | None = None,
            env=None,
        ) -> None:
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
                        "amount": 12.34,
                        "date": "2026-02-15",
                    }
                ],
                "cursor": ("A" * 91) + "=",
            }

        def get_item(self) -> Dict[str, Any]:
            return {"error": None, "item": {}, "institution": {"name": "Test Bank"}}

    import yapcli.cli.transactions as transactions
    import yapcli.accounts as accounts
    import yapcli.institutions as institutions

    monkeypatch.setattr(transactions, "PlaidBackend", FakeBackend)
    monkeypatch.setattr(accounts, "PlaidBackend", FakeBackend)
    monkeypatch.setattr(institutions, "PlaidBackend", FakeBackend)

    class FakeCheckbox:
        def ask(self):
            return ["ins_1|acct-access-1", "ins_2|acct-access-2"]

    def fake_checkbox(*args, **kwargs):
        return FakeCheckbox()

    monkeypatch.setattr(questionary, "checkbox", fake_checkbox)

    out_dir = tmp_path / "out"

    result = runner.invoke(
        cli.app,
        [
            "transactions",
            "--secrets-dir",
            str(secrets_dir),
            "--out-dir",
            str(out_dir),
        ],
    )

    assert result.exit_code == 0

    csv_files = list(out_dir.rglob("*.csv"))
    assert len(csv_files) == 2
    assert sum("ins_1" in str(p) for p in csv_files) == 1
    assert sum("ins_2" in str(p) for p in csv_files) == 1


def test_transactions_with_account_ids_writes_csv_without_prompt(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    runner = CliRunner()

    secrets_dir = tmp_path / "secrets"
    secrets_dir.mkdir()
    (secrets_dir / "ins_1_item_id").write_text("item-1")
    (secrets_dir / "ins_1_access_token").write_text("access-1")
    (secrets_dir / "ins_2_item_id").write_text("item-2")
    (secrets_dir / "ins_2_access_token").write_text("access-2")

    class FakeBackend:
        def __init__(
            self,
            *,
            access_token: str | None = None,
            item_id: str | None = None,
            env=None,
        ) -> None:
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
                        "amount": 12.34,
                        "date": "2026-02-15",
                    }
                ],
                "cursor": ("A" * 91) + "=",
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

    result = runner.invoke(
        cli.app,
        [
            "transactions",
            "acct-access-1",
            "acct-access-2",
            "--secrets-dir",
            str(secrets_dir),
            "--out-dir",
            str(out_dir),
        ],
    )

    assert result.exit_code == 0

    csv_files = list(out_dir.rglob("*.csv"))
    assert len(csv_files) == 2
    assert sum("ins_1" in str(p) for p in csv_files) == 1
    assert sum("ins_2" in str(p) for p in csv_files) == 1


def test_transactions_with_institution_ids_all_accounts_skips_prompt(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    runner = CliRunner()

    secrets_dir = tmp_path / "secrets"
    secrets_dir.mkdir()
    (secrets_dir / "ins_1_item_id").write_text("item-1")
    (secrets_dir / "ins_1_access_token").write_text("access-1")
    (secrets_dir / "ins_2_item_id").write_text("item-2")
    (secrets_dir / "ins_2_access_token").write_text("access-2")

    class FakeBackend:
        def __init__(
            self,
            *,
            access_token: str | None = None,
            item_id: str | None = None,
            env=None,
        ) -> None:
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
                        "amount": 12.34,
                        "date": "2026-02-15",
                    }
                ],
                "cursor": ("A" * 91) + "=",
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

    result = runner.invoke(
        cli.app,
        [
            "transactions",
            "ins_1",
            "ins_2",
            "--all-accounts",
            "--secrets-dir",
            str(secrets_dir),
            "--out-dir",
            str(out_dir),
        ],
    )

    assert result.exit_code == 0

    csv_files = list(out_dir.rglob("*.csv"))
    assert len(csv_files) == 2
    assert sum("ins_1" in str(p) for p in csv_files) == 1
    assert sum("ins_2" in str(p) for p in csv_files) == 1


def test_transactions_all_accounts_without_ids_processes_everything(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    runner = CliRunner()

    secrets_dir = tmp_path / "secrets"
    secrets_dir.mkdir()
    (secrets_dir / "ins_1_item_id").write_text("item-1")
    (secrets_dir / "ins_1_access_token").write_text("access-1")
    (secrets_dir / "ins_2_item_id").write_text("item-2")
    (secrets_dir / "ins_2_access_token").write_text("access-2")

    class FakeBackend:
        def __init__(
            self,
            *,
            access_token: str | None = None,
            item_id: str | None = None,
            env=None,
        ) -> None:
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
                        "amount": 12.34,
                        "date": "2026-02-15",
                    }
                ],
                "cursor": ("A" * 91) + "=",
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

    result = runner.invoke(
        cli.app,
        [
            "transactions",
            "--all-accounts",
            "--secrets-dir",
            str(secrets_dir),
            "--out-dir",
            str(out_dir),
        ],
    )

    assert result.exit_code == 0

    csv_files = list(out_dir.rglob("*.csv"))
    assert len(csv_files) == 2
    assert sum("ins_1" in str(p) for p in csv_files) == 1
    assert sum("ins_2" in str(p) for p in csv_files) == 1


def test_transactions_warns_and_writes_modified_and_removed_csvs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    runner = CliRunner()

    secrets_dir = tmp_path / "secrets"
    secrets_dir.mkdir()
    (secrets_dir / "ins_1_item_id").write_text("item-1")
    (secrets_dir / "ins_1_access_token").write_text("access-1")

    class FakeBackend:
        def __init__(
            self,
            *,
            access_token: str | None = None,
            item_id: str | None = None,
            env=None,
        ) -> None:
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
                        "amount": 12.34,
                        "date": "2026-02-15",
                    }
                ],
                "modified": [
                    {
                        "transaction_id": f"txn-mod-{self.access_token}",
                        "account_id": account_id,
                        "amount": 99.99,
                        "date": "2026-02-16",
                    }
                ],
                "removed": [
                    {
                        "transaction_id": f"txn-rm-{self.access_token}",
                        "account_id": account_id,
                        "date": "2026-02-14",
                    }
                ],
                "cursor": ("A" * 91) + "=",
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

    result = runner.invoke(
        cli.app,
        [
            "transactions",
            "acct-access-1",
            "--secrets-dir",
            str(secrets_dir),
            "--out-dir",
            str(out_dir),
        ],
    )

    assert result.exit_code == 0
    assert "WARNING: Plaid sync returned modified=1 removed=1" in result.stdout

    csv_files = sorted(str(p) for p in out_dir.rglob("*.csv"))
    assert len(csv_files) == 3
    assert any("_modified_" in p for p in csv_files)
    assert any("_removed_" in p for p in csv_files)
