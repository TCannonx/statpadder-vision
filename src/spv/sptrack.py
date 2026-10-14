"""The `.sptrack` tracking file: one zip per match.

Positions are x and y in centimetres (16-bit), an uncertainty in 0.25 m steps (8-bit) and a state.
"""

from __future__ import annotations

import io
import json
import zipfile
from dataclasses import asdict, dataclass
from enum import IntEnum
from pathlib import Path
from typing import Literal

import numpy as np

FORMAT_VERSION = "1.0"
COORDINATE_SYSTEM = ("metres from the near-left corner flag; x along the near touchline; "
                     "y towards the far touchline")
POS_DTYPE = np.dtype([("x", "<i2"), ("y", "<i2"), ("unc", "u1"), ("state", "u1")])
UNC_STEP_M = 0.25


class SptrackError(ValueError):
    pass


class SptrackVersionError(SptrackError):
    pass


class State(IntEnum):
    SEEN = 0
    PREDICTED = 1
    NOT_ON_PITCH = 2
    UNKNOWN = 3


@dataclass
class Manifest:
    format_version: str
    module_version: str
    rate: float
    pitch_length_m: float
    pitch_width_m: float
    pitch_source: Literal["job", "default", "solved"]
    coordinate_system: str
    teams: dict[str, str]
    slots: list[str]
    substitutions: list[dict]
    quality: dict[str, float]
    n_moments: int


@dataclass
class TrackFile:
    manifest: Manifest
    positions: np.ndarray
    ball: np.ndarray
    ball_in_air: np.ndarray
    view: list[np.ndarray]
    pieces: list[dict]
    corrections: list[dict]


def _to_cm(xy_m: np.ndarray) -> np.ndarray:
    cm = np.round(np.asarray(xy_m, dtype=float) * 100)
    if not np.isfinite(cm).all():
        raise SptrackError("a position is NaN or infinite")
    if (cm > 32767).any() or (cm < -32768).any():
        raise SptrackError("position outside the 16-bit centimetre range (about ±327 m)")
    return cm.astype("<i2")


def encode(xy_m: np.ndarray, unc_m: np.ndarray, state: np.ndarray) -> np.ndarray:
    xy_m = np.asarray(xy_m, dtype=float)
    unc_m = np.broadcast_to(np.asarray(unc_m, dtype=float), np.shape(state))
    state = np.asarray(state)
    if ((state < State.SEEN) | (state > State.UNKNOWN)).any():
        raise SptrackError("a state is not one of 0-3 (seen, predicted, not on the pitch, unknown)")
    state = state.astype(np.uint8)
    shown = state <= State.PREDICTED
    if not np.isfinite(xy_m[shown]).all():
        raise SptrackError("a seen or predicted position has no finite x/y")
    if not np.isfinite(unc_m[shown]).all() or (unc_m[shown] < 0).any():
        raise SptrackError("a seen or predicted position has no valid uncertainty")
    xy_m = np.where(shown[..., None], xy_m, 0.0)
    cm = _to_cm(xy_m)
    unc = np.clip(np.round(np.where(shown, unc_m, 0.0) / UNC_STEP_M), 0, 255)
    out = np.zeros(state.shape, dtype=POS_DTYPE)
    out["x"], out["y"] = cm[..., 0], cm[..., 1]
    out["unc"] = np.where(shown, unc, 0).astype(np.uint8)
    out["state"] = state
    return out


