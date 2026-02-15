from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pytest


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
