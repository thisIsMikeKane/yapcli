from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import json

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

    meta_files = list(out_dir.rglob("*_meta.json"))
    assert len(meta_files) == 2


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

    meta_files = list(out_dir.rglob("*_meta.json"))
    assert len(meta_files) == 2


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

    meta_files = list(out_dir.rglob("*_meta.json"))
    assert len(meta_files) == 2


def test_transactions_warns_when_backend_returns_error(
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
                "error": {
                    "status_code": None,
                    "display_message": "Cursor was empty repeatedly",
                    "error_code": "EMPTY_NEXT_CURSOR",
                    "error_type": "YAPCLI_ERROR",
                },
                "transactions": [],
                "modified": [],
                "removed": [],
                "cursor": "",
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
    assert "WARNING:" in result.output
    assert "EMPTY_NEXT_CURSOR" in result.output


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

    meta_files = list(out_dir.rglob("*_meta.json"))
    assert len(meta_files) == 2


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
    assert any(p.endswith("_modified.csv") for p in csv_files)
    assert any(p.endswith("_removed.csv") for p in csv_files)

    meta_files = sorted(str(p) for p in out_dir.rglob("*_meta.json"))
    assert len(meta_files) == 1


def test_transactions_cursor_option_only_allowed_for_single_account_id(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    runner = CliRunner()

    secrets_dir = tmp_path / "secrets"
    secrets_dir.mkdir()
    (secrets_dir / "ins_1_item_id").write_text("item-1")
    (secrets_dir / "ins_1_access_token").write_text("access-1")

    result = runner.invoke(
        cli.app,
        [
            "transactions",
            "acct-access-1",
            "acct-access-2",
            "--cursor",
            ("B" * 91) + "=",
            "--secrets-dir",
            str(secrets_dir),
            "--out-dir",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code != 0
    assert "--cursor is only valid when passing exactly one account_id" in result.output


def test_transactions_cursor_option_passes_cursor_to_backend_and_filename(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    runner = CliRunner()

    secrets_dir = tmp_path / "secrets"
    secrets_dir.mkdir()
    (secrets_dir / "ins_1_item_id").write_text("item-1")
    (secrets_dir / "ins_1_access_token").write_text("access-1")

    seen: dict[str, str | None] = {"cursor": None}
    requested_cursor = ("B" * 91) + "="

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

        def get_transactions(
            self, *, account_id: str | None = None, cursor: str | None = None
        ) -> Dict[str, Any]:
            seen["cursor"] = cursor
            return {
                "transactions": [
                    {
                        "transaction_id": f"txn-{self.access_token}",
                        "account_id": account_id,
                        "amount": 12.34,
                        "date": "2026-02-15",
                    }
                ],
                "cursor": cursor or ("A" * 91) + "=",
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
            "--cursor",
            requested_cursor,
            "--secrets-dir",
            str(secrets_dir),
            "--out-dir",
            str(out_dir),
        ],
    )

    assert result.exit_code == 0
    assert seen["cursor"] == requested_cursor

    csv_files = [p for p in out_dir.rglob("*.csv")]
    assert len(csv_files) == 1

    # Ensure account_id is not part of the account component path anymore.
    assert "acct-access-1" not in str(csv_files[0])

    meta_files = [p for p in out_dir.rglob("*_meta.json")]
    assert len(meta_files) == 1
    meta = json.loads(meta_files[0].read_text())
    assert meta["account_id"] == "acct-access-1"
    assert meta["cursor"] == requested_cursor
    assert "error" in meta
    assert meta["error"] is None


def test_transactions_sync_uses_latest_meta_cursor(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    runner = CliRunner()

    secrets_dir = tmp_path / "secrets"
    secrets_dir.mkdir()
    (secrets_dir / "ins_1_item_id").write_text("item-1")
    (secrets_dir / "ins_1_access_token").write_text("access-1")

    # Pre-create two meta files (older + newer) for the account.
    out_dir = tmp_path / "out"
    from yapcli.accounts import DiscoveredAccount

    account = DiscoveredAccount(
        institution_id="ins_1",
        bank_name="Test Bank",
        account_id="acct-access-1",
        type="depository",
        name="Checking",
        subtype="checking",
        mask="0000",
    )

    import yapcli.cli.transactions as transactions

    old_meta = transactions.build_transactions_meta_path(
        out_dir=out_dir, account=account, timestamp="20260215T000000Z"
    )
    old_meta.parent.mkdir(parents=True, exist_ok=True)
    old_meta.write_text(
        json.dumps({"account_id": account.account_id, "cursor": ("O" * 10)}, indent=2)
    )

    new_cursor = "N" * 10
    new_meta = transactions.build_transactions_meta_path(
        out_dir=out_dir, account=account, timestamp="20260216T000000Z"
    )
    new_meta.write_text(
        json.dumps({"account_id": account.account_id, "cursor": new_cursor}, indent=2)
    )

    seen: dict[str, str | None] = {"cursor": None}

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
                        "account_id": "acct-access-1",
                        "type": "depository",
                        "name": "Checking",
                        "subtype": "checking",
                        "mask": "0000",
                    }
                ]
            }

        def get_transactions(
            self, *, account_id: str | None = None, cursor: str | None = None
        ) -> Dict[str, Any]:
            seen["cursor"] = cursor
            return {
                "transactions": [
                    {
                        "transaction_id": f"txn-{self.access_token}",
                        "account_id": account_id,
                        "amount": 12.34,
                        "date": "2026-02-15",
                    }
                ],
                "cursor": cursor or "",
            }

        def get_item(self) -> Dict[str, Any]:
            return {"error": None, "item": {}, "institution": {"name": "Test Bank"}}

    import yapcli.accounts as accounts
    import yapcli.institutions as institutions

    monkeypatch.setattr(transactions, "PlaidBackend", FakeBackend)
    monkeypatch.setattr(accounts, "PlaidBackend", FakeBackend)
    monkeypatch.setattr(institutions, "PlaidBackend", FakeBackend)

    def fail_checkbox(*args, **kwargs):
        raise AssertionError("questionary.checkbox should not be called")

    monkeypatch.setattr(questionary, "checkbox", fail_checkbox)

    result = runner.invoke(
        cli.app,
        [
            "transactions",
            "acct-access-1",
            "--sync",
            "--secrets-dir",
            str(secrets_dir),
            "--out-dir",
            str(out_dir),
        ],
    )

    assert result.exit_code == 0
    assert seen["cursor"] == new_cursor


def test_transactions_sync_errors_on_account_id_mismatch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    runner = CliRunner()

    secrets_dir = tmp_path / "secrets"
    secrets_dir.mkdir()
    (secrets_dir / "ins_1_item_id").write_text("item-1")
    (secrets_dir / "ins_1_access_token").write_text("access-1")

    out_dir = tmp_path / "out"
    from yapcli.accounts import DiscoveredAccount

    account = DiscoveredAccount(
        institution_id="ins_1",
        bank_name="Test Bank",
        account_id="acct-access-1",
        type="depository",
        name="Checking",
        subtype="checking",
        mask="0000",
    )

    import yapcli.cli.transactions as transactions

    meta = transactions.build_transactions_meta_path(
        out_dir=out_dir, account=account, timestamp="20260216T000000Z"
    )
    meta.parent.mkdir(parents=True, exist_ok=True)
    meta.write_text(json.dumps({"account_id": "different", "cursor": "CUR"}, indent=2))

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
                        "account_id": "acct-access-1",
                        "type": "depository",
                        "name": "Checking",
                        "subtype": "checking",
                        "mask": "0000",
                    }
                ]
            }

        def get_transactions(
            self, *, account_id: str | None = None, cursor: str | None = None
        ) -> Dict[str, Any]:
            return {
                "transactions": [],
                "cursor": cursor or "",
            }

        def get_item(self) -> Dict[str, Any]:
            return {"error": None, "item": {}, "institution": {"name": "Test Bank"}}

    import yapcli.accounts as accounts
    import yapcli.institutions as institutions

    monkeypatch.setattr(transactions, "PlaidBackend", FakeBackend)
    monkeypatch.setattr(accounts, "PlaidBackend", FakeBackend)
    monkeypatch.setattr(institutions, "PlaidBackend", FakeBackend)

    def fail_checkbox(*args, **kwargs):
        raise AssertionError("questionary.checkbox should not be called")

    monkeypatch.setattr(questionary, "checkbox", fail_checkbox)

    result = runner.invoke(
        cli.app,
        [
            "transactions",
            "acct-access-1",
            "--sync",
            "--secrets-dir",
            str(secrets_dir),
            "--out-dir",
            str(out_dir),
        ],
    )

    assert result.exit_code != 0
    assert "Meta account_id mismatch" in result.output


def test_transactions_sync_with_no_existing_meta_runs_without_cursor(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    runner = CliRunner()

    secrets_dir = tmp_path / "secrets"
    secrets_dir.mkdir()
    (secrets_dir / "ins_1_item_id").write_text("item-1")
    (secrets_dir / "ins_1_access_token").write_text("access-1")

    out_dir = tmp_path / "out"
    seen: dict[str, str | None] = {"cursor": "sentinel"}

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
                        "account_id": "acct-access-1",
                        "type": "depository",
                        "name": "Checking",
                        "subtype": "checking",
                        "mask": "0000",
                    }
                ]
            }

        def get_transactions(
            self, *, account_id: str | None = None, cursor: str | None = None
        ) -> Dict[str, Any]:
            seen["cursor"] = cursor
            return {
                "transactions": [],
                "cursor": cursor or "",
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

    result = runner.invoke(
        cli.app,
        [
            "transactions",
            "acct-access-1",
            "--sync",
            "--secrets-dir",
            str(secrets_dir),
            "--out-dir",
            str(out_dir),
        ],
    )

    assert result.exit_code == 0
    assert seen["cursor"] is None