def decode(pos: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    state = pos["state"].astype(int)
    xy = np.stack([pos["x"], pos["y"]], axis=-1).astype(float) / 100
    xy[state > State.PREDICTED] = np.nan
    return xy, pos["unc"].astype(float) * UNC_STEP_M, state


def blank_track(n_moments: int, rate: float, pitch: tuple[float, float],
                pitch_source: Literal["job", "default", "solved"] = "default",
                teams: dict[str, str] | None = None) -> TrackFile:
    """Every slot and the ball UNKNOWN: the starting point the stages fill in."""
    from spv import __version__
    from spv.lineup import slot_ids

    n_slots = len(slot_ids())
    manifest = Manifest(
        format_version=FORMAT_VERSION, module_version=__version__, rate=rate,
        pitch_length_m=pitch[0], pitch_width_m=pitch[1], pitch_source=pitch_source,
        coordinate_system=COORDINATE_SYSTEM, teams=teams or {"home": "Home", "away": "Away"},
        slots=slot_ids(), substitutions=[],
        quality={"camera_share": 0.0, "seen_share": 0.0, "mean_uncertainty_m": 0.0}, n_moments=n_moments)
    return TrackFile(
        manifest=manifest,
        positions=encode(np.full((n_moments, n_slots, 2), np.nan), np.zeros((n_moments, n_slots)),
                         np.full((n_moments, n_slots), State.UNKNOWN)),
        ball=encode(np.full((n_moments, 2), np.nan), np.zeros(n_moments), np.full(n_moments, State.UNKNOWN)),
        ball_in_air=np.zeros(n_moments, dtype=bool), view=[np.zeros((0, 2))] * n_moments,
        pieces=[], corrections=[])


def _npy(array: np.ndarray) -> bytes:
    buf = io.BytesIO()
    np.save(buf, array, allow_pickle=False)
    return buf.getvalue()


def write_sptrack(path: Path, track: TrackFile) -> None:
    offsets = np.zeros(len(track.view) + 1, dtype=np.int64)
    offsets[1:] = np.cumsum([len(v) for v in track.view])
    points = (np.concatenate([np.asarray(v, dtype=float).reshape(-1, 2) for v in track.view])
              if track.view else np.zeros((0, 2)))
    view = io.BytesIO()
    np.savez(view, offsets=offsets, points=_to_cm(points))
    members = {
        "manifest.json": json.dumps(asdict(track.manifest), indent=1).encode(),
        "positions.npy": _npy(np.ascontiguousarray(track.positions, dtype=POS_DTYPE)),
        "ball.npy": _npy(np.ascontiguousarray(track.ball, dtype=POS_DTYPE)),
        "ball_in_air.npy": _npy(np.asarray(track.ball_in_air, dtype=bool)),
        "view.npz": view.getvalue(),
        "pieces.json": json.dumps(track.pieces).encode(),
        "corrections.jsonl": "".join(json.dumps(c) + "\n" for c in track.corrections).encode(),
    }
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name, data in members.items():
            z.writestr(name, data)


def read_sptrack(path: Path) -> TrackFile:
    try:
        with zipfile.ZipFile(path) as z:
            raw = {name: z.read(name) for name in z.namelist()}
    except zipfile.BadZipFile as exc:
        raise SptrackError(f"{path}: not a .sptrack file") from exc
    try:
        manifest = Manifest(**json.loads(raw["manifest.json"]))
    except (KeyError, TypeError) as exc:
        raise SptrackError(f"{path}: bad manifest ({exc})") from exc
    if manifest.format_version.split(".")[0] != FORMAT_VERSION.split(".")[0]:
        raise SptrackVersionError(
            f"{path}: format {manifest.format_version}, this spv reads {FORMAT_VERSION.split('.')[0]}.x")

    def npy(name: str) -> np.ndarray:
        return np.load(io.BytesIO(raw[name]), allow_pickle=False)

    view_npz = np.load(io.BytesIO(raw["view.npz"]), allow_pickle=False)
    offsets, points = view_npz["offsets"], view_npz["points"].astype(float) / 100
    view = [points[offsets[i]:offsets[i + 1]] for i in range(len(offsets) - 1)]
    corrections = [json.loads(line) for line in raw["corrections.jsonl"].decode().splitlines() if line]
    return TrackFile(manifest=manifest, positions=npy("positions.npy"), ball=npy("ball.npy"),
                     ball_in_air=npy("ball_in_air.npy"), view=view,
                     pieces=json.loads(raw["pieces.json"]), corrections=corrections)
