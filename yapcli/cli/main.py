"""Command-line interface for the yapcli package."""

from __future__ import annotations

import typer
from rich.console import Console

from yapcli import __version__
from yapcli.cli.link import app as link_app

console = Console()
app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Utilities for interacting with Plaid programmatically.",
)
app.add_typer(link_app)


def _version_callback(value: bool) -> None:
    """Render the CLI version when the eager --version flag is provided."""
    if value:
        console.print(f"[bold green]yapcli[/] v{__version__}")
        raise typer.Exit()


@app.callback()
def main_callback(
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


def main() -> None:
    """Invoke the Typer application."""
    app(prog_name="yapcli")
