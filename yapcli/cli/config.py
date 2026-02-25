from __future__ import annotations

from pathlib import Path
from typing import Dict

import questionary
import typer
from dotenv import dotenv_values

from yapcli.env import CONSUMED_ENV_VARS, loaded_env_file_paths
from yapcli.utils import (
    default_env_file_path,
    default_log_dir,
    default_output_dir,
    default_secrets_dir,
)

app = typer.Typer(help="Manage yapcli configuration values.")
_KNOWN_ENV_KEYS = CONSUMED_ENV_VARS
_KNOWN_ENV_KEYS_SET = set(_KNOWN_ENV_KEYS)


def _read_env_file(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}

    values = dotenv_values(path)
    return {key: value for key, value in values.items() if value is not None}


def _write_env_file(path: Path, values: Dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    ordered_keys = [key for key in _KNOWN_ENV_KEYS if key in values]
    ordered_keys.extend(key for key in sorted(values) if key not in _KNOWN_ENV_KEYS_SET)

    lines = [f"{key}={values[key]}" for key in ordered_keys]
    path.write_text("\n".join(lines) + "\n")


def _is_sensitive_key(key: str) -> bool:
    key_upper = key.upper()
    return "SECRET" in key_upper or "TOKEN" in key_upper or "PASSWORD" in key_upper


def _ask_text(*, message: str, default: str = "") -> str:
    try:
        answer = questionary.text(message, default=default).ask()
    except KeyboardInterrupt as exc:
        raise typer.Exit(code=1) from exc

    if answer is None:
        raise typer.Exit(code=1)
    return str(answer).strip()


def _ask_password(*, message: str, default: str = "") -> str:
    try:
        answer = questionary.password(message).ask()
    except KeyboardInterrupt as exc:
        raise typer.Exit(code=1) from exc

    if answer is None:
        raise typer.Exit(code=1)

    cast_answer = str(answer).strip()
    if cast_answer == "" and default != "":
        return default
    return cast_answer


def _ask_confirm(*, message: str, default: bool = False) -> bool:
    try:
        answer = questionary.confirm(message, default=default).ask()
    except KeyboardInterrupt as exc:
        raise typer.Exit(code=1) from exc

    if answer is None:
        raise typer.Exit(code=1)
    return bool(answer)


def _ask_select_key(*, message: str) -> str:
    try:
        answer = questionary.select(message, choices=list(_KNOWN_ENV_KEYS)).ask()
    except KeyboardInterrupt as exc:
        raise typer.Exit(code=1) from exc

    if answer is None:
        raise typer.Exit(code=1)
    return str(answer).strip()


def _normalize_known_key(raw_key: str) -> str:
    key = raw_key.strip().upper()
    if key == "":
        raise typer.BadParameter("Key cannot be empty")
    if key not in _KNOWN_ENV_KEYS_SET:
        known = ", ".join(_KNOWN_ENV_KEYS)
        raise typer.BadParameter(f"Unknown key: {key}. Allowed keys: {known}")
    return key


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

    client_id = _ask_text(
        message="PLAID_CLIENT_ID",
        default=existing.get("PLAID_CLIENT_ID", ""),
    )
    plaid_env = _ask_text(
        message="PLAID_ENV",
        default=existing.get("PLAID_ENV", "sandbox"),
    )

    country_codes = _ask_text(
        message="PLAID_COUNTRY_CODES",
        default=existing.get("PLAID_COUNTRY_CODES", "US,CA"),
    )

    values = dict(existing)
    values["PLAID_CLIENT_ID"] = client_id
    values["PLAID_ENV"] = plaid_env
    values["PLAID_COUNTRY_CODES"] = country_codes

    def upsert_secret(key: str) -> None:
        update_secret = True
        if existing.get(key):
            update_secret = _ask_confirm(
                message=f"{key} already exists. Update it?",
                default=False,
            )

        if update_secret:
            values[key] = _ask_password(
                message=f"{key} (leave blank to keep existing)",
                default=existing.get(key, ""),
            )

    # Prefer split secrets (matches .env.example). PLAID_SECRET remains supported
    # as a legacy override but is intentionally not prompted here.
    upsert_secret("PLAID_SANDBOX_SECRET")
    upsert_secret("PLAID_PRODUCTION_SECRET")

    _write_env_file(env_path, values)
    typer.echo(f"Wrote config: {env_path}")


@app.command("set")
def set_config_value(
    key: str | None = typer.Argument(
        None,
        help="Environment variable key (must be a known yapcli env var).",
    ),
    value: str | None = typer.Argument(
        None,
        help="Environment variable value. If omitted, you'll be prompted.",
    ),
    interactive: bool = typer.Option(
        False,
        "--interactive",
        "-i",
        help="Use interactive prompts to choose key/value. Pure CLI mode when disabled.",
    ),
) -> None:
    """Set or update a single key in the default yapcli .env file."""

    env_path = default_env_file_path()
    values = _read_env_file(env_path)

    selected_key: str
    if interactive:
        selected_key = (
            _normalize_known_key(key)
            if key is not None
            else _ask_select_key(message="Select environment variable")
        )
    else:
        if key is None:
            raise typer.BadParameter(
                "Provide KEY and VALUE for pure CLI mode, or pass --interactive."
            )
        selected_key = _normalize_known_key(key)

    selected_value = value
    if selected_value is None:
        if _is_sensitive_key(selected_key):
            selected_value = _ask_password(
                message=f"{selected_key} (leave blank to keep existing)",
                default=values.get(selected_key, ""),
            )
        else:
            selected_value = _ask_text(
                message=selected_key,
                default=values.get(selected_key, ""),
            )

    values[selected_key] = selected_value
    _write_env_file(env_path, values)
    typer.echo(f"Updated {selected_key} in {env_path}")
