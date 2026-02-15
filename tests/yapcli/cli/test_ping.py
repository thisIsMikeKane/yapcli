from typer.testing import CliRunner

from yapcli import cli

def test_ping_defaults_to_plaid(runner: CliRunner) -> None:
    result = runner.invoke(cli.app, ["ping"])

    assert result.exit_code == 0
    assert "Pinging plaid" in result.output
    assert "ok" in result.output


def test_ping_accepts_target_argument(runner: CliRunner) -> None:
    result = runner.invoke(cli.app, ["ping", "sandbox"])

    assert result.exit_code == 0
    assert "Pinging sandbox" in result.output