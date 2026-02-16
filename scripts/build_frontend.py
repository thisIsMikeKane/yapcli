#!/usr/bin/env python3
"""Build the React frontend and copy it to the package directory."""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def build_frontend() -> None:
    """Build the React frontend and copy to package directory."""
    project_root = Path(__file__).parent.parent
    frontend_src = project_root / "frontend"
    frontend_dst = project_root / "yapcli" / "frontend"

    if not frontend_src.exists():
        print(
            f"Error: Frontend source directory not found: {frontend_src}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Detect if running in CI (GitHub Actions, GitLab CI, etc.)
    ci_mode = os.getenv("CI") == "true" or os.getenv("CI_RUNNER_ID") is not None

    # Use npm ci for reproducible builds in CI, npm install for development
    npm_install_cmd = ["npm", "ci", "--yes"] if ci_mode else ["npm", "install"]

    print("Installing frontend dependencies...")
    result = subprocess.run(
        npm_install_cmd,
        cwd=frontend_src,
    )

    if result.returncode != 0:
        print("Error installing dependencies", file=sys.stderr)
        sys.exit(1)

    print("\nBuilding React frontend...")
    result = subprocess.run(
        ["npm", "run", "build"],
        cwd=frontend_src,
    )

    if result.returncode != 0:
        print("Error building frontend", file=sys.stderr)
        sys.exit(1)

    build_src = frontend_src / "build"
    build_dst = frontend_dst / "build"

    if not build_src.exists():
        print(f"Error: Build output not found: {build_src}", file=sys.stderr)
        sys.exit(1)

    # Remove existing build if present
    if build_dst.exists():
        print(f"\nRemoving existing build at {build_dst}")
        shutil.rmtree(build_dst)

    # Create parent directory
    frontend_dst.mkdir(parents=True, exist_ok=True)

    # Copy build to package directory
    print(f"Copying build from {build_src} to {build_dst}")
    shutil.copytree(build_src, build_dst)

    print("\n✓ Frontend built and copied successfully")


if __name__ == "__main__":
    build_frontend()
