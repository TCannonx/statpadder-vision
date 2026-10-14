import json

import pytest

from spv.job import JobError, load_job


def _write(tmp_path, data):
    path = tmp_path / "job.json"
    path.write_text(json.dumps(data))
    return path


JOB = {"video": "clip1.mp4", "lineup": "lineup.json", "output": "out/clip1.sptrack",
       "pitch": {"length_m": 100, "width_m": 64}, "rate": 10, "options": {}}


def test_job_resolves_relative_paths(tmp_path):
    job = load_job(_write(tmp_path, JOB))
    assert job.video == tmp_path / "clip1.mp4"
    assert job.lineup == tmp_path / "lineup.json"
    assert job.output == tmp_path / "out" / "clip1.sptrack"
    assert job.cache_dir == tmp_path / "out" / "clip1.spv-cache"
    assert job.pitch == (100.0, 64.0)
    assert job.rate == 10.0


def test_job_missing_video_field(tmp_path):
    data = {k: v for k, v in JOB.items() if k != "video"}
    with pytest.raises(JobError, match="video"):
        load_job(_write(tmp_path, data))


def test_job_pitch_optional(tmp_path):
    data = {k: v for k, v in JOB.items() if k != "pitch"}
    assert load_job(_write(tmp_path, data)).pitch is None
