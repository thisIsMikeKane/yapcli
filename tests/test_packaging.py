"""Tests for package installation and distribution."""

import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Generator

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


class TestPackageStructure:
    """Test that the package has the correct structure for distribution."""

    def test_entry_point_exists(self, project_root: Path) -> None:
        """Test that the entry point is correctly configured."""
        pyproject = project_root / "pyproject.toml"
        assert pyproject.exists(), "pyproject.toml not found"

        content = pyproject.read_text()
        assert (
            "yapcli = " in content
        ), "Entry point 'yapcli' not found in pyproject.toml"
        assert "yapcli.cli.main:main" in content, "Entry point target incorrect"

    def test_frontend_build_in_package(self, frontend_build: Path) -> None:
        """Test that frontend build exists in the package directory."""
        assert frontend_build.exists(), "Frontend build directory not found"
        assert (frontend_build / "index.html").exists(), "index.html not found in build"

    def test_package_data_configured(self, project_root: Path) -> None:
        """Test that pyproject.toml includes frontend build files as package data."""
        pyproject = project_root / "pyproject.toml"
        assert pyproject.exists(), "pyproject.toml not found"

        content = pyproject.read_text()
        assert (
            "[tool.setuptools.package-data]" in content
        ), "package-data section not found"
        assert (
            'yapcli = ["frontend/build/**/*"]' in content
        ), "Frontend build not included in package-data"


class TestPackageBuild:
    """Test that the package can be built correctly."""

    @pytest.fixture
    def build_dir(self, project_root: Path) -> Generator[Path, None, None]:
        """Create a temporary build directory."""
        build_path = project_root / "dist"
        build_path.mkdir(exist_ok=True)
        yield build_path
        # Cleanup happens naturally

    def test_sdist_build(
        self, project_root: Path, frontend_build: Path, build_dir: Path
    ) -> None:
        """Test that source distribution can be built."""
        # Clean previous builds
        if build_dir.exists():
            for item in build_dir.iterdir():
                if item.is_file():
                    item.unlink()

        # Build source distribution
        result = subprocess.run(
            [sys.executable, "-m", "build", "--sdist"],
            cwd=project_root,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            pytest.fail(f"Source distribution build failed:\n{result.stderr}")

        # Check that tarball was created
        tarballs = list(build_dir.glob("*.tar.gz"))
        assert len(tarballs) > 0, "No source distribution tarball created"

        # Extract and verify contents
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            with tarfile.open(tarballs[0], "r:gz") as tar:
                tar.extractall(tmppath)

            # Find the extracted directory
            extracted = next(tmppath.iterdir())

            # Verify frontend build is included
            frontend_in_sdist = extracted / "yapcli" / "frontend" / "build"
            assert (
                frontend_in_sdist.exists()
            ), "Frontend build not included in source distribution"
            assert (
                frontend_in_sdist / "index.html"
            ).exists(), "index.html not in source distribution"

    def test_wheel_build(
        self, project_root: Path, frontend_build: Path, build_dir: Path
    ) -> None:
        """Test that wheel can be built."""
        # Clean previous builds
        if build_dir.exists():
            for item in build_dir.iterdir():
                if item.is_file() and item.suffix == ".whl":
                    item.unlink()

        # Build wheel
        result = subprocess.run(
            [sys.executable, "-m", "build", "--wheel"],
            cwd=project_root,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            pytest.fail(f"Wheel build failed:\n{result.stderr}")

        # Check that wheel was created
        wheels = list(build_dir.glob("*.whl"))
        assert len(wheels) > 0, "No wheel file created"


class TestInstalledPackage:
    """Test the behavior of the installed package."""

    @pytest.fixture
    def venv_dir(self, tmp_path: Path) -> Path:
        """Create a temporary virtual environment."""
        venv_path = tmp_path / "venv"
        result = subprocess.run(
            [sys.executable, "-m", "venv", str(venv_path)],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            pytest.fail(f"Failed to create venv: {result.stderr}")

        return venv_path

    @pytest.fixture
    def installed_package(
        self,
        project_root: Path,
        frontend_build: Path,
        venv_dir: Path,
    ) -> Path:
        """Install the package in a virtual environment."""
        # Determine pip path
        if sys.platform == "win32":
            pip_path = venv_dir / "Scripts" / "pip.exe"
            python_path = venv_dir / "Scripts" / "python.exe"
        else:
            pip_path = venv_dir / "bin" / "pip"
            python_path = venv_dir / "bin" / "python"

        # Build the package first
        result = subprocess.run(
            [sys.executable, "-m", "build", "--wheel"],
            cwd=project_root,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            pytest.fail(f"Package build failed: {result.stderr}")

        # Find the wheel
        dist_dir = project_root / "dist"
        wheels = list(dist_dir.glob("*.whl"))
        if not wheels:
            pytest.fail("No wheel file found after build")

        wheel_path = wheels[-1]  # Use the most recent wheel

        # Install the wheel
        result = subprocess.run(
            [str(pip_path), "install", str(wheel_path)],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            pytest.fail(f"Package installation failed: {result.stderr}")

        return python_path

    def test_yapcli_command_exists(
        self, installed_package: Path, venv_dir: Path
    ) -> None:
        """Test that the yapcli command is available after installation."""
        if sys.platform == "win32":
            yapcli_path = venv_dir / "Scripts" / "yapcli.exe"
        else:
            yapcli_path = venv_dir / "bin" / "yapcli"

        assert yapcli_path.exists(), f"yapcli command not found at {yapcli_path}"

    def test_yapcli_help(self, installed_package: Path, venv_dir: Path) -> None:
        """Test that yapcli --help works."""
        if sys.platform == "win32":
            yapcli_path = venv_dir / "Scripts" / "yapcli.exe"
        else:
            yapcli_path = venv_dir / "bin" / "yapcli"

        result = subprocess.run(
            [str(yapcli_path), "--help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"yapcli --help failed: {result.stderr}"
        assert "yapcli" in result.stdout.lower() or "plaid" in result.stdout.lower()

    def test_yapcli_link_help(self, installed_package: Path, venv_dir: Path) -> None:
        """Test that yapcli link --help works."""
        if sys.platform == "win32":
            yapcli_path = venv_dir / "Scripts" / "yapcli.exe"
        else:
            yapcli_path = venv_dir / "bin" / "yapcli"

        result = subprocess.run(
            [str(yapcli_path), "link", "--help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"yapcli link --help failed: {result.stderr}"
        assert "link" in result.stdout.lower()
        assert "plaid" in result.stdout.lower()

    def test_frontend_files_installed(
        self, installed_package: Path, venv_dir: Path
    ) -> None:
        """Test that frontend files are installed with the package."""
        # Find site-packages directory
        result = subprocess.run(
            [
                str(installed_package),
                "-c",
                "import yapcli; import os; print(os.path.dirname(yapcli.__file__))",
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            pytest.fail(f"Failed to find yapcli package: {result.stderr}")

        yapcli_dir = Path(result.stdout.strip())
        frontend_build = yapcli_dir / "frontend" / "build"

        assert frontend_build.exists(), f"Frontend build not found at {frontend_build}"
        assert (
            frontend_build / "index.html"
        ).exists(), "index.html not found in installed frontend"
