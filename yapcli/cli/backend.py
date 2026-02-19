from __future__ import annotations

import typer

from yapcli.server import PlaidBackend

app = typer.Typer()


@app.command()
def serve(
    port: int = typer.Option(
        8000,
        "--port",
        help="Port for the local Flask backend server.",
        show_default=True,
    ),
) -> None:
    """Run the local Plaid backend server."""
    flask_app = PlaidBackend().app
    flask_app.run(port=port)