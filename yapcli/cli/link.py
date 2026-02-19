from __future__ import annotations

import datetime as dt
import os
import signal
import subprocess
import sys
import time
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Optional, Tuple

import typer
from loguru import logger
from rich.console import Console

from yapcli.logging import build_log_path
from yapcli.secrets import default_secrets_dir
from yapcli.utils import default_log_dir

console = Console()
app = typer.Typer(help="Run Plaid Link locally and capture the resulting tokens.")


def _get_frontend_dir() -> Path:
    """Get the frontend directory, handling both dev and installed scenarios."""
    # First try package-relative path (for installed package)
    yapcli_package_dir = Path(__file__).resolve().parent.parent
    packaged_frontend = yapcli_package_dir / "frontend" / "build"

    if packaged_frontend.exists():
        return packaged_frontend.parent

    # Fall back to project root (for development)
    project_root = yapcli_package_dir.parent
    dev_frontend = project_root / "frontend"

    if dev_frontend.exists():
        return dev_frontend

    # No frontend found
    raise FileNotFoundError(
        "Frontend directory not found. "
        "Please ensure the package is properly built with the frontend included, "
        "or run from the development directory."
    )


FRONTEND_DIR = _get_frontend_dir()
LOG_DIR = default_log_dir()
DEFAULT_BACKEND_PORT = 8000
DEFAULT_FRONTEND_PORT = 3000
POLL_INTERVAL_SECONDS = 2.0
STARTED_AT_TOLERANCE_SECONDS = 1.0


@dataclass
class ManagedProcess:
    process: subprocess.Popen
    log_handle: IO[str]


