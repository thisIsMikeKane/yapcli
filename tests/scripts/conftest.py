"""Pytest fixtures for scripts/packaging tests."""

import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).resolve().parent.parent.parent


@pytest.fixture(scope="session")
def frontend_build(project_root: Path) -> Path:
    """Ensure frontend is built in the package directory."""
    build_script = project_root / "scripts" / "build_frontend.py"
    if not build_script.exists():
        pytest.skip("scripts/build_frontend.py not found")

    try:
        result = subprocess.run(
            [
                sys.executable,
                str(build_script),
                "build",
                "--install-mode",
                "ci",
                "--check-lock",
            ],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=180,  # 3 minute timeout for frontend build
        )
    except subprocess.TimeoutExpired:
        pytest.fail("Frontend build timed out after 180 seconds")

    if result.returncode != 0:
        output = "\n".join(filter(None, [result.stdout, result.stderr]))
        if "Error: Node version mismatch:" in output:
            pytest.fail(f"Frontend build failed: {output}")
        pytest.skip(f"Frontend build failed: {result.stderr}")

    expected_build = project_root / "yapcli" / "frontend" / "build"
    if not expected_build.exists():
        pytest.skip("Frontend build directory not created")

    return expected_build
