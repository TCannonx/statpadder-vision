"""Builds the match's .sptrack file from the stages before it."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from spv.job import Job
from spv.lineup import load_lineup, slot_occupancy
from spv.pipeline import file_identity
from spv.sptrack import State, blank_track, write_sptrack

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
        track = blank_track(n, job.rate, job.pitch or DEFAULT_PITCH,
                            pitch_source="job" if job.pitch else "default",
                            teams={"home": lineup.home.name, "away": lineup.away.name})
        off_pitch = ~slot_occupancy(lineup, np.arange(n) / job.rate)
        track.positions["state"][off_pitch] = State.NOT_ON_PITCH
        track.manifest.substitutions = [
            {"type": e.type, "team": e.team, "time_s": e.time_s, "off": e.off, "on": e.on}
            for e in lineup.events if e.type == "sub"]
        write_sptrack(out_dir / "match.sptrack", track)
