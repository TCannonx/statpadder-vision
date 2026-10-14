"""Simulator scenes (windows of a match that each test one difficulty) and the null solver."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from spv.sim.camera import CameraPath
from spv.sim.detections import Detections, visible
from spv.sim.tracks import PitchTracks
from spv.sptrack import TrackFile, blank_track

CROWD_PLAYERS = 10
CROWD_DISTANCE_M = 20.0
SUB_LEAD_S = 10.0
OUT_OF_VIEW_LEAD_S = 5.0


@dataclass(frozen=True)
class Scene:
    name: str
    start: int
    stop: int


def _window(start: int, size: int, n_moments: int) -> tuple[int, int]:
    start = int(min(max(start, 0), max(n_moments - size, 0)))
    return start, start + size


def _longest_run(mask: np.ndarray) -> tuple[int, int]:
    """(start, length) of the longest run of True in a 1-D mask."""
    edges = np.flatnonzero(np.diff(np.r_[False, mask, False].astype(int)))
    starts, stops = edges[::2], edges[1::2]
    if len(starts) == 0:
        return 0, 0
    k = int(np.argmax(stops - starts))
    return int(starts[k]), int(stops[k] - starts[k])


def find_scenes(tracks: PitchTracks, camera: CameraPath, length_s: float = 60.0) -> list[Scene]:
    size = round(length_s * tracks.rate)
    n_moments = len(tracks.times_s)
    x = tracks.xy[..., 0]

    length = tracks.pitch[0]
    near_goal = np.maximum((x < CROWD_DISTANCE_M).sum(axis=1), (x > length - CROWD_DISTANCE_M).sum(axis=1))
    running = np.r_[0, np.cumsum(near_goal >= CROWD_PLAYERS)]
    per_window = running[size:] - running[:-size] if n_moments > size else running[-1:]
    scenes = [Scene("crowded_box", *_window(int(np.argmax(per_window)), size, n_moments))]

    on_pitch = ~np.isnan(x)
    hidden = on_pitch & ~visible(camera, tracks.xy)
    run_start, _ = max((_longest_run(hidden[:, i]) for i in range(hidden.shape[1])), key=lambda r: r[1])
    lead = round(OUT_OF_VIEW_LEAD_S * tracks.rate)
    scenes.append(Scene("long_out_of_view", *_window(run_start - lead, size, n_moments)))

    first_on = np.where(on_pitch.any(axis=0), on_pitch.argmax(axis=0), -1)
    late = first_on[first_on > 0]
    if len(late) == 0:
        raise ValueError("no substitute comes on in this match")
    start = int(late.min()) - round(SUB_LEAD_S * tracks.rate)
    scenes.append(Scene("substitution", *_window(start, size, n_moments)))
    return scenes


def null_solver(detections: Detections | None, n_moments: int, rate: float,
                pitch: tuple[float, float]) -> TrackFile:
    """Every slot unknown: the placeholder that stage 4 replaces."""
    return blank_track(n_moments, rate, pitch)
