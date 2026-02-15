from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from typing import Optional, Tuple

import typer
from rich.console import Console

console = Console()
app = typer.Typer(help="Run Plaid Link locally and capture the resulting tokens.")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = PROJECT_ROOT / "frontend"
DEFAULT_SECRETS_DIR = PROJECT_ROOT / "secrets"
DEFAULT_BACKEND_PORT = 8000
DEFAULT_FRONTEND_PORT = 3000
POLL_INTERVAL_SECONDS = 2.0


def start_backend(port: int, secrets_dir: Path) -> subprocess.Popen:
    env = os.environ.copy()
    env["PORT"] = str(port)
    env["PLAID_SECRETS_DIR"] = str(secrets_dir)
    return subprocess.Popen(
        [sys.executable, "-m", "yapcli.server"],
        cwd=PROJECT_ROOT,
        env=env,
        start_new_session=True,
    )


def start_frontend(port: int, serve_build: bool) -> subprocess.Popen:
    env = os.environ.copy()
    env["PORT"] = str(port)
    if serve_build:
        build_dir = FRONTEND_DIR / "build"
        if not build_dir.exists():
            console.print("[yellow]No build found. Running npm run build...[/]")
            subprocess.run(["npm", "run", "build"], cwd=FRONTEND_DIR, env=env, check=True)
        cmd = [sys.executable, "-m", "http.server", str(port), "--directory", "build"]
    else:
        cmd = ["npm", "start"]

    return subprocess.Popen(
        cmd,
        cwd=FRONTEND_DIR,
        env=env,
        start_new_session=True,
    )


def terminate_process(proc: Optional[subprocess.Popen]) -> None:
    if proc is None:
        return

    if proc.poll() is not None:
        return

    try:
        if hasattr(os, "killpg"):
            os.killpg(proc.pid, signal.SIGTERM)
        else:
            proc.terminate()
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        if hasattr(os, "killpg"):
            os.killpg(proc.pid, signal.SIGKILL)
        else:
            proc.kill()
    except ProcessLookupError:
        return


def discover_credentials(secrets_dir: Path, started_at: float) -> Optional[Tuple[str, str, str]]:
    access_files = secrets_dir.glob("*_access_token")
    for access_file in access_files:
        identifier = access_file.name[: -len("_access_token")]
        item_file = secrets_dir / f"{identifier}_item_id"
        if not item_file.exists():
            continue

        access_updated = access_file.stat().st_mtime
        item_updated = item_file.stat().st_mtime
        if access_updated < started_at or item_updated < started_at:
            continue

        item_id = item_file.read_text().strip()
        access_token = access_file.read_text().strip()
        return identifier, item_id, access_token

    return None


def wait_for_credentials(
    *,
    secrets_dir: Path,
    started_at: float,
    timeout: int,
    backend_proc: Optional[subprocess.Popen],
    frontend_proc: Optional[subprocess.Popen],
) -> Tuple[str, str, str]:
    deadline = started_at + timeout
    secrets_dir.mkdir(parents=True, exist_ok=True)

    while time.time() < deadline:
        credentials = discover_credentials(secrets_dir, started_at)
        if credentials:
            return credentials

        if backend_proc and backend_proc.poll() is not None:
            raise RuntimeError("Flask backend terminated before credentials were captured.")

        if frontend_proc and frontend_proc.poll() is not None:
            raise RuntimeError("Frontend server terminated before Plaid Link completed.")

        time.sleep(POLL_INTERVAL_SECONDS)

    raise TimeoutError


@app.command()
def link(  # pragma: no cover - requires Plaid and npm services
    backend_port: int = typer.Option(
        DEFAULT_BACKEND_PORT,
        "--backend-port",
        help="Port for the Flask backend.",
        show_default=True,
    ),
    frontend_port: int = typer.Option(
        DEFAULT_FRONTEND_PORT,
        "--frontend-port",
        help="Port for the React frontend.",
        show_default=True,
    ),
    serve_build: bool = typer.Option(
        False,
        "--serve-build",
        help="Serve the built frontend instead of running the dev server.",
    ),
    secrets_dir: Optional[Path] = typer.Option(
        None,
        "--secrets-dir",
        help="Directory where the backend writes item_id/access_token files.",
    ),
    timeout: int = typer.Option(
        300,
        "--timeout",
        help="Seconds to wait for Plaid Link to complete before timing out.",
        show_default=True,
    ),
    open_browser: bool = typer.Option(
        True,
        "--open-browser/--no-open-browser",
        help="Automatically open the frontend in your browser.",
        show_default=True,
    ),
) -> None:
    start_time = time.time()
    secrets_path = secrets_dir or DEFAULT_SECRETS_DIR

    backend_proc: Optional[subprocess.Popen] = None
    frontend_proc: Optional[subprocess.Popen] = None

    try:
        console.print("[cyan]Starting Flask backend...[/]")
        backend_proc = start_backend(backend_port, secrets_path)
        console.print(f"[green]Backend running[/] on http://127.0.0.1:{backend_port}/api")

        console.print("[cyan]Starting frontend...[/]")
        frontend_proc = start_frontend(frontend_port, serve_build)
        console.print(
            f"[green]Frontend running[/] on http://127.0.0.1:{frontend_port}/"
        )

        frontend_url = f"http://127.0.0.1:{frontend_port}/"
        if open_browser:
            webbrowser.open(frontend_url)
            console.print(f"Opened browser to {frontend_url}")
        else:
            console.print(f"Open your browser to {frontend_url} to finish Plaid Link.")

        console.print("Waiting for Plaid Link to complete and tokens to be written...")
        identifier, item_id, access_token = wait_for_credentials(
            secrets_dir=secrets_path,
            started_at=start_time,
            timeout=timeout,
            backend_proc=backend_proc,
            frontend_proc=frontend_proc,
        )

        console.print("[green]Plaid Link completed.[/]")
        console.print(f"Institution or item key: [bold]{identifier}[/]")
        console.print(f"item_id: [cyan]{item_id}[/]")
        console.print(f"access_token: [cyan]{access_token}[/]")
    except subprocess.CalledProcessError as exc:
        console.print(f"[red]Command failed[/]: {exc}")
        raise typer.Exit(code=1)
    except TimeoutError:
        console.print(
            f"[red]Timed out[/] waiting for Plaid Link after {timeout} seconds."
        )
        raise typer.Exit(code=1)
    except RuntimeError as exc:
        console.print(f"[red]{exc}")
        raise typer.Exit(code=1)
    finally:
        terminate_process(frontend_proc)
        terminate_process(backend_proc)
