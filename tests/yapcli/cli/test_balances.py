from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pytest
from typer.testing import CliRunner

from yapcli import cli


def test_get_accounts_for_institution_reads_secrets_and_calls_backend(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    secrets_dir = tmp_path / "secrets"
    secrets_dir.mkdir()

    (secrets_dir / "ins_109511_item_id").write_text("item-abc")
    (secrets_dir / "ins_109511_access_token").write_text("access-xyz")

    captured: Dict[str, Any] = {}

    class FakeBackend:
        def __init__(
            self,
            *,
            access_token: str | None = None,
            item_id: str | None = None,
            env=None,
        ) -> None:
            captured["access_token"] = access_token
            captured["item_id"] = item_id

        def get_accounts(self) -> Dict[str, Any]:
            return {"accounts": [{"id": "acct-1"}]}

    import yapcli.cli.balances as balances_get

    monkeypatch.setattr(balances_get, "PlaidBackend", FakeBackend)

    payload = balances_get.get_accounts_for_institution(
        institution_id="ins_109511",
        secrets_dir=secrets_dir,
    )

    assert payload == {"accounts": [{"id": "acct-1"}]}
    assert captured["access_token"] == "access-xyz"
    assert captured["item_id"] == "item-abc"


def test_balances_without_institution_prompts_and_allows_all_selection(
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
            return {"accounts": [{"token": self.access_token, "item": self.item_id}]}

    import yapcli.cli.balances as balances

    monkeypatch.setattr(balances, "PlaidBackend", FakeBackend)

    result = runner.invoke(
        cli.app,
        ["balances", "--secrets-dir", str(secrets_dir)],
        input="all\n",
    )

    assert result.exit_code == 0
    assert "ins_1" in result.output
    assert "ins_2" in result.output
