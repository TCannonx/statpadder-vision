import json
import shutil

import pytest

from spv.cli import main
from spv.sptrack import State, read_sptrack

from conftest import FIXTURES


def make_job(tmp_path, video, lineup="lineup_11.json", **extra):
    shutil.copy(FIXTURES / lineup, tmp_path / "lineup.json")
    job = {"video": str(video), "lineup": "lineup.json", "output": "out/match.sptrack", **extra}
    (tmp_path / "job.json").write_text(json.dumps(job))
    return tmp_path / "job.json"


def process(job_path):
    return main(["process", "--job", str(job_path)])


def report(tmp_path):
    return json.loads((tmp_path / "out" / "match.run_report.json").read_text())


def test_process_writes_unknown_track(tiny_video, tmp_path):
    assert process(make_job(tmp_path, tiny_video)) == 0
    track = read_sptrack(tmp_path / "out" / "match.sptrack")
    m = track.manifest
    assert m.n_moments == 30 and track.positions.shape == (30, 22)
    assert (track.positions["state"] == State.UNKNOWN).all()
    assert (track.ball["state"] == State.UNKNOWN).all()
    assert m.pitch_source == "default" and (m.pitch_length_m, m.pitch_width_m) == (105.0, 68.0)
    assert m.substitutions == [{"type": "sub", "team": "home", "time_s": 50.0, "off": "h4", "on": "h12"}]
    assert [s["name"] for s in report(tmp_path)["stages"]] == ["probe", "export"]


def test_nine_a_side_red_card(tiny_video, tmp_path):
    data = json.loads((FIXTURES / "lineup_9_red.json").read_text())
    data["events"][0]["time_s"] = 1.0
    (tmp_path / "nine.json").write_text(json.dumps(data))
    job = {"video": str(tiny_video), "lineup": "nine.json", "output": "out/match.sptrack"}
    (tmp_path / "job.json").write_text(json.dumps(job))
    assert process(tmp_path / "job.json") == 0
    track = read_sptrack(tmp_path / "out" / "match.sptrack")
    slots = track.manifest.slots
    state = lambda t, slot: track.positions["state"][t, slots.index(slot)]
    for slot in ["home_10", "home_11", "away_10", "away_11"]:
        assert state(0, slot) == State.NOT_ON_PITCH
    assert state(0, "away_09") == State.UNKNOWN
    assert state(10, "away_09") == State.NOT_ON_PITCH
    assert state(10, "away_08") == State.UNKNOWN


def test_rerun_is_cached(tiny_video, tmp_path):
    job = make_job(tmp_path, tiny_video)
    assert process(job) == 0 and process(job) == 0
    assert [s["status"] for s in report(tmp_path)["stages"]] == ["cached", "cached"]


def test_pitch_change_reruns_export_only(tiny_video, tmp_path):
    assert process(make_job(tmp_path, tiny_video)) == 0
    assert process(make_job(tmp_path, tiny_video, pitch={"length_m": 100, "width_m": 64})) == 0
    assert [s["status"] for s in report(tmp_path)["stages"]] == ["cached", "ran"]
    m = read_sptrack(tmp_path / "out" / "match.sptrack").manifest
    assert m.pitch_source == "job" and (m.pitch_length_m, m.pitch_width_m) == (100.0, 64.0)


def test_missing_video_message(tmp_path, capsys):
    video = tmp_path / "no such video.mp4"
    assert process(make_job(tmp_path, video)) == 1
    assert str(video) in capsys.readouterr().err
