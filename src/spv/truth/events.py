"""Trusted events read from an event file, as P0 and the scorer need them.

Only kick-offs, restarts, shots and goals are kept, and never a player's or a team's name:
teams become A (the first team named in the file) and B.
"""

from __future__ import annotations

import csv
import io
import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

KINDS = ("kick_off", "corner", "free_kick", "throw_in", "goal_kick", "penalty", "shot", "goal")
_RESTARTS = {"corner-kick": "corner", "free-kick": "free_kick", "throw-in": "throw_in", "goal-kick": "goal_kick"}
_HALVES = {"1st half": 1, "2nd half": 2}


@dataclass(frozen=True)
class TruthEvent:
    row_id: str
    half: int  # 1 or 2
    video_s: float  # seconds on the event file's own video clock
    kind: str  # one of KINDS
    team: str  # "A" or "B"
    x: float | None  # 0-1 towards the goal the team attacks
    y: float | None  # 0-1 from the team's left touchline
    outcome: str | None = None  # shots: on / off / blocked (Eyeball) or the app's outcome


@dataclass(frozen=True)
class TruthFile:
    source: str  # "eyeball" or "statpadder"
    rows: int
    timed_rows: int
    events: list[TruthEvent] = field(default_factory=list)


def _number(text: str | None) -> float | None:
    text = (text or "").strip().replace(",", ".")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _rows(text: str, delimiter: str) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    return [{k.strip(): (v or "").strip() for k, v in row.items() if isinstance(k, str)} for row in reader]


class _Teams:
    def __init__(self) -> None:
        self.names: list[str] = []

    def letter(self, name: str) -> str | None:
        if not name:
            return None
        if name not in self.names:
            self.names.append(name)
        return "A" if name == self.names[0] else "B"


def read_eyeball(path: Path) -> TruthFile:
    rows = _rows(Path(path).read_text(encoding="utf-8-sig"), ";")
    events, timed = _classify_eyeball(rows)
    return TruthFile("eyeball", len(rows), timed, events)


def _classify_eyeball(rows: list[dict[str, str]]) -> tuple[list[TruthEvent], int]:
    """Turn Eyeball-shaped rows (CSV rows, or XML instances reshaped to match) into trusted events."""
    teams, events, timed = _Teams(), [], 0
    kick_off_due = {1: True, 2: True}  # the first pass of a half, and the first after a goal
    for row in rows:
        half = _HALVES.get(row.get("Half", ""))
        team = teams.letter(row.get("Team", ""))
        t = _number(row.get("Video time"))
        if t is not None:
            timed += 1
        if half is None or team is None or t is None:
            continue
        try:
            details = json.loads(row.get("Details") or "{}")
        except json.JSONDecodeError:
            details = {}
        x, y = _number(row.get("X coordinate")), _number(row.get("Y coordinate"))
        kind, outcome = None, None
        event = row.get("Event", "")
        if event == "pass":
            if kick_off_due[half] and x is not None and 0.4 <= x <= 0.6:
                kind = "kick_off"
            else:
                kind = _RESTARTS.get(details.get("restart", "no"))
            kick_off_due[half] = False
        elif event == "shot":
            kind = "penalty" if details.get("restart") == "penalty-kick" else "shot"
            outcome = details.get("on_target")
        elif event == "goal":
            kind = "goal"
            kick_off_due[half] = True
        if kind:
            events.append(TruthEvent(row.get("ID", ""), half, t, kind, team, x, y, outcome))
    return events, timed


def read_eyeball_xml(path: Path) -> TruthFile:
    """An Eyeball Sportscode XML export: the same data as the CSV, in <instance> elements."""
    root = ET.fromstring(Path(path).read_bytes())
    rows: list[dict[str, str]] = []
    for inst in root.iter("instance"):
        labels: dict[str, str] = {}
        for label in inst.findall("label"):
            labels.setdefault((label.findtext("group") or "").strip(), (label.findtext("text") or "").strip())
        if "TEAM" not in labels:  # period markers such as "Kick Off"
            continue
        event, details = labels.get("EVENT", ""), {}
        if event == "pass" and "PASS_RESTART" in labels:
            details["restart"] = labels["PASS_RESTART"]
        elif event == "shot":
            if "SHOT_RESTART" in labels:
                details["restart"] = labels["SHOT_RESTART"]
            if "SHOT_ON_TARGET" in labels:
                details["on_target"] = labels["SHOT_ON_TARGET"]
        rows.append(
            {
                "ID": (inst.findtext("ID") or "").strip(),
                "Half": labels.get("HALF", ""),
                "Event": event,
                "Team": labels["TEAM"],
                "Video time": (inst.findtext("start") or "").strip(),
                "X coordinate": labels.get("X_COORDINATE", ""),
                "Y coordinate": labels.get("Y_COORDINATE", ""),
                "Details": json.dumps(details),
            }
        )
    events, timed = _classify_eyeball(rows)
    return TruthFile("eyeball", len(rows), timed, events)


def read_statpadder(path: Path) -> TruthFile:
    """A StatPadder match CSV export. Hand-coded matches have corners and shots, not other restarts."""
    rows = _rows(Path(path).read_text(encoding="utf-8-sig"), ",")
    teams, periods, events, timed = _Teams(), [], [], 0
    for i, row in enumerate(rows, start=1):
        period = row.get("period", "")
        if period not in periods:
            periods.append(period)
        half = periods.index(period) + 1
        team = teams.letter(row.get("team", ""))
        ms = _number(row.get("video_ms"))
        if ms is not None:
            timed += 1
        if half > 2 or team is None or ms is None:
            continue
        t, row_id = ms / 1000, f"r{i}"
        x, y = _number(row.get("x")), _number(row.get("y"))
        if row.get("type") == "corner":
            events.append(TruthEvent(row_id, half, t, "corner", team, x, y))
        elif row.get("type") == "shot":
            outcome = row.get("outcome") or None
            kind = "penalty" if row.get("penalty", "").lower() == "true" else "shot"
            events.append(TruthEvent(row_id, half, t, kind, team, x, y, outcome))
            if outcome == "goal":
                events.append(TruthEvent(f"{row_id}g", half, t, "goal", team, x, y))
    return TruthFile("statpadder", len(rows), timed, events)


def read_events(path: Path) -> TruthFile:
    text = Path(path).read_text(encoding="utf-8-sig")
    if text.lstrip().startswith(("<?xml", "<file")):
        return read_eyeball_xml(path)
    lines = text.splitlines()
    first = lines[0] if lines else ""
    if "Video time" in first:
        return read_eyeball(path)
    if "video_ms" in first:
        return read_statpadder(path)
    raise ValueError(f"{Path(path).name}: not an Eyeball events file or a StatPadder export")


def zone(x: float | None, y: float | None) -> str:
    if x is None or y is None:
        return "no place"
    third = "own third" if x < 1 / 3 else "middle third" if x < 2 / 3 else "final third"
    flank = "left" if y < 1 / 3 else "centre" if y < 2 / 3 else "right"
    return f"{third}, {flank} (as the team attacks)"
