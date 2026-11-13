"""Matches with a video and a trusted event file. Paths stay in the git-ignored local.config.json."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from spv import config
from spv.truth.events import read_events

ID_PATTERN = re.compile(r"^m\d{2}$")
_KIND_COLUMNS = [("kick_off", "Kick-offs"), ("corner", "Corners"), ("free_kick", "Free kicks"),
                 ("throw_in", "Throw-ins"), ("goal_kick", "Goal kicks"), ("shot", "Shots"), ("goal", "Goals")]


def add_match(match_id: str, video: Path, events: Path, repo_root: Path | None = None) -> None:
    if not ID_PATTERN.match(match_id):
        raise ValueError("match ids are anonymous: m01, m02, ...")
    for path in (video, events):
        if not Path(path).is_file():
            raise FileNotFoundError(f"not found: {Path(path).name}")
    read_events(Path(events))  # refuses a file in neither format
    local = config.load_local_config(repo_root)
    local.setdefault("truth_matches", {})[match_id] = {
        "video": str(Path(video).resolve()), "events": str(Path(events).resolve())}
    config.save_local_config(local, repo_root)


def registered(repo_root: Path | None = None) -> dict[str, dict]:
    return config.load_local_config(repo_root).get("truth_matches", {})


def inventory(repo_root: Path | None = None, probe=None) -> list[dict]:
    if probe is None:
        from spv.stages.probe import probe_video as probe
    rows = []
    for match_id, match in sorted(registered(repo_root).items()):
        tf = read_events(Path(match["events"]))
        rows.append({
            "id": match_id,
            "source": tf.source,
            "minutes": round(probe(Path(match["video"]))["duration_s"] / 60),
            "rows": tf.rows,
            "timed_share": round(tf.timed_rows / tf.rows, 3) if tf.rows else 0.0,
            "halves": len({e.half for e in tf.events}),
            "kinds": dict(Counter(e.kind for e in tf.events)),
        })
    return rows


def inventory_markdown(rows: list[dict], split: dict | None = None) -> str:
    def role(match_id: str) -> str:
        if not split:
            return "-"
        if match_id in split["p0"]:
            return "held out, P0"
        return "held out" if match_id in split["holdout"] else "train"

    head = ["Match", "Source", "Video (min)", "Rows", "Timed", "Halves", *[t for _, t in _KIND_COLUMNS], "Role"]
    lines = ["# Matches with trusted events", "", "| " + " | ".join(head) + " |",
             "| " + " | ".join("---" for _ in head) + " |"]
    for r in rows:
        cells = [r["id"], r["source"], str(r["minutes"]), str(r["rows"]), f"{r['timed_share']:.0%}", str(r["halves"]),
                 *[str(r["kinds"].get(k, 0)) for k, _ in _KIND_COLUMNS], role(r["id"])]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"
