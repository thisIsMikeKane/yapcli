"""Tests for package configuration."""

from pathlib import Path

def test_build_script_exists(project_root: Path) -> None:
    """Verify build_frontend.py exists."""
    script = project_root / "scripts" / "build_frontend.py"
    assert script.exists(), "scripts/build_frontend.py not found"
