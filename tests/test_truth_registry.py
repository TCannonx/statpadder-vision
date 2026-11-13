import pytest

from spv.truth.registry import add_match, inventory, inventory_markdown, registered
from spv.truth.split import choose_holdout, load_split, save_split
from truth_samples import EYEBALL_SAMPLE


def _files(tmp_path):
    video = tmp_path / "v.mp4"
    video.write_bytes(b"not really a video")
    events = tmp_path / "e.csv"
    events.write_text(EYEBALL_SAMPLE, encoding="utf-8-sig")
    return video, events


def test_add_and_inventory(tmp_path):
    video, events = _files(tmp_path)
    add_match("m01", video, events, repo_root=tmp_path)
    assert registered(tmp_path)["m01"] == {"video": str(video.resolve()), "events": str(events.resolve())}
    rows = inventory(tmp_path, probe=lambda p: {"duration_s": 5400.0})
    r = rows[0]
    assert (r["id"], r["source"], r["minutes"], r["rows"], r["timed_share"], r["halves"]) == (
        "m01", "eyeball", 90, 12, 0.917, 2)
    assert r["kinds"]["kick_off"] == 3 and r["kinds"]["corner"] == 1
    assert "| m01 | eyeball | 90 | 12 | 92% | 2 |" in inventory_markdown(rows)


def test_ids_are_anonymous(tmp_path):
    video, events = _files(tmp_path)
    with pytest.raises(ValueError):
        add_match("bohs-u17", video, events, repo_root=tmp_path)


def test_missing_file_is_refused(tmp_path):
    _, events = _files(tmp_path)
    with pytest.raises(FileNotFoundError):
        add_match("m01", tmp_path / "nope.mp4", events, repo_root=tmp_path)


def test_split_is_stable_and_fixed(tmp_path):
    rows = [{"id": f"m{i:02d}", "source": "eyeball", "halves": 2, "timed_share": 1.0} for i in range(1, 11)]
    rows.append({"id": "m11", "source": "statpadder", "halves": 2, "timed_share": 1.0})
    rows.append({"id": "m12", "source": "eyeball", "halves": 1, "timed_share": 1.0})
    holdout = choose_holdout(rows)
    assert len(holdout) == 5 and "m11" not in holdout and "m12" not in holdout
    assert choose_holdout(rows) == holdout
    save_split(holdout, [r["id"] for r in rows], repo_root=tmp_path)
    split = load_split(tmp_path)
    assert split["p0"] == holdout[:3] and len(split["train"]) == 7
    with pytest.raises(FileExistsError):
        save_split(holdout, [r["id"] for r in rows], repo_root=tmp_path)


def test_split_falls_back_to_hand_coded(tmp_path):
    rows = [{"id": "m01", "source": "eyeball", "halves": 2, "timed_share": 1.0},
            {"id": "m02", "source": "statpadder", "halves": 2, "timed_share": 0.99}]
    assert sorted(choose_holdout(rows)) == ["m01", "m02"]
