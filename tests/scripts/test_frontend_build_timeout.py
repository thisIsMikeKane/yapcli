"""Tests for frontend build fixture timeout behavior."""

import subprocess
from pathlib import Path

import pytest

from tests.scripts import conftest as scripts_conftest


def test_frontend_build_timeout_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """frontend_build fixture should fail, not skip, on timeout."""
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "build_frontend.py").write_text("print('stub')", encoding="utf-8")

    def raise_timeout(*args: object, **kwargs: object) -> subprocess.CompletedProcess:
        raise subprocess.TimeoutExpired(cmd=["python", "build_frontend.py"], timeout=240)

    monkeypatch.setattr(scripts_conftest.subprocess, "run", raise_timeout)

    with pytest.raises(pytest.fail.Exception, match="timed out after 240 seconds"):
        scripts_conftest.frontend_build.__wrapped__(tmp_path)
