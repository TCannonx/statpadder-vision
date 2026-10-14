"""The match lineup: who starts, substitutions and red cards, and slot occupancy over time.

Event times are seconds of the video, not the match clock.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np

SLOTS_PER_TEAM = 11
TEAMS = ("home", "away")


class LineupError(ValueError):
    pass


def slot_ids() -> list[str]:
    return [f"{team}_{i:02d}" for team in TEAMS for i in range(1, SLOTS_PER_TEAM + 1)]


@dataclass(frozen=True)
class Player:
    id: str
    number: int | None
    starter: bool


@dataclass(frozen=True)
class Team:
    name: str
    players: tuple[Player, ...]


@dataclass(frozen=True)
class Event:
    type: Literal["sub", "red"]
    team: Literal["home", "away"]
    time_s: float
    off: str | None = None
    on: str | None = None
    player: str | None = None


@dataclass(frozen=True)
class Lineup:
    home: Team
    away: Team
    events: tuple[Event, ...]

    def team(self, team: str) -> Team:
        return {"home": self.home, "away": self.away}[team]

    def on_pitch(self, team: str, time_s: float) -> int:
        starters = sum(p.starter for p in self.team(team).players)
        reds = sum(1 for e in self.events if e.type == "red" and e.team == team and e.time_s <= time_s)
        return starters - reds


def slot_occupancy(lineup: Lineup, times_s: np.ndarray) -> np.ndarray:
    times_s = np.asarray(times_s, dtype=float)
    occ = np.zeros((len(times_s), 2 * SLOTS_PER_TEAM), dtype=bool)
    for k, team in enumerate(TEAMS):
        starters = sum(p.starter for p in lineup.team(team).players)
        reds = sorted(e.time_s for e in lineup.events if e.type == "red" and e.team == team)
        counts = starters - np.searchsorted(reds, times_s, side="right")
        slots = np.arange(SLOTS_PER_TEAM)
        occ[:, k * SLOTS_PER_TEAM:(k + 1) * SLOTS_PER_TEAM] = slots[None, :] < counts[:, None]
    return occ


def _team(data: dict, side: str) -> Team:
    try:
        players = tuple(
            Player(id=str(p["id"]), number=p.get("number"), starter=bool(p["starter"]))
            for p in data[side]["players"]
        )
        team = Team(name=str(data[side]["name"]), players=players)
    except (KeyError, TypeError) as exc:
        raise LineupError(f"lineup: {side} is missing field {exc}") from exc
    starters = sum(p.starter for p in players)
    if starters > SLOTS_PER_TEAM:
        raise LineupError(f"lineup: {side} has {starters} starters, at most {SLOTS_PER_TEAM} allowed")
    return team


def load_lineup(path: Path) -> Lineup:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    home, away = _team(data, "home"), _team(data, "away")
    ids = {"home": {p.id for p in home.players}, "away": {p.id for p in away.players}}
    events = []
    for i, e in enumerate(data.get("events", [])):
        try:
            event = Event(type=e["type"], team=e["team"], time_s=float(e["time_s"]),
                          off=e.get("off"), on=e.get("on"), player=e.get("player"))
        except KeyError as exc:
            raise LineupError(f"lineup: event {i} is missing field {exc}") from exc
        if event.type not in ("sub", "red") or event.team not in TEAMS:
            raise LineupError(f"lineup: event {i} has type {event.type!r} / team {event.team!r}")
        named = [event.off, event.on] if event.type == "sub" else [event.player]
        for pid in named:
            if pid not in ids[event.team]:
                raise LineupError(f"lineup: event {i} names player {pid!r}, not in the {event.team} squad")
        events.append(event)
    return Lineup(home=home, away=away, events=tuple(sorted(events, key=lambda e: e.time_s)))
