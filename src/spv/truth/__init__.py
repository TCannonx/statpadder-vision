"""Phase P0: checking event files against their videos."""

from __future__ import annotations

from pathlib import Path

from spv import config


def truth_dir(repo_root: Path | None = None) -> Path:
    """Where the committed P0 records live. Ids and numbers only: no names, paths or frames."""
    return Path(repo_root or config.REPO_ROOT) / "tests" / "truth"
