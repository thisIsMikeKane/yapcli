import typer
from rich.console import Console

console = Console()
app = typer.Typer()


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
