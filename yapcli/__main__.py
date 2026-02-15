"""Allow ``python -m yapcli`` to execute the CLI."""

from yapcli.cli import main


def _run() -> None:
    """Execute the CLI entry point."""
    main()


if __name__ == "__main__":  # pragma: no cover - module execution guard
    _run()
