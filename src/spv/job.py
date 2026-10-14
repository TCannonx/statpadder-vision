"""The job file: what `spv process` is asked to do."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


class JobError(ValueError):
    pass


@dataclass(frozen=True)
class Job:
    video: Path
    lineup: Path
    output: Path
    cache_dir: Path
    pitch: tuple[float, float] | None
    rate: float = 10.0
    options: dict = field(default_factory=dict)


def load_job(path: Path) -> Job:
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise JobError(f"job {path}: not valid JSON ({exc})") from exc
    base = path.parent

    def resolve(key: str) -> Path:
        if key not in data:
            raise JobError(f"job {path}: missing field {key!r}")
        return (base / data[key]).resolve() if not Path(data[key]).is_absolute() else Path(data[key])

    output = resolve("output")
    cache_dir = resolve("cache_dir") if "cache_dir" in data else output.parent / (output.stem + ".spv-cache")
    pitch = data.get("pitch")
    if pitch is not None:
        try:
            pitch = (float(pitch["length_m"]), float(pitch["width_m"]))
        except (KeyError, TypeError) as exc:
            raise JobError(f"job {path}: pitch needs length_m and width_m") from exc
    return Job(video=resolve("video"), lineup=resolve("lineup"), output=output, cache_dir=cache_dir,
               pitch=pitch, rate=float(data.get("rate", 10)), options=dict(data.get("options", {})))
