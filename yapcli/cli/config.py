from __future__ import annotations

from pathlib import Path
from typing import Dict

import typer
from dotenv import dotenv_values

from yapcli.utils import default_env_file_path

app = typer.Typer(help="Manage yapcli configuration values.")

_DEFAULT_KEY_ORDER = [
    "PLAID_CLIENT_ID",
    "PLAID_SECRET",
    "PLAID_ENV",
    "PLAID_PRODUCTS",
    "PLAID_COUNTRY_CODES",
    "PLAID_REDIRECT_URI",
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


@app.command("path")
def config_path() -> None:
    """Print the default path used for yapcli .env configuration."""

    typer.echo(str(default_env_file_path()))


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

    values = dict(existing)
    values["PLAID_CLIENT_ID"] = client_id
    values["PLAID_ENV"] = plaid_env

    update_secret = True
    if existing.get("PLAID_SECRET"):
        update_secret = typer.confirm(
            "PLAID_SECRET already exists. Update it?",
            default=False,
        )

    if update_secret:
        values["PLAID_SECRET"] = typer.prompt(
            "PLAID_SECRET",
            default=existing.get("PLAID_SECRET", ""),
            hide_input=True,
            confirmation_prompt=True,
            show_default=False,
        ).strip()

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
