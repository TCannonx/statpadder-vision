"""The measures `spv check` runs: the simulator suite (CI) and the reference clips suite (local)."""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

import numpy as np

from spv.cache import RunCache
from spv.check.measures import Measure
from spv.config import REPO_ROOT, data_dir, load_local_config, save_local_config
from spv.job import Job
from spv.pipeline import run_pipeline
from spv.stages import default_stages
from spv.stages.probe import probe_video
from spv.check.score import score_positions, track_from_truth
from spv.sim.camera import simulate_camera
from spv.sim.detections import simulate_detections, visible
from spv.sim.scenes import find_scenes, null_solver
from spv.sim.tracks import ensure_metrica, load_metrica
from spv.sptrack import State, decode, read_sptrack, write_sptrack

SIM_GAME = 2
SIM_SEED = 0
HASH_CHUNK = 16 * 1024 * 1024


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


def clip_identity(path: Path) -> dict:
    """Size, a hash of the first and last 16 MB, and the probe fields: never the path."""
    path = Path(path)
    size = path.stat().st_size
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        digest.update(f.read(HASH_CHUNK))
        if size > HASH_CHUNK:
            f.seek(max(size - HASH_CHUNK, HASH_CHUNK))
            digest.update(f.read())
    return {"size": size, "sha256_head_tail": digest.hexdigest(), **probe_video(path)}


def _clips_folder(repo_root: Path) -> Path:
    return Path(repo_root) / "tests" / "clips"


def add_clip(name: str, path: Path, repo_root: Path) -> None:
    config = load_local_config(repo_root)
    config.setdefault("clips", {})[name] = str(path)
    save_local_config(config, repo_root)
    folder = _clips_folder(repo_root)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{name}.json").write_text(json.dumps({"name": name, **clip_identity(path)}, indent=1) + "\n")
    lineup = folder / f"{name}.lineup.json"
    if not lineup.exists():  # generic squads: the clips show minors, so no names
        squads = {side: {"name": side.title(), "players": [
            {"id": f"{side[0]}{i}", "number": None, "starter": True} for i in range(1, 12)]}
            for side in ("home", "away")}
        lineup.write_text(json.dumps({**squads, "events": []}, indent=1) + "\n")


def clips_suite(repo_root: Path) -> list[Measure] | None:
    clips = load_local_config(repo_root).get("clips", {})
    if not clips:
        return None
    measures = []
    for name, path in sorted(clips.items()):
        expected = json.loads((_clips_folder(repo_root) / f"{name}.json").read_text())
        actual = {"name": name, **clip_identity(Path(path))}
        if actual != expected:
            raise RuntimeError(f"reference clip {name} has changed since it was registered; "
                               f"re-register it with `spv clip add` and reset its baselines")
        with tempfile.TemporaryDirectory() as folder:
            job = Job(video=Path(path), lineup=_clips_folder(repo_root) / f"{name}.lineup.json",
                      output=Path(folder) / f"{name}.sptrack", cache_dir=Path(folder) / "cache",
                      pitch=None)
            report = run_pipeline(job, default_stages(), RunCache(job.cache_dir))
        minutes = expected["duration_s"] / 60
        measures.append(Measure(f"clip.{name}.runtime_s_per_video_min", report.total_s / minutes,
                                "lower", 0.5, relative=True))
    return measures


def _sim() -> list[Measure]:
    return sim_suite(data_dir())


def _clips() -> list[Measure] | None:
    return clips_suite(REPO_ROOT)


SUITES = {"sim": _sim, "clips": _clips}


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
