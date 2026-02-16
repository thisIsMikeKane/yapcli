from __future__ import annotations

import datetime as dt
import subprocess
import threading
import time
from pathlib import Path

import pytest

from yapcli.cli import link
from yapcli.logging import build_log_path


def test_build_log_path_uses_timestamp_and_prefix(tmp_path: Path) -> None:
    started_at = dt.datetime(2024, 1, 2, 3, 4, 5)

    log_path = build_log_path(
        log_dir=link.LOG_DIR,
        prefix="backend",
        started_at=started_at,
    )

    assert log_path.parent == link.LOG_DIR
    assert log_path.name.startswith("backend-20240102-030405")
    assert log_path.suffix == ".log"


def test_discover_credentials_returns_latest(tmp_path: Path) -> None:
    secrets_dir = tmp_path / "secrets"
    secrets_dir.mkdir()
    started_at = time.time()

    time.sleep(0.05)
    access_path = secrets_dir / "ins_123_access_token"
    item_path = secrets_dir / "ins_123_item_id"
    access_path.write_text("sandbox-access-token")
    item_path.write_text("sandbox-item-id")

    credentials = link.discover_credentials(secrets_dir, started_at)

    assert credentials == ("ins_123", "sandbox-item-id", "sandbox-access-token")


def test_wait_for_credentials_detects_new_files(tmp_path: Path) -> None:
    secrets_dir = tmp_path / "secrets"
    secrets_dir.mkdir()
    started_at = time.time()
    access_path = secrets_dir / "ins_live_access_token"
    item_path = secrets_dir / "ins_live_item_id"

    def write_credentials() -> None:
        time.sleep(0.1)
        access_path.write_text("sandbox-access-token")
        item_path.write_text("sandbox-item-id")

    writer = threading.Thread(target=write_credentials)
    writer.start()

    identifier, item_id, access_token = link.wait_for_credentials(
        secrets_dir=secrets_dir,
        started_at=started_at,
        timeout=5,
        backend_proc=None,
        frontend_proc=None,
    )

    writer.join()
    assert (identifier, item_id, access_token) == (
        "ins_live",
        "sandbox-item-id",
        "sandbox-access-token",
    )


def test_wait_for_credentials_times_out(tmp_path: Path) -> None:
    with pytest.raises(TimeoutError):
        link.wait_for_credentials(
            secrets_dir=tmp_path / "secrets",
            started_at=time.time(),
            timeout=1,
            backend_proc=None,
            frontend_proc=None,
        )


def test_terminate_process_stops_running_process(tmp_path: Path) -> None:
    log_path = tmp_path / "process.log"
    log_handle = log_path.open("w")
    process = subprocess.Popen(
        ["sleep", "30"], stdout=log_handle, stderr=subprocess.STDOUT
    )
    managed = link.ManagedProcess(process=process, log_handle=log_handle)

    try:
        link.terminate_process(managed)
        assert managed.process.poll() is not None
    finally:
        if managed.process.poll() is None:
            managed.process.kill()
        log_handle.close()
