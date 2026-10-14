"""Local, git-ignored settings: reference clip paths and the data folder."""

from __future__ import annotations

import json
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_NAME = "local.config.json"


def load_local_config(repo_root: Path | None = None) -> dict:
    path = Path(repo_root or REPO_ROOT) / CONFIG_NAME
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def save_local_config(config: dict, repo_root: Path | None = None) -> None:
    path = Path(repo_root or REPO_ROOT) / CONFIG_NAME
    path.write_text(json.dumps(config, indent=1), encoding="utf-8")


def data_dir(repo_root: Path | None = None) -> Path:
    if os.environ.get("SPV_DATA_DIR"):
        return Path(os.environ["SPV_DATA_DIR"])
    configured = load_local_config(repo_root).get("data_dir")
    return Path(configured) if configured else Path(repo_root or REPO_ROOT) / "data"
