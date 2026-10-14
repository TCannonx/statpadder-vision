from dataclasses import replace
from pathlib import Path

import pytest

from spv.cache import RunCache
from spv.job import Job
from spv.pipeline import file_identity, run_pipeline


class FakeStage:
    def __init__(self, name, depends_on=(), reads=lambda job: {}, version="1"):
        self.name, self.depends_on, self.reads, self.version = name, tuple(depends_on), reads, version
        self.runs = 0
        self.fail = False

    def inputs(self, job):
        return self.reads(job)

    def run(self, job, upstream, out_dir):
        self.runs += 1
        (out_dir / "partial.txt").write_text("partial")
        if self.fail:
            raise RuntimeError("boom")
        (out_dir / "out.txt").write_text(f"{self.name} from {sorted(upstream)}")


@pytest.fixture
def job(tmp_path):
    return Job(video=tmp_path / "v.mp4", lineup=tmp_path / "l.json", output=tmp_path / "o.sptrack",
               cache_dir=tmp_path / "cache", pitch=None, rate=10.0, options={})


def stages():
    a = FakeStage("A", reads=lambda job: {"pitch": job.pitch})
    b = FakeStage("B", depends_on=["A"], reads=lambda job: {"rate": job.rate})
    return a, b


def statuses(report):
    return [s.status for s in report.stages]


def test_second_run_is_cached(job):
    a, b = stages()
    run_pipeline(job, [a, b], RunCache(job.cache_dir))
    report = run_pipeline(job, [a, b], RunCache(job.cache_dir))
    assert statuses(report) == ["cached", "cached"]
    assert (a.runs, b.runs) == (1, 1)


def test_changed_input_reruns_dependents(job):
    a, b = stages()
    run_pipeline(job, [a, b], RunCache(job.cache_dir))
    report = run_pipeline(replace(job, pitch=(100.0, 64.0)), [a, b], RunCache(job.cache_dir))
    assert statuses(report) == ["ran", "ran"]
    report = run_pipeline(replace(job, pitch=(100.0, 64.0), rate=25.0), [a, b], RunCache(job.cache_dir))
    assert statuses(report) == ["cached", "ran"]


def test_version_bump_reruns(job):
    a, b = stages()
    run_pipeline(job, [a, b], RunCache(job.cache_dir))
    b.version = "2"
    assert statuses(run_pipeline(job, [a, b], RunCache(job.cache_dir))) == ["cached", "ran"]


def test_crash_mid_stage_is_redone(job):
    a, b = stages()
    b.fail = True
    with pytest.raises(RuntimeError, match="boom"):
        run_pipeline(job, [a, b], RunCache(job.cache_dir))
    b.fail = False
    report = run_pipeline(job, [a, b], RunCache(job.cache_dir))
    assert statuses(report) == ["cached", "ran"]
    assert sorted(p.name for p in (job.cache_dir / "B").iterdir()) == ["done.json", "out.txt", "partial.txt"]
    assert not (job.cache_dir / "B.tmp").exists()


def test_failed_stage_never_counts_as_done(job):
    a, b = stages()
    run_pipeline(job, [a, b], RunCache(job.cache_dir))
    b.version, b.fail = "2", True
    with pytest.raises(RuntimeError):
        run_pipeline(job, [a, b], RunCache(job.cache_dir))
    b.fail = False
    assert statuses(run_pipeline(job, [a, b], RunCache(job.cache_dir))) == ["cached", "ran"]


def test_dependency_order_checked(job):
    a, b = stages()
    with pytest.raises(ValueError):
        run_pipeline(job, [b, a], RunCache(job.cache_dir))


def test_file_identity_changes_with_content(tmp_path):
    f = tmp_path / "f.bin"
    f.write_bytes(b"one")
    first = file_identity(f)
    f.write_bytes(b"three")
    assert file_identity(f) != first
