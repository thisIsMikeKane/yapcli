from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Tuple

from yapcli.utils import default_config_dir

SECRETS_DIR_ENV_VAR = "PLAID_SECRETS_DIR"


_CONFIG_DIR = default_config_dir()
DEFAULT_SECRETS_DIR = _CONFIG_DIR / "secrets"
DEFAULT_SANDBOX_SECRETS_DIR = _CONFIG_DIR / "sandbox" / "secrets"


def default_secrets_dir() -> Path:
    override = os.getenv(SECRETS_DIR_ENV_VAR)
    if override:
        return Path(override)
    if os.getenv("PLAID_ENV") == "sandbox":
        return DEFAULT_SANDBOX_SECRETS_DIR
    return DEFAULT_SECRETS_DIR


def read_secret_required(path: Path, *, label: str) -> str:
    try:
        value = path.read_text().strip()
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Missing {label} file: {path}") from exc

    if not value:
        raise ValueError(f"Empty {label} in file: {path}")

    return value


def load_credentials(
    *, institution_id: str, secrets_dir: Optional[Path] = None
) -> Tuple[str, str]:
    """Load (item_id, access_token) for an institution_id from secrets files."""

    secrets_path = secrets_dir or default_secrets_dir()
    access_path = secrets_path / f"{institution_id}_access_token"
    item_path = secrets_path / f"{institution_id}_item_id"

    item_id = read_secret_required(item_path, label="item_id")
    access_token = read_secret_required(access_path, label="access_token")

    return item_id, access_token
