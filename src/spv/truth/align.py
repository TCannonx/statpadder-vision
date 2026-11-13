"""How each event file lines up with its video: anchor offsets per half, kits, attacking direction.

Video time = event file time + offset. Records hold ids and numbers only.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

from spv.truth import truth_dir

FLIP = {"left": "right", "right": "left"}


def alignment_path(match_id: str, repo_root: Path | None = None) -> Path:
    return truth_dir(repo_root) / "align" / f"{match_id}.json"


def load_alignment(match_id: str, repo_root: Path | None = None) -> dict:
    path = alignment_path(match_id, repo_root)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"marks": [], "kits": {}, "attack_marks": []}


def save_alignment(match_id: str, data: dict, repo_root: Path | None = None) -> Path:
    path = alignment_path(match_id, repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, sort_keys=True), encoding="utf-8")
    return path


def add_mark(data: dict, half: int, row: str, kind: str, offset_s: float) -> None:
    data["marks"] = [m for m in data["marks"] if m["row"] != row]
    data["marks"].append({"half": half, "row": row, "kind": kind, "offset_s": round(offset_s, 2)})


def _offsets(data: dict, half: int) -> list[float]:
    return [m["offset_s"] for m in data["marks"] if m["half"] == half]


def half_offset(data: dict, half: int) -> float | None:
    values = _offsets(data, half)
    return statistics.median(values) if values else None


def half_spread(data: dict, half: int) -> float | None:
    values = _offsets(data, half)
    return round(max(values) - min(values), 2) if len(values) >= 2 else None


def set_kit(data: dict, team: str, looks: str) -> None:
    data["kits"][team] = looks


def add_attack_mark(data: dict, half: int, row: str, team: str, goal_side: str) -> None:
    """goal_side: the side of the picture holding the goal the row's team is attacking."""
    if goal_side not in FLIP:
        raise ValueError("the goal is on the left or the right of the picture")
    data["attack_marks"] = [m for m in data["attack_marks"] if m["row"] != row]
    data["attack_marks"].append({"half": half, "row": row, "team": team, "goal": goal_side})


def attack_summary(data: dict) -> dict[int, dict]:
    summary = {}
    for half in (1, 2):
        sides = [m["goal"] if m["team"] == "A" else FLIP[m["goal"]]
                 for m in data["attack_marks"] if m["half"] == half]
        if sides:
            top = max(("left", "right"), key=sides.count)
            summary[half] = {"A": top, "agree": sides.count(top), "of": len(sides)}
    return summary


def attack_consistent(summary: dict[int, dict], minimum: int = 3) -> bool:
    if set(summary) != {1, 2}:
        return False
    if any(s["of"] < minimum or s["agree"] != s["of"] for s in summary.values()):
        return False
    return summary[2]["A"] == FLIP[summary[1]["A"]]
