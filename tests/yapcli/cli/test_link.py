from __future__ import annotations

import datetime as dt
import subprocess
import threading
import time
from pathlib import Path

import pytest
import questionary
from typer.testing import CliRunner

from yapcli.cli import link
from yapcli import cli as root_cli
from yapcli.logging import build_log_path


def test_build_log_path_uses_timestamp_and_prefix(tmp_path: Path) -> None:
    started_at = dt.datetime(2024, 1, 2, 3, 4, 5)

    log_dir = tmp_path / "logs"

    log_path = build_log_path(
        log_dir=log_dir,
        prefix="backend",
        started_at=started_at,
    )

    assert log_path.parent == log_dir
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


def test_start_backend_passes_products_arg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    secrets_dir = tmp_path / "secrets"
    secrets_dir.mkdir()
    log_path = tmp_path / "backend.log"

    captured_env = {}
    captured_cmd = []

    class FakeProc:
        pid = 123

        def poll(self):
            return None

    def fake_popen(*args, **kwargs):
        nonlocal captured_env
        nonlocal captured_cmd
        captured_cmd = list(args[0])
        captured_env = dict(kwargs.get("env", {}))
        return FakeProc()

    monkeypatch.setattr(link.subprocess, "Popen", fake_popen)

    managed = link.start_backend(
        port=8000,
        secrets_dir=secrets_dir,
        log_path=log_path,
        products="transactions,investments",
        days_requested=180,
    )

    try:
        assert "PLAID_PRODUCTS" not in captured_env
        assert captured_env.get("YAPCLI_DAYS_REQUESTED") == "180"
        assert captured_cmd == [
            link.sys.executable,
            "-m",
            "yapcli",
            "serve",
            "--port",
            "8000",
            "--products",
            "transactions,investments",
        ]
    finally:
        managed.log_handle.close()


def test_link_defaults_to_sandbox_secrets_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = CliRunner()
    seen: dict[str, Path] = {}
    seen_days: dict[str, int] = {}

    def fake_start_backend(
        port: int,
        secrets_dir: Path,
        log_path: Path,
        *,
        products=None,
        days_requested: int = 365,
    ):
        seen["secrets_dir"] = secrets_dir
        seen_days["value"] = days_requested
        return None

    monkeypatch.setattr(link, "_get_frontend_dir", lambda: Path("."))
    monkeypatch.setattr(link, "start_backend", fake_start_backend)
    monkeypatch.setattr(link, "start_frontend", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        link,
        "wait_for_credentials",
        lambda **kwargs: ("ins_1", "item-1", "access-1"),
    )
    monkeypatch.setattr(link, "terminate_process", lambda *args, **kwargs: None)
    monkeypatch.setattr(link, "_get_frontend_dir", lambda: Path("."))
    result = runner.invoke(
        root_cli.app,
        [
            "--sandbox",
            "link",
            "--no-open-browser",
            "--timeout",
            "1",
        ],
    )

    assert result.exit_code == 0, (
        f"Expected success but got exit_code={result.exit_code}\n"
        f"Output:\n{result.output}\n"
        f"Exception: {result.exception!r}"
    )
    assert seen["secrets_dir"] == link.default_secrets_dir()
    assert seen_days["value"] == 365


