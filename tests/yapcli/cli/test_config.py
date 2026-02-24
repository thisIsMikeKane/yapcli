from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from yapcli import cli


def test_config_paths_prints_loaded_env_files_and_default_dirs(
    monkeypatch: pytest.MonkeyPatch,
    runner: CliRunner,
    tmp_path: Path,
) -> None:
    import yapcli.cli.config as config_cli

    env_path = tmp_path / ".env"
    secrets_dir = tmp_path / "secrets"
    logs_dir = tmp_path / "logs"
    output_dir = tmp_path / "output"

    monkeypatch.setattr(config_cli, "loaded_env_file_paths", lambda: (env_path,))
    monkeypatch.setattr(config_cli, "default_secrets_dir", lambda: secrets_dir)
    monkeypatch.setattr(config_cli, "default_log_dir", lambda: logs_dir)
    monkeypatch.setattr(config_cli, "default_output_dir", lambda: output_dir)

    result = runner.invoke(cli.app, ["config", "paths"])

    assert result.exit_code == 0
    assert str(env_path) in result.output
    assert str(secrets_dir) in result.output
    assert str(logs_dir) in result.output
    assert str(output_dir) in result.output


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

    prompts = iter(
        [
            "client-id",
            "sandbox",
            "US,CA",
            "sandbox-secret",
            "production-secret",
        ]
    )

    def fake_prompt(*_args, **_kwargs):
        return next(prompts)

    monkeypatch.setattr(config_cli.typer, "prompt", fake_prompt)

    result = runner.invoke(cli.app, ["config", "init"])

    assert result.exit_code == 0
    contents = env_path.read_text()
    assert "PLAID_CLIENT_ID=client-id" in contents
    assert "PLAID_ENV=sandbox" in contents
    assert "PLAID_COUNTRY_CODES=US,CA" in contents
    assert "PLAID_SANDBOX_SECRET=sandbox-secret" in contents
    assert "PLAID_PRODUCTION_SECRET=production-secret" in contents
