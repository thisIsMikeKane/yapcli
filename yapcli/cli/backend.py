from __future__ import annotations

import typer

from yapcli.server import PlaidBackend

app = typer.Typer()

_ALLOWED_PRODUCTS = {"transactions", "investments"}


def _parse_products(value: str | None) -> list[str] | None:
    if value is None:
        return None
    raw = value.strip()
    if raw == "":
        return None

    parts = [p.strip().lower() for p in raw.split(",")]
    parts = [p for p in parts if p]
    if not parts:
        return None

    invalid = sorted({p for p in parts if p not in _ALLOWED_PRODUCTS})
    if invalid:
        allowed = ", ".join(sorted(_ALLOWED_PRODUCTS))
        bad = ", ".join(invalid)
        raise typer.BadParameter(
            f"Invalid --products value(s): {bad}. Allowed values: {allowed}"
        )

    return parts


@app.command()
def serve(
    port: int = typer.Option(
        8000,
        "--port",
        help="Port for the local Flask backend server.",
        show_default=True,
    ),
    products: str | None = typer.Option(
        None,
        "--products",
        help=(
            "Comma-separated Plaid products to request during Link token creation. "
            "Example: --products=transactions,investments"
        ),
    ),
) -> None:
    """Run the local Plaid backend server (for development and internal use)."""
    flask_app = PlaidBackend(products=_parse_products(products)).app
    flask_app.run(port=port)
