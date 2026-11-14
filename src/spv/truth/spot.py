"""Spot checks: 20 restarts, shots and goals per match, looked at by eye against the video."""

from __future__ import annotations

import json
from pathlib import Path

from spv.truth import truth_dir
from spv.truth.events import KINDS, TruthEvent

TARGETS = (("goal", 3), ("shot", 5), ("corner", 4), ("free_kick", 3), ("goal_kick", 2), ("throw_in", 2),
           ("kick_off", 1))
SAMPLE_SIZE = 20
FILL_KINDS = ("shot", "corner", "free_kick", "goal_kick", "throw_in")
VERDICTS = {"moment": ("ok", "off", "unseen"), "kind": ("ok", "wrong"), "place": ("ok", "wrong", "unsure"),
            "team": ("ok", "wrong", "unsure")}


def _spread(pool: list[TruthEvent], k: int) -> list[TruthEvent]:
    """k events spread evenly through the match."""
    if k <= 0 or not pool:
        return []
    if k >= len(pool):
        return list(pool)
    if k == 1:
        return [pool[len(pool) // 2]]
    return [pool[round(i * (len(pool) - 1) / (k - 1))] for i in range(k)]


def sample_spot_rows(events: list[TruthEvent], n: int = SAMPLE_SIZE) -> list[str]:
    def order(e: TruthEvent):
        return (e.half, e.video_s)

    by_kind = {kind: sorted((e for e in events if e.kind == kind), key=order) for kind, _ in TARGETS}
    chosen: list[TruthEvent] = []
    for kind, k in TARGETS:
        chosen += _spread(by_kind[kind], k)
    if len(chosen) < n:
        taken = {e.row_id for e in chosen}
        rest = sorted((e for kind in ("shot", "corner", "free_kick", "goal_kick", "throw_in")
                       for e in by_kind[kind] if e.row_id not in taken), key=order)
        chosen += _spread(rest, n - len(chosen))
    return [e.row_id for e in sorted(chosen, key=order)][:n]


def spot_path(match_id: str, repo_root: Path | None = None) -> Path:
    return truth_dir(repo_root) / "spot" / f"{match_id}.json"


def load_spot(match_id: str, repo_root: Path | None = None) -> dict:
    path = spot_path(match_id, repo_root)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"rows": [], "verdicts": {}}


def save_spot(match_id: str, data: dict, repo_root: Path | None = None) -> Path:
    path = spot_path(match_id, repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, sort_keys=True), encoding="utf-8")
    return path


def record_verdict(data: dict, row: str, *, moment: str, kind: str, place: str, team: str) -> None:
    if row not in data["rows"]:
        raise ValueError(f"row {row} is not in this match's spot-check sample")
    verdict = {"moment": moment, "kind": kind, "place": place, "team": team}
    for key, value in verdict.items():
        if value not in VERDICTS[key]:
            raise ValueError(f"{key} is one of {', '.join(VERDICTS[key])}")
    data["verdicts"][row] = verdict


def judged_rows(data: dict) -> list[str]:
    """Rows that can be judged: every row except those whose event is not visible on camera."""
    return [r for r in data["rows"] if data["verdicts"].get(r, {}).get("moment") != "unseen"]


def spot_score(data: dict) -> tuple[int, int, int]:
    """(right, checked, total) over the rows that can be judged. Right: the moment and the kind are right, and the
    place and team are not wrong."""
    judged = judged_rows(data)
    verdicts = [data["verdicts"][r] for r in judged if r in data["verdicts"]]
    right = sum(1 for v in verdicts
                if v["moment"] == "ok" and v["kind"] == "ok" and v["place"] != "wrong" and v["team"] != "wrong")
    return right, len(verdicts), len(judged)


def top_up(data: dict, events: list[TruthEvent], exclude=frozenset(), n: int = SAMPLE_SIZE,
           kinds=None) -> list[str]:
    """Replace each not-visible row by one that can be judged, until n rows can be judged. Returns the rows added.
    kinds limits the rows picked to those kinds (default: the usual fill kinds)."""
    allowed = FILL_KINDS if kinds is None else tuple(kinds)
    unknown = [k for k in allowed if k not in KINDS]
    if unknown:
        raise ValueError(f"unknown kind {', '.join(map(str, unknown))}; kinds are {', '.join(KINDS)}")
    by_id = {e.row_id: e for e in events}
    unseen_rows = [r for r in data["rows"] if data["verdicts"].get(r, {}).get("moment") == "unseen"]
    added: list[str] = []
    for row in unseen_rows:
        if len(judged_rows(data)) >= n:
            break
        if row not in by_id:
            continue
        gone = by_id[row]
        taken = set(data["rows"]) | set(exclude)
        left = [e for e in events if e.row_id not in taken]
        same = [e for e in left if e.kind == gone.kind] if kinds is None or gone.kind in allowed else []
        pool = same or [e for e in left if e.kind in allowed]
        if not pool:
            break
        pick = min(pool, key=lambda e: (abs((e.half - gone.half) * 1e6 + e.video_s - gone.video_s),
                                        e.half, e.video_s, e.row_id))
        data["rows"].append(pick.row_id)
        added.append(pick.row_id)
    return added
