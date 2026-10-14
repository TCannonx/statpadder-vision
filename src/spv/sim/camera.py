"""A simulated ball-following camera on a mast at the halfway line.

The parameter defaults are starting values; build step 2 tunes them to clip1's solved camera.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import shapely

from spv.sim.tracks import PitchTracks

HORIZON_CUT_M = 200.0


@dataclass(frozen=True)
class CameraParams:
    mast_back_m: float = 3.0
    mast_height_m: float = 8.0
    lag_s: float = 0.7
    view_width_m: float = 35.0
    hfov_min_deg: float = 20.0
    hfov_max_deg: float = 70.0
    aspect: float = 16 / 9
    margin_m: float = 5.0


@dataclass
class CameraPath:
    mast: tuple[float, float, float]
    aim_xy: np.ndarray
    hfov_deg: np.ndarray
    footprint: list[shapely.Polygon]


def _aim(ball_xy: np.ndarray, pitch: tuple[float, float], alpha: float) -> np.ndarray:
    aim = np.empty_like(ball_xy)
    known = np.flatnonzero(~np.isnan(ball_xy[:, 0]))
    current = ball_xy[known[0]] if len(known) else np.array(pitch) / 2
    for t, ball in enumerate(ball_xy):
        if not np.isnan(ball[0]):
            current = current + (ball - current) * alpha
        aim[t] = current
    return aim


def _corners(mast: np.ndarray, aim_xy: np.ndarray, hfov_deg: np.ndarray, aspect: float) -> np.ndarray:
    """Ground points (T, 4, 2) where the image corners' rays meet the pitch plane."""
    target = np.column_stack([aim_xy, np.zeros(len(aim_xy))])
    forward = target - mast
    forward /= np.linalg.norm(forward, axis=1, keepdims=True)
    right = np.cross(forward, [0.0, 0.0, 1.0])
    right /= np.linalg.norm(right, axis=1, keepdims=True)
    up = np.cross(right, forward)
    tan_h = np.tan(np.radians(hfov_deg) / 2)[:, None]
    tan_v = tan_h / aspect
    points = []
    for sx, sy in [(-1, -1), (1, -1), (1, 1), (-1, 1)]:
        ray = forward + sx * tan_h * right + sy * tan_v * up
        down = ray[:, 2] < -1e-9
        scale = np.where(down, -mast[2] / np.where(down, ray[:, 2], -1.0), np.inf)
        hit = mast[:2] + scale[:, None] * ray[:, :2]
        flat = ray[:, :2] / np.linalg.norm(ray[:, :2], axis=1, keepdims=True)
        far = mast[:2] + HORIZON_CUT_M * flat
        too_far = ~down | (np.linalg.norm(hit - mast[:2], axis=1) > HORIZON_CUT_M)
        points.append(np.where(too_far[:, None], far, hit))
    return np.stack(points, axis=1)


def simulate_camera(tracks: PitchTracks, params: CameraParams = CameraParams()) -> CameraPath:
    length, width = tracks.pitch
    mast = np.array([length / 2, -params.mast_back_m, params.mast_height_m])
    alpha = 1 - np.exp(-(1 / tracks.rate) / params.lag_s)
    aim = _aim(np.asarray(tracks.ball_xy, dtype=float), tracks.pitch, alpha)
    distance = np.linalg.norm(np.column_stack([aim, np.zeros(len(aim))]) - mast, axis=1)
    hfov = np.clip(np.degrees(2 * np.arctan(params.view_width_m / 2 / distance)),
                   params.hfov_min_deg, params.hfov_max_deg)
    corners = _corners(mast, aim, hfov, params.aspect)
    hulls = shapely.convex_hull(shapely.multipoints(corners.reshape(-1, 2),
                                                    indices=np.repeat(np.arange(len(aim)), 4)))
    grown = shapely.box(-params.margin_m, -params.margin_m, length + params.margin_m, width + params.margin_m)
    footprint = list(shapely.intersection(hulls, grown))
    return CameraPath(mast=tuple(mast), aim_xy=aim, hfov_deg=hfov, footprint=footprint)


def in_view(path: CameraPath, t: int, xy: np.ndarray) -> np.ndarray:
    xy = np.asarray(xy, dtype=float).reshape(-1, 2)
    known = ~np.isnan(xy).any(axis=1)
    out = np.zeros(len(xy), dtype=bool)
    if known.any():
        out[known] = shapely.contains_xy(path.footprint[t], xy[known, 0], xy[known, 1])
    return out
