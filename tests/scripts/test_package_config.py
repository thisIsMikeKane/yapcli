"""Tests for package configuration."""

from pathlib import Path

import pytest


def test_pyproject_has_correct_entry_point(project_root: Path) -> None:
    """Verify pyproject.toml has yapcli entry point."""
    pyproject = project_root / "pyproject.toml"
    content = pyproject.read_text()
    
    assert "yapcli = " in content, "Entry point 'yapcli' not found"
    assert "yapcli.cli.main:main" in content, "Entry point should reference yapcli.cli.main:main"
    
    # Old entry point should not exist
    assert "py-plaid" not in content, "Old entry point 'py-plaid' should be removed"


def test_package_data_configured(project_root: Path) -> None:
    """Verify pyproject.toml includes package data for frontend."""
    pyproject = project_root / "pyproject.toml"
    content = pyproject.read_text()
    
    assert "[tool.setuptools.package-data]" in content, "package-data configuration missing"
    assert 'yapcli = ["frontend/build/**/*"]' in content, "Frontend build not in package-data"
    
    # Verify exclusions
    assert "exclude" in content, "Test exclusions not configured"


def test_build_script_exists(project_root: Path) -> None:
    """Verify build_frontend.py exists."""
    script = project_root / "scripts" / "build_frontend.py"
    assert script.exists(), "scripts/build_frontend.py not found"


def test_link_module_imports() -> None:
    """Verify link.py can be imported (syntax check)."""
    try:
        from yapcli.cli import link  # noqa: F401
    except Exception as e:
        pytest.fail(f"Failed to import link.py: {e}")


def test_main_module_imports() -> None:
    """Verify main.py can be imported (syntax check)."""
    try:
        from yapcli.cli import main  # noqa: F401
    except Exception as e:
        pytest.fail(f"Failed to import main.py: {e}")
