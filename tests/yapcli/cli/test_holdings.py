from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pytest
import questionary
from typer.testing import CliRunner

from yapcli import cli


def test_holdings_all_accounts_without_ids_writes_csv(
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

        def get_holdings(self) -> Dict[str, Any]:
            return {
                "error": None,
                "holdings": {
                    "holdings": [
                        {
                            "account_id": f"acct-{self.access_token}",
                            "security_id": "sec-1",
                            "quantity": 1.0,
                        }
                    ]
                },
            }

        def get_item(self) -> Dict[str, Any]:
            return {"error": None, "item": {}, "institution": {"name": "Test Bank"}}

    import yapcli.cli.holdings as holdings
    import yapcli.accounts as accounts
    import yapcli.institutions as institutions

    monkeypatch.setattr(holdings, "PlaidBackend", FakeBackend)
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
            "holdings",
            "--all-accounts",
            "--out-dir",
            str(out_dir),
        ],
    )

    assert result.exit_code == 0

    files = list(out_dir.glob("ins_1_9999_*.csv"))
    assert len(files) == 1
