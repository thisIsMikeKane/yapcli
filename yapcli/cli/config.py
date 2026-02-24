from __future__ import annotations

from pathlib import Path
from typing import Dict

import typer
from dotenv import dotenv_values

from yapcli.env import loaded_env_file_paths
from yapcli.utils import (
    default_env_file_path,
    default_log_dir,
    default_output_dir,
    default_secrets_dir,
)

app = typer.Typer(help="Manage yapcli configuration values.")

_DEFAULT_KEY_ORDER = [
    "PLAID_CLIENT_ID",
    "PLAID_ENV",
    "PLAID_SANDBOX_SECRET",
    "PLAID_PRODUCTION_SECRET",
    "PLAID_COUNTRY_CODES",
    # Legacy override (takes precedence if set). Not prompted by `config init`.
    "PLAID_SECRET",
]


def _read_env_file(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}

    values = dotenv_values(path)
    return {key: value for key, value in values.items() if value is not None}


def _write_env_file(path: Path, values: Dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    ordered_keys = [key for key in _DEFAULT_KEY_ORDER if key in values]
    ordered_keys.extend(
        key for key in sorted(values) if key not in set(_DEFAULT_KEY_ORDER)
    )

    lines = [f"{key}={values[key]}" for key in ordered_keys]
    path.write_text("\n".join(lines) + "\n")


def _is_sensitive_key(key: str) -> bool:
    key_upper = key.upper()
    return "SECRET" in key_upper or "TOKEN" in key_upper or "PASSWORD" in key_upper


@app.command("paths")
def config_paths() -> None:
    """Print env/config paths used by yapcli."""

    loaded_envs = loaded_env_file_paths()
    typer.echo("Loaded .env files:")
    if loaded_envs:
        for path in loaded_envs:
            typer.echo(f"  {path}")
    else:
        typer.echo("  (none)")

    typer.echo("Default directories:")
    typer.echo(f"  secrets: {default_secrets_dir()}")
    typer.echo(f"  logs:    {default_log_dir()}")
    typer.echo(f"  output:  {default_output_dir()}")


@app.command("init")
def init_config(
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite an existing .env file instead of merging into it.",
    )
) -> None:
    """Interactively initialize the yapcli .env file."""

    env_path = default_env_file_path()
    existing = {} if force else _read_env_file(env_path)

    client_id = typer.prompt(
        "PLAID_CLIENT_ID",
        default=existing.get("PLAID_CLIENT_ID", ""),
    ).strip()
    plaid_env = typer.prompt(
        "PLAID_ENV",
        default=existing.get("PLAID_ENV", "sandbox"),
    ).strip()

    country_codes = typer.prompt(
        "PLAID_COUNTRY_CODES",
        default=existing.get("PLAID_COUNTRY_CODES", "US,CA"),
    ).strip()

    values = dict(existing)
    values["PLAID_CLIENT_ID"] = client_id
    values["PLAID_ENV"] = plaid_env
    values["PLAID_COUNTRY_CODES"] = country_codes

    def upsert_secret(key: str) -> None:
        update_secret = True
        if existing.get(key):
            update_secret = typer.confirm(
                f"{key} already exists. Update it?",
                default=False,
            )

        if update_secret:
            values[key] = typer.prompt(
                key,
                default=existing.get(key, ""),
                hide_input=True,
                confirmation_prompt=True,
                show_default=False,
            ).strip()

    # Prefer split secrets (matches .env.example). PLAID_SECRET remains supported
    # as a legacy override but is intentionally not prompted here.
    upsert_secret("PLAID_SANDBOX_SECRET")
    upsert_secret("PLAID_PRODUCTION_SECRET")

    _write_env_file(env_path, values)
    typer.echo(f"Wrote config: {env_path}")


@app.command("set")
def set_config_value(
    key: str = typer.Argument(
        ..., help="Environment variable key (e.g. PLAID_CLIENT_ID)."
    ),
    value: str | None = typer.Argument(
        None,
        help="Environment variable value. If omitted, you'll be prompted.",
    ),
) -> None:
    """Set or update a single key in the default yapcli .env file."""

    env_path = default_env_file_path()
    values = _read_env_file(env_path)

    key = key.strip()
    if key == "":
        raise typer.BadParameter("Key cannot be empty")

    if value is None:
        value = typer.prompt(
            f"{key}",
            default=values.get(key, ""),
            hide_input=_is_sensitive_key(key),
            confirmation_prompt=_is_sensitive_key(key),
            show_default=not _is_sensitive_key(key),
        )

    values[key] = value
    _write_env_file(env_path, values)
    typer.echo(f"Updated {key} in {env_path}")
