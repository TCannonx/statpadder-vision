"""Full-pitch truth for the simulator: public tracking data in spv's pitch coordinates."""

from __future__ import annotations

import csv
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import numpy as np

METRICA_PITCH = (105.0, 68.0)
METRICA_URL = ("https://raw.githubusercontent.com/metrica-sports/sample-data/master/data/"
               "Sample_Game_{game}/Sample_Game_{game}_RawTrackingData_{side}_Team.csv")


@dataclass
class PitchTracks:
    rate: float
    pitch: tuple[float, float]
    times_s: np.ndarray
    ids: list[str]
    teams: list[str]
    xy: np.ndarray
    ball_xy: np.ndarray


def resample(times: np.ndarray, values: np.ndarray, grid: np.ndarray) -> np.ndarray:
    """Linear interpolation along axis 0 that never bridges a NaN neighbour."""
    j = np.clip(np.searchsorted(times, grid, side="right") - 1, 0, len(times) - 2)
    w = (grid - times[j]) / (times[j + 1] - times[j])
    w = w.reshape((-1,) + (1,) * (values.ndim - 1))
    left, right = values[j], values[j + 1]
    out = left * (1 - w) + right * w
    out = np.where(w < 1e-9, left, out)
    return np.where(w > 1 - 1e-9, right, out)


def _read_metrica(path: Path) -> tuple[np.ndarray, list[str], np.ndarray, np.ndarray]:
    with open(path, newline="") as f:
        reader = csv.reader(f)
        team, numbers, names = next(reader), next(reader), next(reader)
    data = np.loadtxt(path, delimiter=",", skiprows=3, dtype=float)
    columns = [i for i, name in enumerate(names) if name.startswith("Player")]
    side = next(t for t in team if t).lower()
    ids = [f"{side}_p{names[i][len('Player'):].strip()}" for i in columns]
    xy = np.stack([data[:, [i, i + 1]] for i in columns], axis=1)
    ball = data[:, [names.index("Ball"), names.index("Ball") + 1]]
    return data[:, 2], ids, xy, ball


def _to_pitch(uv: np.ndarray) -> np.ndarray:
    length, width = METRICA_PITCH
    return np.stack([uv[..., 0] * length, (1 - uv[..., 1]) * width], axis=-1)


def load_metrica(home_csv: Path, away_csv: Path, rate: float = 10.0) -> PitchTracks:
    t, home_ids, home_xy, ball = _read_metrica(home_csv)
    t_away, away_ids, away_xy, _ = _read_metrica(away_csv)
    if len(t) != len(t_away) or not np.allclose(t, t_away):
        raise ValueError("home and away files have different frames")
    grid = np.arange(np.ceil(t[0] * rate - 1e-9), np.floor(t[-1] * rate + 1e-9) + 1) / rate
    xy = resample(t, _to_pitch(np.concatenate([home_xy, away_xy], axis=1)), grid)
    ids = home_ids + away_ids
    return PitchTracks(rate=rate, pitch=METRICA_PITCH, times_s=grid, ids=ids,
                       teams=[i.split("_")[0] for i in ids], xy=xy,
                       ball_xy=resample(t, _to_pitch(ball), grid))


def ensure_metrica(game: int, data_dir: Path) -> tuple[Path, Path]:
    folder = Path(data_dir) / "metrica"
    folder.mkdir(parents=True, exist_ok=True)
    paths = []
    for side in ("Home", "Away"):
        url = METRICA_URL.format(game=game, side=side)
        path = folder / url.rsplit("/", 1)[1]
        if not path.exists():
            part = path.with_suffix(".part")
            with urllib.request.urlopen(url) as response, open(part, "wb") as out:
                while chunk := response.read(1 << 20):
                    out.write(chunk)
            part.replace(path)
        paths.append(path)
    return paths[0], paths[1]
