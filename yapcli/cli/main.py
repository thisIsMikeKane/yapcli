"""Command-line interface for the yapcli package."""

from __future__ import annotations

import datetime as dt
import os
from pathlib import Path

import typer
from rich.console import Console

from yapcli import __version__
from yapcli.cli.balances import app as balances_app
from yapcli.cli.link import app as link_app
from yapcli.cli.transactions import app as transactions_app
from yapcli.logging import configure_logging

console = Console()


def _get_default_log_dir() -> Path:
    """Get the default log directory, using user home for installed packages."""
    env_log_dir = os.getenv("YAPCLI_LOG_DIR")
    if env_log_dir:
        return Path(env_log_dir)
    
    # Try to use project root if running from source
    try:
        project_root = Path(__file__).resolve().parents[2]
        dev_logs = project_root / "logs"
        # Check if we're in a development environment
        if (project_root / "pyproject.toml").exists():
            return dev_logs
    except (IndexError, OSError):
        pass
    
    # Fall back to user home directory for installed packages
    return Path.home() / ".yapcli" / "logs"


LOG_DIR = _get_default_log_dir()

_LOGGING_CONFIGURED = False


def _configure_cli_logging(prefix: str) -> None:
    global _LOGGING_CONFIGURED
    if _LOGGING_CONFIGURED:
        return

    configure_logging(
        log_dir=LOG_DIR,
        prefix=prefix,
        started_at=dt.datetime.now(),
        level=os.getenv("YAPCLI_LOG_LEVEL", "INFO"),
    )
    _LOGGING_CONFIGURED = True


app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Utilities for interacting with Plaid programmatically.",
)
app.add_typer(link_app)
app.add_typer(balances_app)
app.add_typer(transactions_app)


def _version_callback(value: bool) -> None:
    """Render the CLI version when the eager --version flag is provided."""
    if value:
        _configure_cli_logging("version")
        console.print(f"[bold green]yapcli[/] v{__version__}")
        raise typer.Exit()


@app.callback()
def main_callback(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show the CLI version and exit.",
        is_eager=True,
        callback=_version_callback,
    ),
) -> None:
    """Handle global CLI options before dispatching to sub-commands."""

    prefix = ctx.invoked_subcommand or "cli"
    _configure_cli_logging(prefix)


def main() -> None:
    """Invoke the Typer application."""
    app(prog_name="yapcli")
