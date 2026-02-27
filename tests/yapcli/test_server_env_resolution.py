from __future__ import annotations

import os
from pathlib import Path

from yapcli.env import load_env_files
from yapcli.server import _resolve_plaid_env_and_secret


def test_defaults_to_production_when_both_env_secrets_defined_and_plaid_env_missing() -> (
    None
):
    env = {
        "PLAID_CLIENT_ID": "client",
        "PLAID_SANDBOX_SECRET": "sandbox-secret",
        "PLAID_PRODUCTION_SECRET": "production-secret",
        # PLAID_ENV missing
        # PLAID_SECRET missing
    }

    plaid_env, plaid_secret = _resolve_plaid_env_and_secret(env)
    assert plaid_env == "production"
    assert plaid_secret == "production-secret"


def test_uses_env_specific_secret_when_plaid_secret_missing_and_env_is_sandbox() -> (
    None
):
    env = {
        "PLAID_CLIENT_ID": "client",
        "PLAID_ENV": "sandbox",
        "PLAID_SANDBOX_SECRET": "sandbox-secret",
        # PLAID_SECRET missing
    }

    plaid_env, plaid_secret = _resolve_plaid_env_and_secret(env)
    assert plaid_env == "sandbox"
    assert plaid_secret == "sandbox-secret"


def test_defaults_to_sandbox_when_only_sandbox_secret_defined_and_plaid_env_missing() -> (
    None
):
    env = {
        "PLAID_CLIENT_ID": "client",
        "PLAID_SANDBOX_SECRET": "sandbox-secret",
        # PLAID_ENV missing
        # PLAID_PRODUCTION_SECRET missing
        # PLAID_SECRET missing
    }

    plaid_env, plaid_secret = _resolve_plaid_env_and_secret(env)
    assert plaid_env == "sandbox"
    assert plaid_secret == "sandbox-secret"


def test_uses_env_specific_secret_when_plaid_secret_missing_and_env_is_production() -> (
    None
):
    env = {
        "PLAID_CLIENT_ID": "client",
        "PLAID_ENV": "production",
        "PLAID_PRODUCTION_SECRET": "production-secret",
        # PLAID_SECRET missing
    }

    plaid_env, plaid_secret = _resolve_plaid_env_and_secret(env)
    assert plaid_env == "production"
    assert plaid_secret == "production-secret"


def test_plaid_secret_takes_precedence_over_env_specific_secrets() -> None:
    env = {
        "PLAID_CLIENT_ID": "client",
        "PLAID_ENV": "sandbox",
        "PLAID_SECRET": "direct-secret",
        "PLAID_SANDBOX_SECRET": "sandbox-secret",
        "PLAID_PRODUCTION_SECRET": "production-secret",
    }

    plaid_env, plaid_secret = _resolve_plaid_env_and_secret(env)
    assert plaid_env == "sandbox"
    assert plaid_secret == "direct-secret"


def test_load_env_files_applies_platform_then_cwd_without_overriding_shell_env(
    monkeypatch,
    tmp_path: Path,
) -> None:
    platform_env = tmp_path / "platform.env"
    cwd_env = tmp_path / "cwd.env"

    platform_env.write_text("PLAID_CLIENT_ID=from-platform\nPLAID_COUNTRY_CODES=US\n")
    cwd_env.write_text("PLAID_CLIENT_ID=from-cwd\n")

    monkeypatch.setattr("yapcli.env.platform_env_file_path", lambda: platform_env)
    monkeypatch.setattr("yapcli.env.cwd_env_file_path", lambda: cwd_env)

    monkeypatch.delenv("PLAID_CLIENT_ID", raising=False)
    monkeypatch.delenv("PLAID_COUNTRY_CODES", raising=False)

    load_env_files()

    # CWD overrides platform
    assert os.getenv("PLAID_CLIENT_ID") == "from-cwd"
    # Platform-only key is still applied
    assert os.getenv("PLAID_COUNTRY_CODES") == "US"


def test_load_env_files_does_not_override_shell_environment_value(
    monkeypatch,
    tmp_path: Path,
) -> None:
    platform_env = tmp_path / "platform.env"
    cwd_env = tmp_path / "cwd.env"

    platform_env.write_text("PLAID_CLIENT_ID=from-platform\n")
    cwd_env.write_text("PLAID_CLIENT_ID=from-cwd\n")

    monkeypatch.setattr("yapcli.env.platform_env_file_path", lambda: platform_env)
    monkeypatch.setattr("yapcli.env.cwd_env_file_path", lambda: cwd_env)

    monkeypatch.setenv("PLAID_CLIENT_ID", "already-set")

    load_env_files()

    assert os.getenv("PLAID_CLIENT_ID") == "already-set"


def test_load_env_files_skips_unrecognized_env_var_and_warns(
    monkeypatch,
    tmp_path: Path,
) -> None:
    platform_env = tmp_path / "platform.env"
    cwd_env = tmp_path / "cwd.env"

    platform_env.write_text("UNRECOGNIZED_VAR=from-platform\n")
    cwd_env.write_text("PLAID_CLIENT_ID=from-cwd\n")

    monkeypatch.setattr("yapcli.env.platform_env_file_path", lambda: platform_env)
    monkeypatch.setattr("yapcli.env.cwd_env_file_path", lambda: cwd_env)

    monkeypatch.delenv("UNRECOGNIZED_VAR", raising=False)
    monkeypatch.delenv("PLAID_CLIENT_ID", raising=False)

    warnings: list[str] = []

    def fake_warning(message: str, *args) -> None:
        if args:
            warnings.append(message.format(*args))
        else:
            warnings.append(message)

    monkeypatch.setattr("yapcli.env.logger.warning", fake_warning)

    load_env_files()

    assert os.getenv("UNRECOGNIZED_VAR") is None
    assert os.getenv("PLAID_CLIENT_ID") == "from-cwd"
    assert any("Skipping unrecognized env var" in w for w in warnings)
