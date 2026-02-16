#!/usr/bin/env python3
"""
Prepare the package for distribution.

This script:
1. Builds the React frontend
2. Builds the Python package (sdist and wheel)
3. Validates the package contents
4. Optionally uploads to PyPI
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    
    if check and result.returncode != 0:
        print(f"Error: Command failed with exit code {result.returncode}", file=sys.stderr)
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


def build_frontend(project_root: Path) -> None:
    """Build the React frontend."""
    print("\n🎨 Building React frontend...")
    build_script = project_root / "scripts" / "build_frontend.py"
    run_command([sys.executable, str(build_script)], cwd=project_root)
    
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
    run_command([sys.executable, "-m", "twine", "check", str(dist_dir / "*")], cwd=project_root)
    
    # Check that frontend is included in tarball
    tarballs = list(dist_dir.glob("*.tar.gz"))
    if tarballs:
        result = run_command(
            ["tar", "-tzf", str(tarballs[0])],
            cwd=project_root,
            check=False
        )
        if "frontend/build" not in result.stdout:
            print("Warning: Frontend build may not be included in source distribution", file=sys.stderr)
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
    
    confirm = input(f"Upload to {repository}? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("Upload cancelled")
        return
    
    cmd = [sys.executable, "-m", "twine", "upload"]
    if test:
        cmd.extend(["--repository", "testpypi"])
    cmd.append(f"{dist_dir}/*")
    
    run_command(cmd, cwd=project_root)
    print(f"✓ Uploaded to {repository}")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Prepare yapcli package for distribution")
    parser.add_argument("--clean", action="store_true", help="Clean previous builds")
    parser.add_argument("--no-frontend", action="store_true", help="Skip frontend build")
    parser.add_argument("--upload", action="store_true", help="Upload to PyPI")
    parser.add_argument("--test-pypi", action="store_true", help="Upload to Test PyPI instead")
    args = parser.parse_args()
    
    project_root = Path(__file__).parent.parent
    
    print("=" * 60)
    print("yapcli Package Distribution Preparation")
    print("=" * 60)
    
    if args.clean:
        clean_build_dirs(project_root)
    
    if not args.no_frontend:
        build_frontend(project_root)
    
    build_package(project_root)
    validate_package(project_root)
    
    if args.upload or args.test_pypi:
        upload_to_pypi(project_root, test=args.test_pypi)
    
    print("\n" + "=" * 60)
    print("✅ Package preparation complete!")
    print("=" * 60)
    
    if not args.upload and not args.test_pypi:
        print("\nTo upload to PyPI:")
        print("  python scripts/prepare_package.py --upload")
        print("\nTo upload to Test PyPI:")
        print("  python scripts/prepare_package.py --test-pypi")


if __name__ == "__main__":
    main()
