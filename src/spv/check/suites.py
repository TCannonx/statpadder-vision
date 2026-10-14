"""The measures `spv check` runs: the simulator suite (CI) and the reference clips suite (local)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np

from spv.check.measures import Measure
from spv.check.score import score_positions, track_from_truth
from spv.sim.camera import simulate_camera
from spv.sim.detections import simulate_detections, visible
from spv.sim.scenes import find_scenes, null_solver
from spv.sim.tracks import ensure_metrica, load_metrica
from spv.sptrack import State, decode, read_sptrack, write_sptrack

SIM_GAME = 2
SIM_SEED = 0


def sim_suite(data_dir: Path) -> list[Measure]:
    truth = load_metrica(*ensure_metrica(SIM_GAME, data_dir))
    camera = simulate_camera(truth)
    detections = simulate_detections(truth, camera, seed=SIM_SEED)
    n = len(truth.times_s)
    track = null_solver(detections, n, truth.rate, truth.pitch)
    ball_known = ~np.isnan(truth.ball_xy[:, 0])
    ball_seen = visible(camera, truth.ball_xy[:, None])[:, 0]

    measures = []
    scenes = find_scenes(truth, camera)
    for scene in scenes:
        score = score_positions(track, truth, scene.start, scene.stop)
        window = slice(scene.start, scene.stop)
        in_view = ball_seen[window][ball_known[window]].mean() if ball_known[window].any() else 0.0
        measures += [
            Measure(f"sim.{scene.name}.within_2m", score["within_2m"], "higher", 0.01),
            Measure(f"sim.{scene.name}.false_players", score["false_players"], "lower", 0.01),
            Measure(f"sim.{scene.name}.ball_in_view", float(in_view), "higher", 0.02),
        ]
    measures.append(Measure("sptrack.roundtrip_max_error_m", _roundtrip_error(truth, scenes[0]), "lower", 0.001))
    return measures


def _sim() -> list[Measure]:
    from spv.config import data_dir

    return sim_suite(data_dir())


SUITES = {"sim": _sim}


def _roundtrip_error(truth, scene) -> float:
    track = track_from_truth(truth, scene.start, scene.stop)
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "truth.sptrack"
        write_sptrack(path, track)
        xy, _, state = decode(read_sptrack(path).positions[scene.start:scene.stop])
    true_xy = truth.xy[scene.start:scene.stop]
    # each written slot against the nearest truth player (players are far more than 1 cm apart)
    diff = np.abs(xy[:, :, None] - true_xy[:, None, :])  # (W, S, P, 2)
    nearest = np.nanargmin(np.where(np.isnan(diff), np.inf, diff).sum(axis=-1), axis=2)
    per_slot = np.take_along_axis(diff, nearest[..., None, None], axis=2)[:, :, 0]
    seen = state == State.SEEN
    if not seen.any():
        raise ValueError("round-trip check wrote no positions")
    return float(per_slot[seen].max())
