"""Runs stages in order through the cache, so a run can resume after a stop."""

from __future__ import annotations

import hashlib
import json
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal, Protocol

from spv.cache import RunCache
from spv.job import Job


class Stage(Protocol):
    name: str
    version: str
    depends_on: tuple[str, ...]

    def inputs(self, job: Job) -> dict: ...

    def run(self, job: Job, upstream: dict[str, Path], out_dir: Path) -> None: ...


@dataclass
class StageResult:
    name: str
    status: Literal["ran", "cached"]
    seconds: float


@dataclass
class RunReport:
    stages: list[StageResult] = field(default_factory=list)
    total_s: float = 0.0

    def to_json(self) -> dict:
        return asdict(self)


def file_identity(path: Path) -> dict:
    path = Path(path)
    st = path.stat()
    return {"path": str(path.resolve()), "size": st.st_size, "mtime_ns": st.st_mtime_ns}


def fingerprint(stage: Stage, job: Job, upstream_fps: dict[str, str]) -> str:
    payload = {"name": stage.name, "version": stage.version, "inputs": stage.inputs(job),
               "upstream": upstream_fps}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def run_pipeline(job: Job, stages: list[Stage], cache: RunCache) -> RunReport:
    seen: set[str] = set()
    for stage in stages:
        missing = [d for d in stage.depends_on if d not in seen]
        if missing:
            raise ValueError(f"stage {stage.name} depends on {missing}, which must come earlier")
        seen.add(stage.name)

    report = RunReport()
    start = time.perf_counter()
    fps: dict[str, str] = {}
    dirs: dict[str, Path] = {}
    for stage in stages:
        t0 = time.perf_counter()
        fp = fingerprint(stage, job, {d: fps[d] for d in stage.depends_on})
        found = cache.lookup(stage.name, fp)
        if found is not None:
            dirs[stage.name], status = found, "cached"
        else:
            out = cache.begin(stage.name)
            stage.run(job, {d: dirs[d] for d in stage.depends_on}, out)
            dirs[stage.name], status = cache.commit(stage.name, fp), "ran"
        fps[stage.name] = fp
        seconds = time.perf_counter() - t0
        report.stages.append(StageResult(stage.name, status, seconds))
        print(f"{stage.name}: {status}" + (f" in {seconds:.1f} s" if status == "ran" else ""),
              file=sys.stderr)
    report.total_s = time.perf_counter() - start
    return report
