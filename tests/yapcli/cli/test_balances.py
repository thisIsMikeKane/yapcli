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

        def get_item(self) -> Dict[str, Any]:
            return {"error": None, "item": {}, "institution": {"name": "Test Bank"}}

    import yapcli.cli.balances as balances
    import yapcli.utils as utils

    monkeypatch.setattr(balances, "PlaidBackend", FakeBackend)
    monkeypatch.setattr(utils, "PlaidBackend", FakeBackend)

    class FakeCheckbox:
        def ask(self):
            return ["ins_1", "ins_2"]

    def fake_checkbox(*args, **kwargs):
        return FakeCheckbox()

    monkeypatch.setattr(utils.questionary, "checkbox", fake_checkbox)

    out_dir = tmp_path / "out"

    result = runner.invoke(
        cli.app,
        [
            "balances",
            "--secrets-dir",
            str(secrets_dir),
            "--out-dir",
            str(out_dir),
        ],
    )

    assert result.exit_code == 0

    ins_1_files = list(out_dir.glob("ins_1_*.csv"))
    ins_2_files = list(out_dir.glob("ins_2_*.csv"))
    assert len(ins_1_files) == 1
    assert len(ins_2_files) == 1
