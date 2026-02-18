from __future__ import annotations

import datetime as dt
import os
import re
import site
import sysconfig
from pathlib import Path

from platformdirs import PlatformDirs

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_APP_NAME = "yapcli"
_PLATFORM_DIRS = PlatformDirs(appname=_APP_NAME)


def _is_under(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _installed_lib_roots() -> list[Path]:
    roots: list[Path] = []

    for key in ("purelib", "platlib"):
        value = sysconfig.get_paths().get(key)
        if value:
            roots.append(Path(value).resolve())

    try:
        for value in site.getsitepackages():
            roots.append(Path(value).resolve())
    except Exception:
        pass

    try:
        user_site = site.getusersitepackages()
        if user_site:
            roots.append(Path(user_site).resolve())
    except Exception:
        pass

    deduped: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        key = str(root)
        if key not in seen:
            seen.add(key)
            deduped.append(root)
    return deduped


def _is_installed_package() -> bool:
    package_dir = _PROJECT_ROOT.resolve()
    return any(_is_under(package_dir, root) for root in _installed_lib_roots())


def _is_development_checkout() -> bool:
    if _is_installed_package():
        return False
    return (_PROJECT_ROOT / "pyproject.toml").exists()


def default_config_dir() -> Path:
    if _is_development_checkout():
        return _PROJECT_ROOT
    return Path(_PLATFORM_DIRS.user_config_path)


def default_log_dir() -> Path:
    override = os.getenv("YAPCLI_LOG_DIR")
    if override:
        return Path(override)

    if _is_development_checkout():
        return _PROJECT_ROOT / "logs"

    return Path(_PLATFORM_DIRS.user_log_path)


def default_data_dir() -> Path:
    """Default data directory.

    Uses the current working directory's `data` folder.
    """

    return Path.cwd() / "data"


def timestamp_for_filename() -> str:
    """UTC timestamp suitable for filenames (e.g. 20260215T032018Z)."""

    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def safe_filename_component(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return cleaned or "unknown"
