from __future__ import annotations

from yapcli.server import _resolve_plaid_env_and_secret


def test_defaults_to_production_when_both_env_secrets_defined_and_plaid_env_missing() -> None:
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


def test_uses_env_specific_secret_when_plaid_secret_missing_and_env_is_sandbox() -> None:
    env = {
        "PLAID_CLIENT_ID": "client",
        "PLAID_ENV": "sandbox",
        "PLAID_SANDBOX_SECRET": "sandbox-secret",
        # PLAID_SECRET missing
    }

    plaid_env, plaid_secret = _resolve_plaid_env_and_secret(env)
    assert plaid_env == "sandbox"
    assert plaid_secret == "sandbox-secret"


def test_uses_env_specific_secret_when_plaid_secret_missing_and_env_is_production() -> None:
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
