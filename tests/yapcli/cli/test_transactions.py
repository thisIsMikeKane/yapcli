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
                        "name": "Checking",
                        "subtype": "checking",
                        "mask": "0000",
                    }
                ]
            }

        def get_transactions(self, *, account_id: str | None = None) -> Dict[str, Any]:
            return {
                "latest_transactions": [
                    {
                        "transaction_id": f"txn-{self.access_token}",
                        "account_id": account_id,
                        "amount": 12.34,
                        "date": "2026-02-15",
                    }
                ]
            }

        def get_item(self) -> Dict[str, Any]:
            return {"error": None, "item": {}, "institution": {"name": "Test Bank"}}

    import yapcli.cli.transactions as transactions
    import yapcli.utils as utils

    monkeypatch.setattr(transactions, "PlaidBackend", FakeBackend)
    monkeypatch.setattr(utils, "PlaidBackend", FakeBackend)

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

    ins_1_files = list(out_dir.glob("ins_1_0000_*.csv"))
    ins_2_files = list(out_dir.glob("ins_2_0000_*.csv"))
    assert len(ins_1_files) == 1
    assert len(ins_2_files) == 1


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
                        "name": "Checking",
                        "subtype": "checking",
                        "mask": "0000",
                    }
                ]
            }

        def get_transactions(self, *, account_id: str | None = None) -> Dict[str, Any]:
            return {
                "latest_transactions": [
                    {
                        "transaction_id": f"txn-{self.access_token}",
                        "account_id": account_id,
                        "amount": 12.34,
                        "date": "2026-02-15",
                    }
                ]
            }

        def get_item(self) -> Dict[str, Any]:
            return {"error": None, "item": {}, "institution": {"name": "Test Bank"}}

    import yapcli.cli.transactions as transactions
    import yapcli.utils as utils

    monkeypatch.setattr(transactions, "PlaidBackend", FakeBackend)
    monkeypatch.setattr(utils, "PlaidBackend", FakeBackend)

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

    ins_1_files = list(out_dir.glob("ins_1_0000_*.csv"))
    ins_2_files = list(out_dir.glob("ins_2_0000_*.csv"))
    assert len(ins_1_files) == 1
    assert len(ins_2_files) == 1


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
                        "name": "Checking",
                        "subtype": "checking",
                        "mask": "0000",
                    }
                ]
            }

        def get_transactions(self, *, account_id: str | None = None) -> Dict[str, Any]:
            return {
                "latest_transactions": [
                    {
                        "transaction_id": f"txn-{self.access_token}",
                        "account_id": account_id,
                        "amount": 12.34,
                        "date": "2026-02-15",
                    }
                ]
            }

        def get_item(self) -> Dict[str, Any]:
            return {"error": None, "item": {}, "institution": {"name": "Test Bank"}}

    import yapcli.cli.transactions as transactions
    import yapcli.utils as utils

    monkeypatch.setattr(transactions, "PlaidBackend", FakeBackend)
    monkeypatch.setattr(utils, "PlaidBackend", FakeBackend)

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

    ins_1_files = list(out_dir.glob("ins_1_0000_*.csv"))
    ins_2_files = list(out_dir.glob("ins_2_0000_*.csv"))
    assert len(ins_1_files) == 1
    assert len(ins_2_files) == 1


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
                        "name": "Checking",
                        "subtype": "checking",
                        "mask": "0000",
                    }
                ]
            }

        def get_transactions(self, *, account_id: str | None = None) -> Dict[str, Any]:
            return {
                "latest_transactions": [
                    {
                        "transaction_id": f"txn-{self.access_token}",
                        "account_id": account_id,
                        "amount": 12.34,
                        "date": "2026-02-15",
                    }
                ]
            }

        def get_item(self) -> Dict[str, Any]:
            return {"error": None, "item": {}, "institution": {"name": "Test Bank"}}

    import yapcli.cli.transactions as transactions
    import yapcli.utils as utils

    monkeypatch.setattr(transactions, "PlaidBackend", FakeBackend)
    monkeypatch.setattr(utils, "PlaidBackend", FakeBackend)

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

    ins_1_files = list(out_dir.glob("ins_1_0000_*.csv"))
    ins_2_files = list(out_dir.glob("ins_2_0000_*.csv"))
    assert len(ins_1_files) == 1
    assert len(ins_2_files) == 1
