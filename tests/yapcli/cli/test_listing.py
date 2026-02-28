from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from yapcli import cli
from yapcli.institutions import DiscoveredInstitution


def test_list_shows_institutions_and_accounts(
    monkeypatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()

    import yapcli.cli.listing as listing

    monkeypatch.setenv("PLAID_SECRETS_DIR", str(tmp_path / "secrets"))

    monkeypatch.setattr(
        listing,
        "discover_institutions",
        lambda **kwargs: [
            DiscoveredInstitution(institution_id="ins_1", bank_name="Bank A"),
            DiscoveredInstitution(institution_id="ins_2", bank_name=None),
        ],
    )

    def fake_fetch_accounts(*, institution: DiscoveredInstitution):
        if institution.institution_id == "ins_1":
            return [
                {
                    "account_id": "acc-1",
                    "name": "Checking",
                    "type": "depository",
                    "subtype": "checking",
                    "mask": "1234",
                }
            ]
        return [
            {
                "account_id": "acc-2",
                "official_name": "Brokerage Account",
                "type": "investment",
                "subtype": "brokerage",
            }
        ]

    monkeypatch.setattr(listing, "_fetch_accounts", fake_fetch_accounts)

    result = runner.invoke(cli.app, ["list"])

    assert result.exit_code == 0
    assert "ins_1 (Bank A)" in result.output
    assert "Checking (depository/checking) account_id=acc-1 ••••1234" in result.output
    assert "ins_2" in result.output
    assert "Brokerage Account (investment/brokerage) account_id=acc-2" in result.output


def test_list_handles_account_fetch_errors(monkeypatch, tmp_path: Path) -> None:
    runner = CliRunner()

    import yapcli.cli.listing as listing

    monkeypatch.setenv("PLAID_SECRETS_DIR", str(tmp_path / "secrets"))

    monkeypatch.setattr(
        listing,
        "discover_institutions",
        lambda **kwargs: [DiscoveredInstitution(institution_id="ins_1")],
    )

    def raise_fetch(*, institution: DiscoveredInstitution):
        raise RuntimeError("boom")

    monkeypatch.setattr(listing, "_fetch_accounts", raise_fetch)

    result = runner.invoke(cli.app, ["list"])

    assert result.exit_code == 0
    assert "ins_1" in result.output
    assert "(unable to load accounts)" in result.output
