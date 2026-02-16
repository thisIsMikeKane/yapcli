"""Shared pytest configuration and fixtures."""

import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture
def project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def frontend_build(project_root: Path) -> Path:
    """Ensure frontend is built in the package directory."""
    build_script = project_root / "scripts" / "build_frontend.py"
    if not build_script.exists():
        pytest.skip("scripts/build_frontend.py not found")

    # Run the build script
    result = subprocess.run(
        [sys.executable, str(build_script)],
        cwd=project_root,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        pytest.skip(f"Frontend build failed: {result.stderr}")

    expected_build = project_root / "yapcli" / "frontend" / "build"
    if not expected_build.exists():
        pytest.skip("Frontend build directory not created")

    return expected_build
