"""Command-line interface for the py_pliad package."""

from __future__ import annotations

import typer
from rich.console import Console

from yapcli import __version__

console = Console()
app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Utilities for interacting with Plaid programmatically.",
)


def _version_callback(value: bool) -> None:
    """Render the CLI version when the eager --version flag is provided."""
    if value:
        console.print(f"[bold green]py-plaid[/] v{__version__}")
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


@app.command()
def ping(
    target: str = typer.Argument(
        "plaid",
        show_default=True,
        help="Friendly label identifying the system you are checking.",
    )
) -> None:
    """Perform a lightweight connectivity check to confirm the CLI is wired up."""
    console.print(f"[cyan]Pinging[/] [bold]{target}[/] ... [green]ok[/]")


def main() -> None:
    """Invoke the Typer application."""
    app(prog_name="py-plaid")


if __name__ == "__main__":  # pragma: no cover - module execution guard
    main()
