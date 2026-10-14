"""Reads the video's duration, frame rate and size with ffprobe."""

from __future__ import annotations

import json
import shutil
import subprocess
from fractions import Fraction
from pathlib import Path

from spv.job import Job
from spv.pipeline import file_identity


def probe_video(path: Path) -> dict:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"video not found: {path}")
    if shutil.which("ffprobe") is None:
        raise RuntimeError("ffprobe not found: install ffmpeg")
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height,avg_frame_rate:format=duration", "-of", "json", str(path)],
        capture_output=True, text=True, check=True).stdout
    data = json.loads(out)
    stream = data["streams"][0]
    return {"duration_s": float(data["format"]["duration"]), "fps": float(Fraction(stream["avg_frame_rate"])),
            "width": int(stream["width"]), "height": int(stream["height"])}


class ProbeStage:
    name = "probe"
    version = "1"
    depends_on: tuple[str, ...] = ()

    def inputs(self, job: Job) -> dict:
        if not job.video.is_file():
            raise FileNotFoundError(f"video not found: {job.video}")
        return {"video": file_identity(job.video)}

    def run(self, job: Job, upstream: dict[str, Path], out_dir: Path) -> None:
        (out_dir / "probe.json").write_text(json.dumps(probe_video(job.video)))
