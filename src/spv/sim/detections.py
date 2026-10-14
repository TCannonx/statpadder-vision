"""Simulated detector output: what stages 2 and 3 would give for the simulated camera.

The rates are starting values, to be measured on the reference clips in build step 3.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import shapely

from spv.sim.camera import CameraPath
from spv.sim.tracks import PitchTracks

BALL, FALSE = -2, -1


@dataclass(frozen=True)
class DetectionParams:
    miss_rate: float = 0.05
    crowd_radius_m: float = 1.0
    crowd_miss_rate: float = 0.30
    noise_base_m: float = 0.3
    noise_per_m: float = 0.01
    false_per_moment: float = 0.5
    team_flip_rate: float = 0.03
    ball_miss_rate: float = 0.30


@dataclass
class Detections:
    moment: np.ndarray
    xy: np.ndarray
    team: np.ndarray
    is_ball: np.ndarray
    conf: np.ndarray
    truth: np.ndarray


def visible(camera: CameraPath, xy: np.ndarray) -> np.ndarray:
    """(T, N) in-view mask for points (T, N, 2); NaN is never in view."""
    footprints = np.asarray(camera.footprint, dtype=object)[:, None]
    known = ~np.isnan(xy[..., 0])
    inside = shapely.contains_xy(footprints, np.nan_to_num(xy[..., 0], nan=-1e6),
                                 np.nan_to_num(xy[..., 1], nan=-1e6))
    return inside & known


def _false_detections(camera: CameraPath, rate: float,
                      rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """Uniform points in each moment's footprint, a Poisson number per moment."""
    footprints = np.asarray(camera.footprint, dtype=object)
    counts = rng.poisson(rate, size=len(footprints))
    if counts.sum() == 0:
        return np.zeros(0, dtype=int), np.zeros((0, 2))
    moments = np.repeat(np.arange(len(counts)), counts * 8)  # oversample, then keep the first `count` inside
    bounds = shapely.bounds(footprints[moments])
    xy = rng.uniform(bounds[:, :2], bounds[:, 2:])
    inside = shapely.contains_xy(footprints[moments], xy[:, 0], xy[:, 1])
    moments, xy = moments[inside], xy[inside]
    rank = np.arange(len(moments)) - np.searchsorted(moments, moments)
    keep = rank < counts[moments]
    return moments[keep], xy[keep]


def simulate_detections(tracks: PitchTracks, camera: CameraPath,
                        params: DetectionParams = DetectionParams(), seed: int = 0) -> Detections:
    rng = np.random.default_rng(seed)
    xy = np.asarray(tracks.xy, dtype=float)
    n_moments, n_players = xy.shape[:2]
    mast = np.asarray(camera.mast[:2])

    gaps = np.linalg.norm(xy[:, :, None] - xy[:, None, :], axis=-1)
    gaps[:, np.arange(n_players), np.arange(n_players)] = np.inf
    crowded = (np.nan_to_num(gaps, nan=np.inf) < params.crowd_radius_m).any(axis=2)
    miss = np.where(crowded, params.crowd_miss_rate, params.miss_rate)
    hit = visible(camera, xy) & (rng.random((n_moments, n_players)) >= miss)
    moment, player = np.nonzero(hit)
    true_xy = xy[moment, player]
    sigma = params.noise_base_m + params.noise_per_m * np.linalg.norm(true_xy - mast, axis=1)
    people_xy = true_xy + rng.normal(size=true_xy.shape) * sigma[:, None]
    true_team = np.array([0 if t == "home" else 1 for t in tracks.teams], dtype=np.int8)[player]
    flipped = rng.random(len(player)) < params.team_flip_rate
    team = np.where(flipped, 1 - true_team, true_team).astype(np.int8)

    ball_xy = np.asarray(tracks.ball_xy, dtype=float)
    ball_hit = visible(camera, ball_xy[:, None])[:, 0] & (rng.random(n_moments) >= params.ball_miss_rate)
    ball_moment = np.flatnonzero(ball_hit)
    ball_det = ball_xy[ball_moment] + rng.normal(size=(len(ball_moment), 2)) * params.noise_base_m

    false_moment, false_xy = _false_detections(camera, params.false_per_moment, rng)
    n_ball, n_false = len(ball_moment), len(false_moment)

    moments = np.concatenate([moment, ball_moment, false_moment])
    order = np.argsort(moments, kind="stable")
    return Detections(
        moment=moments[order],
        xy=np.concatenate([people_xy, ball_det, false_xy])[order],
        team=np.concatenate([team, np.full(n_ball, -1, np.int8),
                             rng.integers(0, 2, n_false).astype(np.int8)])[order],
        is_ball=np.concatenate([np.zeros(len(player), bool), np.ones(n_ball, bool), np.zeros(n_false, bool)])[order],
        conf=np.concatenate([rng.uniform(0.5, 1.0, len(player)), rng.uniform(0.3, 0.9, n_ball),
                             rng.uniform(0.25, 0.6, n_false)])[order],
        truth=np.concatenate([player, np.full(n_ball, BALL), np.full(n_false, FALSE)])[order],
    )
