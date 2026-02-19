from __future__ import annotations

import os
from pathlib import Path

from yapcli import _load_default_dotenv
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


def test_load_default_dotenv_loads_values_from_default_env_file(
    monkeypatch,
    tmp_path: Path,
) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("PLAID_CLIENT_ID=from-config\n")

    monkeypatch.setattr("yapcli.default_env_file_path", lambda: env_path)
    monkeypatch.delenv("PLAID_CLIENT_ID", raising=False)

    loaded = _load_default_dotenv()

    assert loaded is True
    assert os.getenv("PLAID_CLIENT_ID") == "from-config"


def test_load_default_dotenv_does_not_override_existing_environment_value(
    monkeypatch,
    tmp_path: Path,
) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("PLAID_CLIENT_ID=from-config\n")

    monkeypatch.setattr("yapcli.default_env_file_path", lambda: env_path)
    monkeypatch.setenv("PLAID_CLIENT_ID", "already-set")

    loaded = _load_default_dotenv()

    assert loaded is True
    assert os.getenv("PLAID_CLIENT_ID") == "already-set"
