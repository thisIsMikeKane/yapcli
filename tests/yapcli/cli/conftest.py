from __future__ import annotations

from typing import Iterator

import pytest
from typer.testing import CliRunner


@pytest.fixture()
def runner() -> Iterator[CliRunner]:
    """Provide a CLI runner."""
    yield CliRunner()
