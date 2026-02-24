from __future__ import annotations

import datetime as dt
import os
import re
from pathlib import Path
from typing import Mapping, Optional

from platformdirs import PlatformDirs

_APP_NAME = "yapcli"
_PLATFORM_DIRS = PlatformDirs(appname=_APP_NAME)


def _env_value(env: Optional[Mapping[str, str]], key: str) -> Optional[str]:
    if env is None:
        return os.getenv(key)
    value = env.get(key)
    return value


def _is_sandbox(env: Optional[Mapping[str, str]]) -> bool:
    return (_env_value(env, "PLAID_ENV") or "").strip() == "sandbox"


def default_dirs_mode(env: Optional[Mapping[str, str]] = None) -> str:
    """Return the default directory mode.

    Controlled by YAPCLI_DEFAULT_DIRS:
    - CWD: resolve config/secrets/logs relative to the current working directory
    - PLATFORM_DIRS: resolve config/secrets/logs using platformdirs

    Defaults to PLATFORM_DIRS.
    """

    raw = (_env_value(env, "YAPCLI_DEFAULT_DIRS") or "").strip().upper()
    if raw in {"CWD"}:
        return "CWD"
    if raw in {"PLATFORM_DIRS", "PLATFORMDIRS", "PLATFORM"}:
        return "PLATFORM_DIRS"
    return "PLATFORM_DIRS"


def default_config_dir(env: Optional[Mapping[str, str]] = None) -> Path:
    if default_dirs_mode(env) == "CWD":
        return Path.cwd()
    return Path(_PLATFORM_DIRS.user_config_path)


def default_log_dir(env: Optional[Mapping[str, str]] = None) -> Path:
    override = _env_value(env, "YAPCLI_LOG_DIR")
    if override:
        return Path(override)

    if default_dirs_mode(env) == "CWD":
        if _is_sandbox(env):
            return Path.cwd() / "sandbox" / "logs"
        return Path.cwd() / "logs"

    base = Path(_PLATFORM_DIRS.user_log_path)
    if _is_sandbox(env):
        return base / "sandbox"
    return base


def default_env_file_path(env: Optional[Mapping[str, str]] = None) -> Path:
    """Path used for writing configuration via `yapcli config` commands."""

    return default_config_dir(env) / ".env"


def default_secrets_dir(env: Optional[Mapping[str, str]] = None) -> Path:
    override = _env_value(env, "PLAID_SECRETS_DIR")
    if override:
        return Path(override)

    base = default_config_dir(env)
    if _is_sandbox(env):
        return base / "sandbox" / "secrets"
    return base / "secrets"


def default_output_dir(env: Optional[Mapping[str, str]] = None) -> Path:
    override = _env_value(env, "YAPCLI_OUTPUT_DIR")
    if override:
        return Path(override)

    if _is_sandbox(env):
        return Path.cwd() / "sandbox" / "output"
    return Path.cwd() / "output"


def timestamp_for_filename() -> str:
    """UTC timestamp suitable for filenames (e.g. 20260215T032018Z)."""

    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def safe_filename_component(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return cleaned or "unknown"
