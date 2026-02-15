from typer.testing import CliRunner

from yapcli import cli


def test_help_shows_when_no_args(runner: CliRunner) -> None:
    result = runner.invoke(cli.app, [])

    assert result.exit_code == 2
    assert "Utilities for interacting with Plaid programmatically." in result.output
    assert "link" in result.output


def test_version_flag_outputs_version(runner: CliRunner) -> None:

    result = runner.invoke(cli.app, ["--version"])

    assert result.exit_code == 0
    assert "yapcli v0.0.1.dev" in result.output



