#!/usr/bin/env python3
"""Build the React frontend and copy it to the package directory."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
from enum import Enum
from pathlib import Path

import typer


class InstallMode(str, Enum):
    auto = "auto"
    ci = "ci"
    install = "install"


def _running_in_ci() -> bool:
    return os.getenv("CI") == "true" or os.getenv("CI_RUNNER_ID") is not None


def _resolve_install_mode(mode: InstallMode) -> InstallMode:
    if mode == InstallMode.auto:
        return InstallMode.ci if _running_in_ci() else InstallMode.install
    return mode


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_frontend(*, install_mode: InstallMode, check_lock: bool) -> None:
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

    package_lock = frontend_src / "package-lock.json"
    resolved_install_mode = _resolve_install_mode(install_mode)

    if resolved_install_mode == InstallMode.ci and not package_lock.exists():
        typer.echo(
            "Error: --install-mode=ci requires frontend/package-lock.json",
            err=True,
        )
        raise typer.Exit(1)

    npm_install_cmd = (
        ["npm", "ci"] if resolved_install_mode == InstallMode.ci else ["npm", "install"]
    )

    npm_env = {
        **os.environ,
        "NPM_CONFIG_AUDIT": "false",
        "NPM_CONFIG_FUND": "false",
    }

    lock_hash_before: str | None = None
    if check_lock and package_lock.exists():
        lock_hash_before = _sha256(package_lock)

    typer.echo("Installing frontend dependencies...")
    result = subprocess.run(
        npm_install_cmd,
        cwd=frontend_src,
        env=npm_env,
    )

    if result.returncode != 0:
        typer.echo("Error installing dependencies", err=True)
        raise typer.Exit(1)

    typer.echo("\nBuilding React frontend...")
    result = subprocess.run(
        ["npm", "run", "build"],
        cwd=frontend_src,
        env=npm_env,
    )

    if result.returncode != 0:
        typer.echo("Error building frontend", err=True)
        raise typer.Exit(1)

    if lock_hash_before is not None:
        lock_hash_after = _sha256(package_lock)
        if lock_hash_after != lock_hash_before:
            typer.echo(
                "Error: package-lock.json changed during frontend build.",
                err=True,
            )
            typer.echo(
                "Tip: Run with --install-mode=ci to require reproducible installs.",
                err=True,
            )
            raise typer.Exit(1)

    build_src = frontend_src / "build"
    build_dst = frontend_dst / "build"

    if not build_src.exists():
        typer.echo(f"Error: Build output not found: {build_src}", err=True)
        raise typer.Exit(1)

    # Remove existing build if present
    if build_dst.exists():
        typer.echo(f"\nRemoving existing build at {build_dst}")
        shutil.rmtree(build_dst)

    # Create parent directory
    frontend_dst.mkdir(parents=True, exist_ok=True)

    # Copy build to package directory
    typer.echo(f"Copying build from {build_src} to {build_dst}")
    shutil.copytree(build_src, build_dst)

    typer.echo("\n✓ Frontend built and copied successfully")


def clean_frontend(project_root: Path) -> None:
    frontend_src = project_root / "frontend"
    frontend_dst = project_root / "yapcli" / "frontend"

    targets = [
        frontend_src / "build",
        frontend_src / "node_modules",
        frontend_dst / "build",
    ]

    for target in targets:
        if not target.exists():
            typer.echo(f"Skipping (not found): {target}")
            continue

        typer.echo(f"Removing: {target}")
        shutil.rmtree(target)


app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.command("build")
def build_command(
    install_mode: InstallMode = typer.Option(
        InstallMode.auto,
        "--install-mode",
        help="How to install frontend deps: auto (CI→ci else install), ci, or install.",
        case_sensitive=False,
    ),
    check_lock: bool | None = typer.Option(
        None,
        "--check-lock/--no-check-lock",
        help="Fail if frontend/package-lock.json changes during the run (defaults to on for ci, off otherwise).",
    ),
) -> None:
    resolved_install_mode = _resolve_install_mode(install_mode)
    resolved_check_lock = check_lock
    if resolved_check_lock is None:
        resolved_check_lock = resolved_install_mode == InstallMode.ci

    build_frontend(install_mode=install_mode, check_lock=resolved_check_lock)


@app.command("clean")
def clean_command() -> None:
    """Delete build artifacts (including node_modules)."""
    project_root = Path(__file__).parent.parent
    clean_frontend(project_root)


if __name__ == "__main__":
    app()
