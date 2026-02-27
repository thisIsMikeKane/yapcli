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

from yapcli.institutions import discover_institutions, prompt_for_institutions
from yapcli.logging import build_log_path
from yapcli.utils import default_log_dir, default_secrets_dir

console = Console()
app = typer.Typer(help="Run Plaid Link locally and capture the resulting tokens.")


def _get_frontend_dir() -> Path:
    """Get the packaged frontend directory containing bundled build assets."""
    yapcli_package_dir = Path(__file__).resolve().parent.parent

    # Otherwise try package-relative path (installed package)
    packaged_frontend = yapcli_package_dir / "frontend" / "build"

    if packaged_frontend.exists():
        return packaged_frontend.parent

    # No frontend found
    raise FileNotFoundError(
        "Packaged frontend build not found at 'yapcli/frontend/build'. "
        "Please ensure the package is built with frontend assets included."
    )


DEFAULT_BACKEND_PORT = 8000
DEFAULT_FRONTEND_PORT = 3000
POLL_INTERVAL_SECONDS = 2.0
STARTED_AT_TOLERANCE_SECONDS = 1.0
_ALLOWED_PRODUCTS = {"transactions", "investments"}


def _validate_products(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None

    raw = value.strip()
    if raw == "":
        return None

    parts = [p.strip().lower() for p in raw.split(",")]
    parts = [p for p in parts if p]
    if not parts:
        return None

    invalid = sorted({p for p in parts if p not in _ALLOWED_PRODUCTS})
    if invalid:
        allowed = ", ".join(sorted(_ALLOWED_PRODUCTS))
        bad = ", ".join(invalid)
        raise typer.BadParameter(
            f"Invalid --products value(s): {bad}. Allowed values: {allowed}"
        )

    return ",".join(parts)


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
    days_requested: int = 365,
) -> ManagedProcess:
    env = os.environ.copy()
    env["PORT"] = str(port)
    env["PLAID_SECRETS_DIR"] = str(secrets_dir)
    env["YAPCLI_DAYS_REQUESTED"] = str(days_requested)

    log_file = log_path.open("w")
    try:
        cmd = [sys.executable, "-m", "yapcli", "serve", "--port", str(port)]
        if products is not None and products.strip() != "":
            cmd.extend(["--products", products])
        process = subprocess.Popen(
            cmd,
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


def start_frontend(
    port: int,
    log_path: Path,
    *,
    frontend_dir: Path,
    backend_port: int,
) -> ManagedProcess:
    index_html = frontend_dir / "build" / "index.html"
    logger.info(
        "Serving frontend build from yapcli/frontend/build/index.html ({})",
        index_html,
    )
    if not index_html.exists():
        logger.error("Packaged frontend index.html is missing: {}", index_html)
        logger.error(
            "This installation is missing bundled frontend assets. Reinstall or rebuild the package.",
        )
        console.print("[red]Packaged frontend build is missing.[/]")
        console.print("Expected file: yapcli/frontend/build/index.html")
        raise typer.Exit(1)

    env = os.environ.copy()
    log_file = log_path.open("w")
    try:
        cmd = [
            sys.executable,
            "-m",
            "yapcli.frontend_proxy",
            "--port",
            str(port),
            "--backend-port",
            str(backend_port),
            "--build-dir",
            str(frontend_dir / "build"),
        ]
        process = subprocess.Popen(
            cmd,
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        logger.info(
            "Started frontend (pid={}, port={}, backend_port={}) log -> {}",
            process.pid,
            port,
            backend_port,
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


def _clear_institution_secrets(*, secrets_dir: Path, institution_id: str) -> int:
    removed = 0
    for path in secrets_dir.glob(f"{institution_id}_*"):
        if path.is_file():
            path.unlink(missing_ok=True)
            removed += 1
    return removed


def _clear_all_secrets(*, secrets_dir: Path) -> int:
    removed = 0
    for path in secrets_dir.glob("*"):
        if path.is_file():
            path.unlink(missing_ok=True)
            removed += 1
    return removed


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
        help="Port for the bundled React frontend.",
        show_default=True,
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
        callback=_validate_products,
        help=(
            "Comma-separated Plaid products to request during Link."
            "Example: --products=transactions,investments"
        ),
    ),
    days_requested: int = typer.Option(
        365,
        "--days",
        min=1,
        help=(
            "Days of historical transactions requested during Link token creation "
            "(Plaid transactions.days_requested)."
        ),
        show_default=True,
    ),
    clear: bool = typer.Option(
        False,
        "--clear",
        help="Clear saved secrets via interactive institution selection UI.",
    ),
    clear_ins: Optional[str] = typer.Option(
        None,
        "--clear_ins",
        help="Clear saved secrets for one institution id (for example: --clear_ins ins_0000).",
    ),
    clear_all: bool = typer.Option(
        False,
        "--clear-all",
        help="Clear all saved secrets.",
    ),
) -> None:
    """
    Launch Plaid Link locally and wait for user to complete the flow returning an item_id and access_token.
    """
    secrets_path = default_secrets_dir()

    clear_mode_count = int(clear) + int(bool(clear_ins)) + int(clear_all)
    if clear_mode_count > 1:
        raise typer.BadParameter(
            "Use only one of --clear, --clear_ins, or --clear-all"
        )

    if clear_mode_count == 1 and any(
        [
            backend_port != DEFAULT_BACKEND_PORT,
            frontend_port != DEFAULT_FRONTEND_PORT,
            timeout != 300,
            not open_browser,
            products is not None,
            days_requested != 365,
        ]
    ):
        raise typer.BadParameter(
            "--clear/--clear_ins/--clear-all cannot be used with link options such as --backend-port, "
            "--frontend-port, --timeout, --open-browser/--no-open-browser, --products, or --days"
        )

    if clear_mode_count == 1:
        secrets_path.mkdir(parents=True, exist_ok=True)

        if clear_all:
            removed = _clear_all_secrets(secrets_dir=secrets_path)
            console.print(
                f"[green]Cleared[/] {removed} secret file(s) from {secrets_path}."
            )
            logger.info(
                "Cleared all secrets (count={}, secrets_dir={})",
                removed,
                secrets_path,
            )
            return

        selected_ids: list[str]
        if clear_ins:
            selected_ids = [clear_ins]
        elif clear:
            try:
                discovered = discover_institutions(secrets_dir=secrets_path)
                selected_ids = prompt_for_institutions(
                    discovered,
                    message="Select institution secret(s) to clear",
                )
            except ValueError as exc:
                raise typer.BadParameter(str(exc)) from exc
        else:
            raise typer.BadParameter(
                "Use one of --clear, --clear_ins, or --clear-all"
            )

        total_removed = 0
        for selected_id in selected_ids:
            removed = _clear_institution_secrets(
                secrets_dir=secrets_path,
                institution_id=selected_id,
            )
            total_removed += removed
            console.print(
                f"[green]Cleared[/] {removed} secret file(s) for {selected_id}."
            )

        logger.info(
            "Cleared institution secrets (institutions={}, files_removed={}, secrets_dir={})",
            selected_ids,
            total_removed,
            secrets_path,
        )
        return

    started_at = time.time()
    started_dt = dt.datetime.fromtimestamp(started_at)
    # Logging is configured once in the main Typer app callback.

    log_dir = default_log_dir()
    backend_log_path = build_log_path(
        log_dir=log_dir,
        prefix="backend",
        started_at=started_dt,
    )
    frontend_log_path = build_log_path(
        log_dir=log_dir,
        prefix="frontend",
        started_at=started_dt,
    )

    backend_proc: Optional[ManagedProcess] = None
    frontend_proc: Optional[ManagedProcess] = None

    try:
        try:
            frontend_dir = _get_frontend_dir()
        except FileNotFoundError as exc:
            console.print("[red]Frontend not found[/]")
            console.print(str(exc))
            console.print(
                "Looked for bundled build at 'yapcli/frontend/build/index.html'."
            )
            raise typer.Exit(code=1)

        logger.info(
            "Launching Plaid Link (backend_port={}, frontend_port={}, secrets_dir={})",
            backend_port,
            frontend_port,
            secrets_path,
        )
        console.print("[cyan]Starting Flask backend...[/]")
        backend_proc = start_backend(
            backend_port,
            secrets_path,
            backend_log_path,
            products=products,
            days_requested=days_requested,
        )
        console.print(
            f"[green]Backend running[/] on http://localhost:{backend_port}/api (log: {backend_log_path})"
        )

        console.print("[cyan]Starting frontend...[/]")
        frontend_proc = start_frontend(
            frontend_port,
            frontend_log_path,
            frontend_dir=frontend_dir,
            backend_port=backend_port,
        )
        console.print(
            f"[green]Frontend running[/] on http://localhost:{frontend_port}/ (log: {frontend_log_path})"
        )

        frontend_url = f"http://localhost:{frontend_port}/"
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
