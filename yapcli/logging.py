from __future__ import annotations

import datetime as dt
from pathlib import Path

from loguru import logger


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

    logger.info("Logging configured. Log file: {}", log_path)
    return log_path