def test_link_passes_custom_days_requested(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = CliRunner()
    seen_days: dict[str, int] = {}

    def fake_start_backend(
        port: int,
        secrets_dir: Path,
        log_path: Path,
        *,
        products=None,
        days_requested: int = 365,
    ):
        seen_days["value"] = days_requested
        return None

    monkeypatch.setattr(link, "_get_frontend_dir", lambda: Path("."))
    monkeypatch.setattr(link, "start_backend", fake_start_backend)
    monkeypatch.setattr(link, "start_frontend", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        link,
        "wait_for_credentials",
        lambda **kwargs: ("ins_1", "item-1", "access-1"),
    )
    monkeypatch.setattr(link, "terminate_process", lambda *args, **kwargs: None)
    monkeypatch.setattr(link, "_get_frontend_dir", lambda: Path("."))
    result = runner.invoke(
        root_cli.app,
        [
            "--sandbox",
            "link",
            "--days",
            "120",
            "--no-open-browser",
            "--timeout",
            "1",
        ],
    )

    assert result.exit_code == 0
    assert seen_days["value"] == 120


def test_link_rejects_invalid_products(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = CliRunner()

    # Ensure we fail before trying to start subprocesses.
    monkeypatch.setattr(link, "start_backend", lambda *args, **kwargs: None)
    monkeypatch.setattr(link, "start_frontend", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        link, "wait_for_credentials", lambda **kwargs: ("ins", "item", "access")
    )
    monkeypatch.setattr(link, "terminate_process", lambda *args, **kwargs: None)

    result = runner.invoke(
        root_cli.app,
        [
            "--sandbox",
            "link",
            "--no-open-browser",
            "--timeout",
            "1",
            "--products",
            "transactions,liabilities",
        ],
    )

    assert result.exit_code != 0
    assert "Invalid --products" in result.output


def test_link_rejects_invalid_days(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = CliRunner()

    # failures should happen before backend/frontend are started
    monkeypatch.setattr(link, "start_backend", lambda *args, **kwargs: None)
    monkeypatch.setattr(link, "start_frontend", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        link,
        "wait_for_credentials",
        lambda **kwargs: ("ins", "item", "access"),
    )
    monkeypatch.setattr(link, "terminate_process", lambda *args, **kwargs: None)
    monkeypatch.setattr(link, "_get_frontend_dir", lambda: Path("."))

    for bad in ["0", "731"]:
        result = runner.invoke(
            root_cli.app,
            [
                "--sandbox",
                "link",
                "--no-open-browser",
                "--timeout",
                "1",
                "--days",
                bad,
            ],
        )
        assert result.exit_code != 0, f"expected failure for days={bad}"
        assert "Invalid value for '--days'" in result.output
def test_link_clear_all_clears_only_current_environment(tmp_path: Path) -> None:
    runner = CliRunner()
    env = {"YAPCLI_DEFAULT_DIRS": "CWD", "PLAID_ENV": "production"}

    with runner.isolated_filesystem(temp_dir=str(tmp_path)):
        cwd = Path.cwd()
        (cwd / "secrets").mkdir(parents=True, exist_ok=True)
        (cwd / "sandbox" / "secrets").mkdir(parents=True, exist_ok=True)
        (cwd / "secrets" / "ins_prod_access_token").write_text("prod-token")
        (cwd / "sandbox" / "secrets" / "ins_sandbox_access_token").write_text(
            "sandbox-token"
        )

        result = runner.invoke(root_cli.app, ["link", "--clear-all"], env=env)

        assert result.exit_code == 0
        assert not (cwd / "secrets" / "ins_prod_access_token").exists()
        assert (cwd / "sandbox" / "secrets" / "ins_sandbox_access_token").exists()


def test_link_clear_single_institution_by_argument(tmp_path: Path) -> None:
    runner = CliRunner()
    env = {"YAPCLI_DEFAULT_DIRS": "CWD", "PLAID_ENV": "production"}

    with runner.isolated_filesystem(temp_dir=str(tmp_path)):
        cwd = Path.cwd()
        secrets = cwd / "secrets"
        secrets.mkdir(parents=True, exist_ok=True)
        (secrets / "ins_0000_access_token").write_text("token")
        (secrets / "ins_0000_item_id").write_text("item")
        (secrets / "ins_1111_access_token").write_text("other")

        result = runner.invoke(
            root_cli.app,
            ["link", "--clear_ins", "ins_0000"],
            env=env,
        )

        assert result.exit_code == 0
        assert not (secrets / "ins_0000_access_token").exists()
        assert not (secrets / "ins_0000_item_id").exists()
        assert (secrets / "ins_1111_access_token").exists()


def test_link_clear_interactive_uses_questionary_and_item_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = CliRunner()
    env = {"YAPCLI_DEFAULT_DIRS": "CWD", "PLAID_ENV": "production"}

    class _AskResult:
        def ask(self):
            return ["ins_0000"]

    captured_titles: list[str] = []

    def fake_checkbox(message, choices):
        assert message == "Select institution secret(s) to clear"
        captured_titles.extend([choice.title for choice in choices])
        return _AskResult()

    class _FakeBackend:
        def __init__(self, access_token: str, item_id: str):
            self.access_token = access_token
            self.item_id = item_id

        def get_item(self):
            return {"institution": {"name": "Test Bank"}}

    monkeypatch.setattr(questionary, "checkbox", fake_checkbox)
    monkeypatch.setattr("yapcli.institutions.PlaidBackend", _FakeBackend)

    with runner.isolated_filesystem(temp_dir=str(tmp_path)):
        cwd = Path.cwd()
        secrets = cwd / "secrets"
        secrets.mkdir(parents=True, exist_ok=True)
        (secrets / "ins_0000_access_token").write_text("token")
        (secrets / "ins_0000_item_id").write_text("item_0000")

        result = runner.invoke(root_cli.app, ["link", "--clear"], env=env)

        assert result.exit_code == 0
        assert "item_id=ins_0000 - Test Bank" in captured_titles
        assert not (secrets / "ins_0000_access_token").exists()
        assert not (secrets / "ins_0000_item_id").exists()


def test_link_clear_rejects_multiple_clear_modes() -> None:
    runner = CliRunner()

    result = runner.invoke(
        root_cli.app,
        ["link", "--clear", "--clear_ins", "ins_0000"],
    )

    assert result.exit_code != 0
    assert "Use only one of --clear, --clear_ins, or --clear-all" in result.output


def test_link_clear_rejects_link_options(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = CliRunner()

    monkeypatch.setattr(link, "start_backend", lambda *args, **kwargs: None)

    result = runner.invoke(
        root_cli.app,
        ["link", "--clear-all", "--timeout", "1"],
    )

    assert result.exit_code != 0
    assert "cannot be used with link" in result.output
