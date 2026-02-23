#!/usr/bin/env python3
"""
Prepare the package for distribution.

This script:
1. Builds the React frontend
2. Builds the Python package (sdist and wheel)
3. Validates the package contents
4. Optionally uploads to PyPI
"""

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer


def run_command(
    cmd: list[str], cwd: Path | None = None, check: bool = True
) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)

    if check and result.returncode != 0:
        print(
            f"Error: Command failed with exit code {result.returncode}", file=sys.stderr
        )
        print(f"stdout: {result.stdout}", file=sys.stderr)
        print(f"stderr: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    return result


def clean_build_dirs(project_root: Path) -> None:
    """Clean previous build directories."""
    print("\n📦 Cleaning previous builds...")

    dist_dir = project_root / "dist"
    if dist_dir.exists():
        print(f"Removing {dist_dir}")
        shutil.rmtree(dist_dir)

    build_dir = project_root / "build"
    if build_dir.exists():
        print(f"Removing {build_dir}")
        shutil.rmtree(build_dir)

    # Clean egg-info directories
    for egg_info in project_root.glob("*.egg-info"):
        print(f"Removing {egg_info}")
        shutil.rmtree(egg_info)


def build_frontend(
    project_root: Path,
    *,
    frontend_install_mode: str,
    frontend_check_lock: Optional[bool],
) -> None:
    """Build the React frontend."""
    print("\n🎨 Building React frontend...")
    build_script = project_root / "scripts" / "build_frontend.py"

    cmd = [
        sys.executable,
        str(build_script),
        "build",
        "--install-mode",
        frontend_install_mode,
    ]
    if frontend_check_lock is True:
        cmd.append("--check-lock")
    elif frontend_check_lock is False:
        cmd.append("--no-check-lock")

    run_command(cmd, cwd=project_root)

    # Verify build output
    frontend_build = project_root / "yapcli" / "frontend" / "build"
    if not frontend_build.exists():
        print("Error: Frontend build directory not created", file=sys.stderr)
        sys.exit(1)

    if not (frontend_build / "index.html").exists():
        print("Error: index.html not found in frontend build", file=sys.stderr)
        sys.exit(1)

    print("✓ Frontend built successfully")


def build_package(project_root: Path) -> None:
    """Build the Python package."""
    print("\n📦 Building Python package...")
    run_command([sys.executable, "-m", "build"], cwd=project_root)

    dist_dir = project_root / "dist"
    if not dist_dir.exists() or not list(dist_dir.glob("*")):
        print("Error: No distribution files created", file=sys.stderr)
        sys.exit(1)

    print("\n✓ Package built successfully:")
    for item in dist_dir.iterdir():
        print(f"  - {item.name}")


def validate_package(project_root: Path) -> None:
    """Validate the built package."""
    print("\n✅ Validating package...")

    dist_dir = project_root / "dist"

    # Check with twine
    run_command(
        [sys.executable, "-m", "twine", "check", str(dist_dir / "*")], cwd=project_root
    )

    # Check that frontend is included in tarball
    tarballs = list(dist_dir.glob("*.tar.gz"))
    if tarballs:
        result = run_command(
            ["tar", "-tzf", str(tarballs[0])], cwd=project_root, check=False
        )
        if "frontend/build" not in result.stdout:
            print(
                "Warning: Frontend build may not be included in source distribution",
                file=sys.stderr,
            )
        else:
            print("✓ Frontend build found in source distribution")

    print("✓ Package validation passed")


def upload_to_pypi(project_root: Path, test: bool = True) -> None:
    """Upload the package to PyPI."""
    dist_dir = project_root / "dist"

    if test:
        print("\n📤 Uploading to Test PyPI...")
        repository = "testpypi"
    else:
        print("\n📤 Uploading to PyPI...")
        repository = "pypi"

    if not typer.confirm(f"Upload to {repository}?"):
        typer.echo("Upload cancelled")
        return

    cmd = [sys.executable, "-m", "twine", "upload"]
    if test:
        cmd.extend(["--repository", "testpypi"])
    cmd.append(f"{dist_dir}/*")

    run_command(cmd, cwd=project_root)
    print(f"✓ Uploaded to {repository}")


def main(
    clean: bool = typer.Option(False, "--clean", help="Clean previous builds."),
    no_frontend: bool = typer.Option(
        False, "--no-frontend", help="Skip frontend build."
    ),
    upload: bool = typer.Option(False, "--upload", help="Upload to PyPI."),
    test_pypi: bool = typer.Option(
        False, "--test-pypi", help="Upload to Test PyPI instead."
    ),
    frontend_install_mode: str = typer.Option(
        "ci",
        "--frontend-install-mode",
        help="Forwarded to scripts/build_frontend.py --install-mode (auto|ci|install).",
    ),
    frontend_check_lock: Optional[bool] = typer.Option(
        None,
        "--frontend-check-lock/--frontend-no-check-lock",
        help="Forwarded to scripts/build_frontend.py --check-lock/--no-check-lock.",
    ),
) -> None:
    project_root = Path(__file__).parent.parent

    if upload and test_pypi:
        raise typer.BadParameter("Pass only one of --upload or --test-pypi")

    typer.echo("=" * 60)
    typer.echo("yapcli Package Distribution Preparation")
    typer.echo("=" * 60)

    if clean:
        clean_build_dirs(project_root)

    if not no_frontend:
        if frontend_install_mode not in {"auto", "ci", "install"}:
            raise typer.BadParameter(
                "Must be one of: auto, ci, install",
                param_hint="--frontend-install-mode",
            )
        build_frontend(
            project_root,
            frontend_install_mode=frontend_install_mode,
            frontend_check_lock=frontend_check_lock,
        )

    build_package(project_root)
    validate_package(project_root)

    if upload or test_pypi:
        upload_to_pypi(project_root, test=test_pypi)

    typer.echo("\n" + "=" * 60)
    typer.echo("✅ Package preparation complete!")
    typer.echo("=" * 60)

    if not upload and not test_pypi:
        typer.echo("\nTo upload to PyPI:")
        typer.echo("  python scripts/prepare_package.py --upload")
        typer.echo("\nTo upload to Test PyPI:")
        typer.echo("  python scripts/prepare_package.py --test-pypi")


if __name__ == "__main__":
    typer.run(main)
