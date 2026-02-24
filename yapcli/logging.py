from __future__ import annotations

import datetime as dt
from pathlib import Path

from loguru import logger

from yapcli.env import loaded_env_file_paths
from yapcli.utils import default_log_dir, default_output_dir, default_secrets_dir


def log_startup_paths() -> None:
    """Log the same path info shown by `yapcli config paths`."""

    loaded_envs = loaded_env_file_paths()
    if loaded_envs:
        logger.info("Loaded .env files: {}", ", ".join(str(p) for p in loaded_envs))
    else:
        logger.info("Loaded .env files: (none)")

    logger.info(
        "Default directories: secrets_dir={}, log_dir={}, output_dir={}",
        default_secrets_dir(),
        default_log_dir(),
        default_output_dir(),
    )


def build_log_path(*, log_dir: Path, prefix: str, started_at: dt.datetime) -> Path:
    timestamp = started_at.strftime("%Y%m%d-%H%M%S")
    return log_dir / f"{prefix}-{timestamp}.log"


def configure_logging(
    *,
    log_dir: Path,
    prefix: str,
    started_at: dt.datetime,
    level: str = "INFO",
) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = build_log_path(log_dir=log_dir, prefix=prefix, started_at=started_at)

    logger.remove()
    logger.add(
        log_path,
        level=level,
        enqueue=True,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {message}",
    )
    return log_path