def start_backend(
    port: int,
    secrets_dir: Path,
    log_path: Path,
    *,
    products: Optional[str] = None,
) -> ManagedProcess:
    env = os.environ.copy()
    env["PORT"] = str(port)
    env["PLAID_SECRETS_DIR"] = str(secrets_dir)
    if products is not None and products.strip() != "":
        env["PLAID_PRODUCTS"] = products

    log_file = log_path.open("w")
    try:
        process = subprocess.Popen(
            [sys.executable, "-m", "yapcli", "serve", "--port", str(port)],
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        logger.info(
            "Started backend (pid={}, port={}, secrets_dir={}) log -> {}",
            process.pid,
            port,
            secrets_dir,
            log_path,
        )
        return ManagedProcess(process=process, log_handle=log_file)
    except Exception:
        log_file.close()
        logger.exception("Failed to start backend process")
        raise


def start_frontend(port: int, serve_build: bool, log_path: Path) -> ManagedProcess:
    env = os.environ.copy()
    env["PORT"] = str(port)
    log_file = log_path.open("w")

    try:
        if serve_build:
            build_dir = FRONTEND_DIR / "build"
            if not build_dir.exists():
                console.print("[yellow]No build found. Running npm run build...[/]")
                logger.info("No frontend build found. Building before serve...")
                subprocess.run(
                    ["npm", "run", "build"],
                    cwd=FRONTEND_DIR,
                    env=env,
                    check=True,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                )
            cmd = [
                sys.executable,
                "-m",
                "http.server",
                str(port),
                "--directory",
                "build",
            ]
        else:
            cmd = ["npm", "start"]

        process = subprocess.Popen(
            cmd,
            cwd=FRONTEND_DIR,
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        logger.info(
            "Started frontend (pid={}, port={}, serve_build={}) log -> {}",
            process.pid,
            port,
            serve_build,
            log_path,
        )
        return ManagedProcess(process=process, log_handle=log_file)
    except Exception:
        log_file.close()
        logger.exception("Failed to start frontend process")
        raise


def terminate_process(proc: Optional[ManagedProcess]) -> None:
    if proc is None:
        return

    process = proc.process

    if process.poll() is not None:
        proc.log_handle.close()
        return

    try:
        # Only signal the process group when the child is its group leader
        # (i.e., created with start_new_session=True). Otherwise terminate just the process.
        if hasattr(os, "killpg") and hasattr(os, "getpgid"):
            try:
                if os.getpgid(process.pid) == process.pid:
                    os.killpg(process.pid, signal.SIGTERM)
                else:
                    process.terminate()
            except ProcessLookupError:
                process.terminate()
        else:
            process.terminate()
        process.wait(timeout=10)
        logger.info("Terminated process pid={}", process.pid)
    except subprocess.TimeoutExpired:
        if hasattr(os, "killpg"):
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
        logger.warning("Force killed process pid={} after timeout", process.pid)
    except ProcessLookupError:
        logger.warning("Process pid={} was already gone", process.pid)
    finally:
        proc.log_handle.close()


def discover_credentials(
    secrets_dir: Path, started_at: float
) -> Optional[Tuple[str, str, str]]:
    best: Optional[Tuple[str, str, str]] = None
    best_updated = -1.0

    for access_file in secrets_dir.glob("*_access_token"):
        identifier = access_file.name[: -len("_access_token")]
        item_file = secrets_dir / f"{identifier}_item_id"
        if not item_file.exists():
            continue

        try:
            access_updated = access_file.stat().st_mtime
            item_updated = item_file.stat().st_mtime
        except FileNotFoundError:
            continue

        # Some filesystems have coarse mtime resolution (e.g. 1s). If we compare
        # strictly against a high-resolution started_at, we can miss files that
        # were written shortly after started_at but recorded with an earlier-
        # rounded mtime.
        cutoff = started_at - STARTED_AT_TOLERANCE_SECONDS
        if access_updated < cutoff or item_updated < cutoff:
            continue

        updated = max(access_updated, item_updated)
        if updated >= best_updated:
            item_id = item_file.read_text().strip()
            access_token = access_file.read_text().strip()
            best = (identifier, item_id, access_token)
            best_updated = updated

    return best


def wait_for_credentials(
    *,
    secrets_dir: Path,
    started_at: float,
    timeout: int,
    backend_proc: Optional[ManagedProcess],
    frontend_proc: Optional[ManagedProcess],
) -> Tuple[str, str, str]:
    deadline = started_at + timeout
    secrets_dir.mkdir(parents=True, exist_ok=True)

    while time.time() < deadline:
        credentials = discover_credentials(secrets_dir, started_at)
        if credentials:
            return credentials

        if backend_proc and backend_proc.process.poll() is not None:
            raise RuntimeError(
                "Flask backend terminated before credentials were captured."
            )

        if frontend_proc and frontend_proc.process.poll() is not None:
            raise RuntimeError(
                "Frontend server terminated before Plaid Link completed."
            )

        remaining = deadline - time.time()
        if remaining <= 0:
            break
        time.sleep(min(POLL_INTERVAL_SECONDS, remaining))

    raise TimeoutError


@app.command()
def link(
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
    products: Optional[str] = typer.Option(
        None,
        "--products",
        help=(
            "Comma-separated Plaid products to request during Link."
            "Defaults to PLAID_PRODUCTS env var or 'transactions' if not set. "
            "Example: --products=transactions,investments"
        ),
    ),
) -> None:
    """
    Launch Plaid Link locally and wait for user to complete the flow returning an item_id and access_token.
    """
    started_at = time.time()
    started_dt = dt.datetime.fromtimestamp(started_at)
    # Logging is configured once in the main Typer app callback.

    secrets_path = secrets_dir or default_secrets_dir()
    backend_log_path = build_log_path(
        log_dir=LOG_DIR,
        prefix="backend",
        started_at=started_dt,
    )
    frontend_log_path = build_log_path(
        log_dir=LOG_DIR,
        prefix="frontend",
        started_at=started_dt,
    )

    backend_proc: Optional[ManagedProcess] = None
    frontend_proc: Optional[ManagedProcess] = None

    try:
        logger.info(
            "Launching Plaid Link (backend_port={}, frontend_port={}, serve_build={}, secrets_dir={})",
            backend_port,
            frontend_port,
            serve_build,
            secrets_path,
        )
        console.print("[cyan]Starting Flask backend...[/]")
        backend_proc = start_backend(
            backend_port,
            secrets_path,
            backend_log_path,
            products=products,
        )
        console.print(
            f"[green]Backend running[/] on http://127.0.0.1:{backend_port}/api (log: {backend_log_path})"
        )

        console.print("[cyan]Starting frontend...[/]")
        frontend_proc = start_frontend(frontend_port, serve_build, frontend_log_path)
        console.print(
            f"[green]Frontend running[/] on http://127.0.0.1:{frontend_port}/ (log: {frontend_log_path})"
        )

        frontend_url = f"http://127.0.0.1:{frontend_port}/"
        if open_browser:
            webbrowser.open(frontend_url)
            console.print(f"Opened browser to {frontend_url}")
            logger.info("Opened browser to {}", frontend_url)
        else:
            console.print(f"Open your browser to {frontend_url} to finish Plaid Link.")
            logger.info(
                "Browser not opened automatically. Navigate to {}", frontend_url
            )

        console.print("Waiting for Plaid Link to complete and tokens to be written...")
        logger.info("Waiting for credentials to appear in {}", secrets_path)
        identifier, item_id, access_token = wait_for_credentials(
            secrets_dir=secrets_path,
            started_at=started_at,
            timeout=timeout,
            backend_proc=backend_proc,
            frontend_proc=frontend_proc,
        )

        console.print("[green]Plaid Link completed.[/]")
        console.print(f"Institution or item key: [bold]{identifier}[/]")
        console.print(f"item_id: [cyan]{item_id}[/]")
        console.print(f"access_token: [cyan]{access_token}[/]")
        logger.info(
            "Plaid Link completed. identifier={} item_id={} access_token_saved",
            identifier,
            item_id,
        )
    except subprocess.CalledProcessError as exc:
        console.print(f"[red]Command failed[/]: {exc}")
        logger.exception("Command failed during Plaid Link execution")
        raise typer.Exit(code=1)
    except TimeoutError:
        console.print(
            f"[red]Timed out[/] waiting for Plaid Link after {timeout} seconds."
        )
        logger.error("Timed out waiting for Plaid Link after {} seconds", timeout)
        raise typer.Exit(code=1)
    except RuntimeError as exc:
        console.print(f"[red]{exc}")
        logger.error("Runtime error while waiting for Plaid Link: {}", exc)
        raise typer.Exit(code=1)
    finally:
        terminate_process(frontend_proc)
        terminate_process(backend_proc)
        logger.info("Stopped link subprocesses")
