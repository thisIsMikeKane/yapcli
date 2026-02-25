from __future__ import annotations

import datetime as dt

from pathlib import Path
from typing import Any, Dict

import pytest
import questionary
from typer.testing import CliRunner

from yapcli import cli


def test_investment_transactions_account_ids_writes_csv_without_prompt(
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
                        "type": "investment",
                        "name": "Brokerage",
                        "subtype": "brokerage",
                        "mask": "9999",
                    }
                ]
            }

        def get_investments_transactions(self) -> Dict[str, Any]:
            return {
                "error": None,
                "investments_transactions": {
                    "investment_transactions": [
                        {
                            "investment_transaction_id": "itxn-1",
                            "account_id": f"acct-{self.access_token}",
                            "amount": 12.34,
                            "date": "2026-02-15",
                        }
                    ]
                },
            }

        def get_item(self) -> Dict[str, Any]:
            return {"error": None, "item": {}, "institution": {"name": "Test Bank"}}

    import yapcli.cli.investment_transactions as investment_transactions
    import yapcli.accounts as accounts
    import yapcli.institutions as institutions

    monkeypatch.setattr(investment_transactions, "PlaidBackend", FakeBackend)
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
            "investment_transactions",
            "acct-access-1",
            "--out-dir",
            str(out_dir),
        ],
    )

    assert result.exit_code == 0

    files = list(out_dir.glob("ins_1_9999_*.csv"))
    assert len(files) == 1


def test_investment_transactions_prompt_filters_out_credit_accounts(
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
                        "account_id": f"acct-credit-{self.access_token}",
                        "type": "credit",
                        "name": "Credit Card",
                        "subtype": "credit card",
                        "mask": "1111",
                    },
                    {
                        "account_id": f"acct-invest-{self.access_token}",
                        "type": "investment",
                        "name": "Brokerage",
                        "subtype": "brokerage",
                        "mask": "9999",
                    },
                ]
            }

        def get_investments_transactions(self) -> Dict[str, Any]:
            return {
                "error": None,
                "investments_transactions": {
                    "investment_transactions": [
                        {
                            "investment_transaction_id": "itxn-1",
                            "account_id": f"acct-invest-{self.access_token}",
                            "amount": 12.34,
                            "date": "2026-02-15",
                        }
                    ]
                },
            }

        def get_item(self) -> Dict[str, Any]:
            return {"error": None, "item": {}, "institution": {"name": "Test Bank"}}

    import yapcli.cli.investment_transactions as investment_transactions
    import yapcli.accounts as accounts
    import yapcli.institutions as institutions

    monkeypatch.setattr(investment_transactions, "PlaidBackend", FakeBackend)
    monkeypatch.setattr(accounts, "PlaidBackend", FakeBackend)
    monkeypatch.setattr(institutions, "PlaidBackend", FakeBackend)

    class FakeCheckbox:
        def ask(self):
            return ["ins_1|acct-invest-access-1"]

    def fake_checkbox(message, *, choices):
        # Ensure the prompt only shows eligible account types.
        titles = [c.title for c in choices]
        assert any("(investment/" in title for title in titles)
        assert not any("(credit/" in title for title in titles)
        return FakeCheckbox()

    monkeypatch.setattr(questionary, "checkbox", fake_checkbox)

    out_dir = tmp_path / "out"

    monkeypatch.setenv("PLAID_SECRETS_DIR", str(secrets_dir))

    result = runner.invoke(
        cli.app,
        [
            "investment_transactions",
            "--out-dir",
            str(out_dir),
        ],
    )

    assert result.exit_code == 0

    files = list(out_dir.glob("ins_1_9999_*.csv"))
    assert len(files) == 1


def test_investment_transactions_start_end_dates_passed_to_backend(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    runner = CliRunner()

    secrets_dir = tmp_path / "secrets"
    secrets_dir.mkdir()
    (secrets_dir / "ins_1_item_id").write_text("item-1")
    (secrets_dir / "ins_1_access_token").write_text("access-1")

    seen: dict[str, dt.date | None] = {"start_date": None, "end_date": None}

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
                        "type": "investment",
                        "name": "Brokerage",
                        "subtype": "brokerage",
                        "mask": "9999",
                    }
                ]
            }

        def get_investments_transactions(
            self,
            *,
            start_date: dt.date | None = None,
            end_date: dt.date | None = None,
        ) -> Dict[str, Any]:
            seen["start_date"] = start_date
            seen["end_date"] = end_date
            return {
                "error": None,
                "investments_transactions": {
                    "investment_transactions": [
                        {
                            "investment_transaction_id": "itxn-1",
                            "account_id": f"acct-{self.access_token}",
                            "amount": 12.34,
                            "date": "2026-02-15",
                        }
                    ]
                },
            }

        def get_item(self) -> Dict[str, Any]:
            return {"error": None, "item": {}, "institution": {"name": "Test Bank"}}

    import yapcli.cli.investment_transactions as investment_transactions
    import yapcli.accounts as accounts
    import yapcli.institutions as institutions

    monkeypatch.setattr(investment_transactions, "PlaidBackend", FakeBackend)
    monkeypatch.setattr(accounts, "PlaidBackend", FakeBackend)
    monkeypatch.setattr(institutions, "PlaidBackend", FakeBackend)

    monkeypatch.setattr(
        questionary,
        "checkbox",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("questionary.checkbox should not be called")
        ),
    )

    monkeypatch.setenv("PLAID_SECRETS_DIR", str(secrets_dir))

    result = runner.invoke(
        cli.app,
        [
            "investment_transactions",
            "acct-access-1",
            "--start_date",
            "2026-01-01",
            "--end_date",
            "2026-01-31",
            "--out-dir",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code == 0
    assert seen["start_date"] == dt.date(2026, 1, 1)
    assert seen["end_date"] == dt.date(2026, 1, 31)


def test_investment_transactions_rejects_start_date_after_end_date(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    runner = CliRunner()

    secrets_dir = tmp_path / "secrets"
    secrets_dir.mkdir()
    (secrets_dir / "ins_1_item_id").write_text("item-1")
    (secrets_dir / "ins_1_access_token").write_text("access-1")

    monkeypatch.setenv("PLAID_SECRETS_DIR", str(secrets_dir))

    result = runner.invoke(
        cli.app,
        [
            "investment_transactions",
            "acct-access-1",
            "--start_date",
            "2026-02-01",
            "--end_date",
            "2026-01-31",
            "--out-dir",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code != 0
    assert "--start_date cannot be after --end_date" in result.output
