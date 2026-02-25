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


def test_config_set_rejects_unknown_key(
    monkeypatch: pytest.MonkeyPatch,
    runner: CliRunner,
    tmp_path: Path,
) -> None:
    env_path = tmp_path / ".env"

    import yapcli.cli.config as config_cli

    monkeypatch.setattr(config_cli, "default_env_file_path", lambda: env_path)

    result = runner.invoke(
        cli.app,
        ["config", "set", "UNKNOWN_VAR", "value"],
    )

    assert result.exit_code != 0
    assert "Unknown key" in result.output


def test_config_set_interactive_selects_key_and_prompts_value(
    monkeypatch: pytest.MonkeyPatch,
    runner: CliRunner,
    tmp_path: Path,
) -> None:
    env_path = tmp_path / ".env"

    import yapcli.cli.config as config_cli

    monkeypatch.setattr(config_cli, "default_env_file_path", lambda: env_path)

    class _Prompt:
        def __init__(self, value):
            self._value = value

        def ask(self):
            return self._value

    monkeypatch.setattr(
        config_cli.questionary,
        "select",
        lambda *_args, **_kwargs: _Prompt("PLAID_CLIENT_ID"),
    )
    monkeypatch.setattr(
        config_cli.questionary,
        "text",
        lambda *_args, **_kwargs: _Prompt("client-interactive"),
    )

    result = runner.invoke(
        cli.app,
        ["config", "set", "--interactive"],
    )

    assert result.exit_code == 0
    contents = env_path.read_text()
    assert "PLAID_CLIENT_ID=client-interactive" in contents


def test_config_init_writes_prompted_values(
    monkeypatch: pytest.MonkeyPatch,
    runner: CliRunner,
    tmp_path: Path,
) -> None:
    env_path = tmp_path / ".env"

    import yapcli.cli.config as config_cli

    monkeypatch.setattr(config_cli, "default_env_file_path", lambda: env_path)

    class _Prompt:
        def __init__(self, value):
            self._value = value

        def ask(self):
            return self._value

    text_prompts = iter(["client-id", "sandbox", "US,CA"])
    password_prompts = iter(["sandbox-secret", "production-secret"])

    monkeypatch.setattr(
        config_cli.questionary,
        "text",
        lambda *_args, **_kwargs: _Prompt(next(text_prompts)),
    )
    monkeypatch.setattr(
        config_cli.questionary,
        "password",
        lambda *_args, **_kwargs: _Prompt(next(password_prompts)),
    )
    monkeypatch.setattr(
        config_cli.questionary,
        "confirm",
        lambda *_args, **_kwargs: _Prompt(True),
    )

    result = runner.invoke(cli.app, ["config", "init"])

    assert result.exit_code == 0
    contents = env_path.read_text()
    assert "PLAID_CLIENT_ID=client-id" in contents
    assert "PLAID_ENV=sandbox" in contents
    assert "PLAID_COUNTRY_CODES=US,CA" in contents
    assert "PLAID_SANDBOX_SECRET=sandbox-secret" in contents
    assert "PLAID_PRODUCTION_SECRET=production-secret" in contents
