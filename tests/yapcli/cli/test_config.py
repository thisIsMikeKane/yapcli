from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from yapcli import cli


def test_config_path_prints_default_env_path(
    monkeypatch: pytest.MonkeyPatch,
    runner: CliRunner,
    tmp_path: Path,
) -> None:
    env_path = tmp_path / ".env"

    import yapcli.cli.config as config_cli

    monkeypatch.setattr(config_cli, "default_env_file_path", lambda: env_path)

    result = runner.invoke(cli.app, ["config", "path"])

    assert result.exit_code == 0
    assert str(env_path) in result.output


def test_config_set_writes_value_to_env_file(
    monkeypatch: pytest.MonkeyPatch,
    runner: CliRunner,
    tmp_path: Path,
) -> None:
    env_path = tmp_path / ".env"

    import yapcli.cli.config as config_cli

    monkeypatch.setattr(config_cli, "default_env_file_path", lambda: env_path)

    result = runner.invoke(
        cli.app,
        ["config", "set", "PLAID_CLIENT_ID", "client-123"],
    )

    assert result.exit_code == 0
    contents = env_path.read_text()
    assert "PLAID_CLIENT_ID=client-123" in contents


def test_config_init_writes_prompted_values(
    monkeypatch: pytest.MonkeyPatch,
    runner: CliRunner,
    tmp_path: Path,
) -> None:
    env_path = tmp_path / ".env"

    import yapcli.cli.config as config_cli

    monkeypatch.setattr(config_cli, "default_env_file_path", lambda: env_path)

    prompts = iter(["client-id", "sandbox", "super-secret"])

    def fake_prompt(*_args, **_kwargs):
        return next(prompts)

    monkeypatch.setattr(config_cli.typer, "prompt", fake_prompt)

    result = runner.invoke(cli.app, ["config", "init"])

    assert result.exit_code == 0
    contents = env_path.read_text()
    assert "PLAID_CLIENT_ID=client-id" in contents
    assert "PLAID_ENV=sandbox" in contents
    assert "PLAID_SECRET=super-secret" in contents
