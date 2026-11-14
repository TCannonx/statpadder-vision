"""The held-out matches: never trained on, never tuned on. Fixed once made."""

from __future__ import annotations

import json
import random
from pathlib import Path

from spv.truth import truth_dir

SEED = 20261113


def split_path(repo_root: Path | None = None) -> Path:
    return truth_dir(repo_root) / "split.json"


def choose_holdout(rows: list[dict], n: int = 5, seed: int = SEED) -> list[str]:
    """Eyeball matches first (full event stream), hand-coded ones only if there are too few.
    The first three returned are the P0 matches."""
    def usable(r: dict) -> bool:
        return r["halves"] == 2 and r["timed_share"] >= 0.95

    eyeball = sorted(r["id"] for r in rows if usable(r) and r["source"] == "eyeball")
    others = sorted(r["id"] for r in rows if usable(r) and r["source"] != "eyeball")
    rng = random.Random(seed)
    picked = rng.sample(eyeball, min(n, len(eyeball)))
    if len(picked) < n:
        picked += rng.sample(others, min(n - len(picked), len(others)))
    return picked


def save_split(holdout: list[str], all_ids: list[str], repo_root: Path | None = None, force: bool = False) -> Path:
    path = split_path(repo_root)
    if path.exists() and not force:
        raise FileExistsError("the split is fixed once made: use --force only if Thomas agrees")
    data = {"seed": SEED, "holdout": holdout, "p0": holdout[:3], "train": sorted(set(all_ids) - set(holdout))}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1), encoding="utf-8")
    return path


def load_split(repo_root: Path | None = None) -> dict | None:
    path = split_path(repo_root)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
