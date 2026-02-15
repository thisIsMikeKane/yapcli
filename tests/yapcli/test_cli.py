from __future__ import annotations

from typing import Iterator

import pytest
from rich.console import Console
from typer.testing import CliRunner

from yapcli import cli


@pytest.fixture()
def runner(monkeypatch: pytest.MonkeyPatch) -> Iterator[CliRunner]:
    """Provide a CLI runner with deterministic console output."""
    console = Console(force_terminal=False, color_system=None, markup=True)
    monkeypatch.setattr(cli, "console", console)
    yield CliRunner()


def test_help_shows_when_no_args(runner: CliRunner) -> None:
    result = runner.invoke(cli.app, [])

    assert result.exit_code == 2
    assert "Utilities for interacting with Plaid programmatically." in result.output
    assert "ping" in result.output


def test_version_flag_outputs_version(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli, "__version__", "1.2.3")

    result = runner.invoke(cli.app, ["--version"])

    assert result.exit_code == 0
    assert "py-plaid v1.2.3" in result.output


def test_ping_defaults_to_plaid(runner: CliRunner) -> None:
    result = runner.invoke(cli.app, ["ping"])

    assert result.exit_code == 0
    assert "Pinging plaid" in result.output
    assert "ok" in result.output


def test_ping_accepts_target_argument(runner: CliRunner) -> None:
    result = runner.invoke(cli.app, ["ping", "sandbox"])

    assert result.exit_code == 0
    assert "Pinging sandbox" in result.output
