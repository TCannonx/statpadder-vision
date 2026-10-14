"""Scoring a tracking output against simulator truth."""

from __future__ import annotations

import numpy as np
from scipy.optimize import linear_sum_assignment

from spv.lineup import SLOTS_PER_TEAM, TEAMS
from spv.sim.tracks import PitchTracks
from spv.sptrack import State, TrackFile, blank_track, decode, encode

WITHIN_M = 2.0
NO_MATCH = 1e9


def _match(slot_xy: np.ndarray, truth_xy: np.ndarray) -> list[tuple[int, int]]:
    """Slot-to-player pairs minimising mean distance over the moments both have positions."""
    d = np.linalg.norm(slot_xy[:, :, None] - truth_xy[:, None, :], axis=-1)  # (W, S, P)
    counts = (~np.isnan(d)).sum(axis=0)
    cost = np.where(counts > 0, np.nansum(d, axis=0) / np.maximum(counts, 1), NO_MATCH)
    rows, cols = linear_sum_assignment(cost)
    return [(r, c) for r, c in zip(rows, cols) if cost[r, c] < NO_MATCH]


def score_positions(track: TrackFile, truth: PitchTracks, start: int, stop: int) -> dict[str, float]:
    xy, _, state = decode(track.positions[start:stop])
    true_xy = truth.xy[start:stop]
    true_on = ~np.isnan(true_xy[..., 0])
    shown = state <= State.PREDICTED
    within = seen = false = 0
    for k, team in enumerate(TEAMS):
        slots = np.arange(k * SLOTS_PER_TEAM, (k + 1) * SLOTS_PER_TEAM)
        players = np.array([i for i, t in enumerate(truth.teams) if t == team], dtype=int)
        unmatched = set(slots.tolist())
        for s, p in _match(xy[:, slots], true_xy[:, players]):
            slot, player = slots[s], players[p]
            unmatched.discard(int(slot))
            dist = np.linalg.norm(xy[:, slot] - true_xy[:, player], axis=-1)
            within += int((true_on[:, player] & shown[:, slot] & (dist <= WITHIN_M)).sum())
            seen += int((true_on[:, player] & (state[:, slot] == State.SEEN)).sum())
            false += int((shown[:, slot] & ~true_on[:, player]).sum())
        false += sum(int(shown[:, slot].sum()) for slot in unmatched)
    total_true, total_shown = int(true_on.sum()), int(shown.sum())
    return {"within_2m": within / total_true if total_true else 0.0,
            "seen_share": seen / total_true if total_true else 0.0,
            "false_players": false / total_shown if total_shown else 0.0}


def track_from_truth(truth: PitchTracks, start: int, stop: int, unc_m: float = 0.0) -> TrackFile:
    """The truth as a track: every on-pitch player SEEN; a substitute takes the first freed slot.

    Known limit: a slot that changed player at a substitution is scored against one of them only;
    identity scoring arrives with stage 4.
    """
    n = len(truth.times_s)
    track = blank_track(n, truth.rate, truth.pitch)
    xy = np.full((n, 2 * SLOTS_PER_TEAM, 2), np.nan)
    state = np.full((n, 2 * SLOTS_PER_TEAM), State.UNKNOWN)
    on = ~np.isnan(truth.xy[..., 0])
    for k, team in enumerate(TEAMS):
        players = [i for i, t in enumerate(truth.teams) if t == team]
        holder: list[int | None] = [None] * SLOTS_PER_TEAM
        for t in range(start, stop):
            for p in players:
                if on[t, p] and p not in holder:
                    free = next((s for s, h in enumerate(holder) if h is None or not on[t, h]), None)
                    if free is None:
                        raise ValueError(f"more than {SLOTS_PER_TEAM} {team} players on the pitch at moment {t}")
                    holder[free] = p
            for s, p in enumerate(holder):
                if p is not None and on[t, p]:
                    xy[t, k * SLOTS_PER_TEAM + s] = truth.xy[t, p]
                    state[t, k * SLOTS_PER_TEAM + s] = State.SEEN
    track.positions = encode(xy, np.full(state.shape, unc_m), state)
    return track
