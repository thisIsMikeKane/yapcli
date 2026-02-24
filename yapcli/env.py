from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Iterable

from dotenv import dotenv_values
from platformdirs import PlatformDirs

_APP_NAME = "yapcli"
_PLATFORM_DIRS = PlatformDirs(appname=_APP_NAME)

_LOADED_ENV_FILES: list[Path] = []


def cwd_env_file_path() -> Path:
    return Path.cwd() / ".env"


def platform_env_file_path() -> Path:
    return Path(_PLATFORM_DIRS.user_config_path) / ".env"


def _apply_env_values(
    values: Dict[str, str],
    *,
    preserve_keys: set[str],
    allow_override: bool,
) -> tuple[int, int, int, int]:
    """Apply values to os.environ.

    Behavior:
    - Keys present in preserve_keys are never modified.
    - If allow_override=True, keys not in preserve_keys may override existing values.

    Returns:
        (applied_new, overridden_existing, skipped_preserved, skipped_existing)
    """

    applied_new = 0
    overridden_existing = 0
    skipped_preserved = 0
    skipped_existing = 0

    for key, value in values.items():
        if key in preserve_keys:
            skipped_preserved += 1
            continue

        if key in os.environ:
            if allow_override:
                os.environ[key] = value
                overridden_existing += 1
            else:
                skipped_existing += 1
            continue

        os.environ[key] = value
        applied_new += 1

    return applied_new, overridden_existing, skipped_preserved, skipped_existing


def _read_env_file(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    parsed = dotenv_values(path)
    return {k: v for k, v in parsed.items() if k is not None and v is not None}


def load_env_files() -> Iterable[Path]:
    """Load env vars from both platform and CWD .env files.

    Precedence (highest to lowest):
    1. Existing os.environ
    2. CWD .env
    3. platformdirs user_config .env

    Returns an iterable of paths that were attempted in load order.
    """

    platform_path = platform_env_file_path()
    cwd_path = cwd_env_file_path()

    _LOADED_ENV_FILES.clear()

    # Capture what was already present so we never override a shell-provided value.
    baseline_keys = set(os.environ.keys())

    # Apply lowest-precedence first.
    platform_values = _read_env_file(platform_path)
    if platform_values:
        applied_new, overridden, preserved, skipped_existing = _apply_env_values(
            platform_values,
            preserve_keys=baseline_keys,
            allow_override=False,
        )
        _LOADED_ENV_FILES.append(platform_path)

    cwd_values = _read_env_file(cwd_path)
    if cwd_values:
        applied_new, overridden, preserved, skipped_existing = _apply_env_values(
            cwd_values,
            preserve_keys=baseline_keys,
            allow_override=True,
        )
        _LOADED_ENV_FILES.append(cwd_path)

    return (platform_path, cwd_path)


def loaded_env_file_paths() -> tuple[Path, ...]:
    """Return env files that were actually loaded (contained at least one value)."""

    return tuple(_LOADED_ENV_FILES)
