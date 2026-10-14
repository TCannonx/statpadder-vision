import json

import pytest

from spv.check.suites import add_clip, clips_suite
from spv.config import load_local_config


def test_clip_add_writes_config_and_metadata(tiny_video, tmp_path):
    add_clip("x", tiny_video, tmp_path)
    assert load_local_config(tmp_path)["clips"]["x"] == str(tiny_video)
    meta_text = (tmp_path / "tests" / "clips" / "x.json").read_text()
    meta = json.loads(meta_text)
    assert "path" not in meta and str(tiny_video.parent.name) not in meta_text
    assert meta["duration_s"] == pytest.approx(3.0, abs=0.1) and meta["fps"] == 25.0
    lineup = json.loads((tmp_path / "tests" / "clips" / "x.lineup.json").read_text())
    assert sum(p["starter"] for p in lineup["home"]["players"]) == 11
    assert all("name" not in p for p in lineup["home"]["players"])


def test_clips_suite_none_without_config(tmp_path):
    assert clips_suite(tmp_path) is None


def test_clips_suite_runtime_measure(tiny_video, tmp_path):
    add_clip("x", tiny_video, tmp_path)
    measures = clips_suite(tmp_path)
    assert [m.name for m in measures] == ["clip.x.runtime_s_per_video_min"]
    assert measures[0].better == "lower" and measures[0].relative


def test_clips_suite_detects_changed_file(tiny_video, tmp_path):
    clip = tmp_path / "copy.mp4"
    clip.write_bytes(tiny_video.read_bytes())
    add_clip("x", clip, tmp_path)
    with open(clip, "ab") as f:
        f.write(b"extra")
    with pytest.raises(RuntimeError, match="changed"):
        clips_suite(tmp_path)
