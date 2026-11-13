"""Frames and contact sheets from a match video, for checking events by eye.

Sheets show minors: they go to runs/ (git-ignored) and are never committed.
"""

from __future__ import annotations

import io
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

LABEL_BAND = 22


def offsets(spec: str) -> list[float]:
    parts = spec.split(":")
    if len(parts) != 3:
        raise ValueError("offsets are from:to:step, for example -3:3:0.5")
    start, stop, step = (float(p) for p in parts)
    if step <= 0 or stop < start:
        raise ValueError("offsets need a positive step and from <= to")
    n = round((stop - start) / step)
    return [round(start + i * step, 3) + 0.0 for i in range(n + 1)]


def clock(t_s: float) -> str:
    t_s = max(t_s, 0.0)
    hours, rest = divmod(t_s, 3600)
    minutes, seconds = divmod(rest, 60)
    return f"{int(hours)}:{int(minutes):02d}:{seconds:04.1f}"


def grab_frame(video: Path, t_s: float, width: int = 480) -> Image.Image:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found: install ffmpeg")
    out = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", f"{max(t_s, 0.0):.3f}", "-i", str(video), "-frames:v", "1",
         "-vf", f"scale={width}:-2", "-f", "image2pipe", "-vcodec", "png", "-"],
        capture_output=True, check=True).stdout
    if not out:
        raise ValueError(f"no frame at {t_s:.1f} s")
    return Image.open(io.BytesIO(out)).convert("RGB")


def contact_sheet(video: Path, times: list[float], labels: list[str], out: Path,
                  columns: int = 4, width: int = 480) -> Path:
    if not times or len(times) != len(labels):
        raise ValueError("one label per time, and at least one time")
    frames: list[Image.Image | None] = []
    for t in times:
        try:
            frames.append(grab_frame(video, t, width))
        except (ValueError, subprocess.CalledProcessError):
            frames.append(None)
    tile_w, tile_h = next((f.size for f in frames if f is not None), (width, width * 9 // 16))
    cols = min(columns, len(frames))
    rows = -(-len(frames) // cols)
    sheet = Image.new("RGB", (cols * tile_w, rows * (tile_h + LABEL_BAND)), "black")
    draw = ImageDraw.Draw(sheet)
    for i, (frame, label) in enumerate(zip(frames, labels)):
        x, y = (i % cols) * tile_w, (i // cols) * (tile_h + LABEL_BAND)
        sheet.paste(frame if frame is not None else Image.new("RGB", (tile_w, tile_h), "grey"), (x, y + LABEL_BAND))
        draw.text((x + 4, y + 4), label if frame is not None else f"{label} (no frame)", fill="white")
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    return out
