"""Builds the match's .sptrack file from the stages before it."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from spv import __version__
from spv.job import Job
from spv.lineup import load_lineup, slot_ids, slot_occupancy
from spv.pipeline import file_identity
from spv.sptrack import (COORDINATE_SYSTEM, FORMAT_VERSION, Manifest, State, TrackFile, encode,
                         write_sptrack)

DEFAULT_PITCH = (105.0, 68.0)


def moment_count(duration_s: float, rate: float) -> int:
    return max(0, math.ceil(duration_s * rate - 1e-9))


class ExportStage:
    name = "export"
    version = "1"
    depends_on = ("probe",)

    def inputs(self, job: Job) -> dict:
        return {"lineup": file_identity(job.lineup), "pitch": job.pitch, "rate": job.rate}

    def run(self, job: Job, upstream: dict[str, Path], out_dir: Path) -> None:
        probe = json.loads((upstream["probe"] / "probe.json").read_text())
        lineup = load_lineup(job.lineup)
        n = moment_count(probe["duration_s"], job.rate)
        times = np.arange(n) / job.rate
        occupied = slot_occupancy(lineup, times)
        state = np.where(occupied, State.UNKNOWN, State.NOT_ON_PITCH)
        positions = encode(np.full((n, 22, 2), np.nan), np.zeros((n, 22)), state)
        ball = encode(np.full((n, 2), np.nan), np.zeros(n), np.full(n, State.UNKNOWN))
        length, width = job.pitch or DEFAULT_PITCH
        manifest = Manifest(
            format_version=FORMAT_VERSION, module_version=__version__, rate=job.rate,
            pitch_length_m=length, pitch_width_m=width,
            pitch_source="job" if job.pitch else "default", coordinate_system=COORDINATE_SYSTEM,
            teams={"home": lineup.home.name, "away": lineup.away.name}, slots=slot_ids(),
            substitutions=[{"type": e.type, "team": e.team, "time_s": e.time_s, "off": e.off, "on": e.on}
                           for e in lineup.events if e.type == "sub"],
            quality={"camera_share": 0.0, "seen_share": 0.0, "mean_uncertainty_m": 0.0},
            n_moments=n)
        write_sptrack(out_dir / "match.sptrack", TrackFile(
            manifest=manifest, positions=positions, ball=ball, ball_in_air=np.zeros(n, dtype=bool),
            view=[np.zeros((0, 2))] * n, pieces=[], corrections=[]))
