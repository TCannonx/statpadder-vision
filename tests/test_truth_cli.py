import json

import pytest

from spv import config
from spv.cli import main
from truth_samples import EYEBALL_TIMED


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "REPO_ROOT", tmp_path)
    return tmp_path


def test_truth_flow(repo, tiny_video, capsys):
    events = repo / "e.csv"
    events.write_text(EYEBALL_TIMED, encoding="utf-8-sig")
    assert main(["truth", "add", "m01", str(tiny_video), str(events)]) == 0
    assert main(["truth", "add", "team", str(tiny_video), str(events)]) == 1
    assert main(["truth", "inventory"]) == 0
    assert "| m01 | eyeball |" in (repo / "tests/truth/inventory.md").read_text(encoding="utf-8")
    assert main(["truth", "split"]) == 0
    assert json.loads((repo / "tests/truth/split.json").read_text())["p0"] == ["m01"]
    assert main(["truth", "split"]) == 1  # fixed once made

    capsys.readouterr()
    assert main(["truth", "events", "m01", "--kind", "corner"]) == 0
    listed = capsys.readouterr().out.strip().splitlines()
    assert len(listed) == 1 and listed[0].startswith("3\t")

    assert main(["truth", "sheet", "m01", "--row", "1", "--base", "-29", "--around=-0.5:0.5:0.5"]) == 0
    assert len(list((repo / "runs/truth/m01").glob("*.png"))) == 1
    assert main(["truth", "mark", "m01", "--row", "1", "--offset", "-29"]) == 0
    assert main(["truth", "mark", "m01", "--row", "99", "--offset", "0"]) == 1
    assert main(["truth", "kit", "m01", "--team", "A", "--looks", "white shirts"]) == 0
    assert main(["truth", "attack", "m01", "--row", "4", "--goal", "right"]) == 0
    align = json.loads((repo / "tests/truth/align/m01.json").read_text())
    assert align["marks"][0]["offset_s"] == -29.0 and align["kits"] == {"A": "white shirts"}

    assert main(["truth", "spots", "m01"]) == 1  # half 2 has no offset yet
    assert main(["truth", "mark", "m01", "--row", "9", "--offset", "-2999"]) == 0
    assert main(["truth", "spots", "m01"]) == 0
    spot = json.loads((repo / "tests/truth/spot/m01.json").read_text())
    assert spot["rows"] and (repo / f"runs/truth/m01/spot_row{spot['rows'][0]}.png").exists()
    row = spot["rows"][0]
    assert main(["truth", "spot", "m01", "--row", row, "--moment", "ok", "--kind", "ok",
                 "--place", "unsure", "--team", "ok"]) == 0

    # the made-up file is so short that the sample takes every fallback row; free one, then the corner is not
    # visible on camera and is replaced by a row that can be judged
    sample_file = repo / "tests/truth/spot/m01.json"
    short = json.loads(sample_file.read_text())
    short["rows"].remove("8")
    sample_file.write_text(json.dumps(short), encoding="utf-8")
    (repo / "runs/truth/m01/spot_row8.png").unlink()
    assert main(["truth", "spot", "m01", "--row", "3", "--moment", "unseen", "--kind", "ok",
                 "--place", "ok", "--team", "ok"]) == 0
    assert main(["truth", "spots", "m01"]) == 0
    capsys.readouterr()
    spot = json.loads((repo / "tests/truth/spot/m01.json").read_text())
    assert len(spot["rows"]) == 6 and spot["rows"][-1] == "8"
    assert (repo / "runs/truth/m01/spot_row8.png").exists()
    assert main(["truth", "spots", "m01"]) == 0
    assert "no rows to add" in capsys.readouterr().out

    report = repo / "tests/truth/p0_report.md"
    report.write_text("# old\n\n## Notes\n\nKept by hand.\n", encoding="utf-8")
    assert main(["truth", "report"]) == 1  # far from done: STOP
    text = report.read_text(encoding="utf-8")
    assert "**Verdict:** STOP" in text and text.endswith("\n\n## Notes\n\nKept by hand.\n")
    assert "# old" not in text
    assert main(["truth", "untestable", "m01", "--reason", "camera too far"]) == 0
    stored = repo / "tests/truth/untestable.json"
    assert json.loads(stored.read_text()) == {"m01": "camera too far"}
    assert main(["truth", "untestable", "m09", "--reason", "x"]) == 1  # not registered
    assert main(["truth", "report"]) == 1  # nothing testable left: STOP
    text = report.read_text(encoding="utf-8")
    assert "not testable: camera too far" in text and "excluded from the verdict" in text


def test_untestable_rejects_a_match_outside_p0(repo, tiny_video):
    events = repo / "e.csv"
    events.write_text(EYEBALL_TIMED, encoding="utf-8-sig")
    assert main(["truth", "add", "m01", str(tiny_video), str(events)]) == 0
    for m in ("m02", "m03", "m04"):
        assert main(["truth", "add", m, str(tiny_video), str(events)]) == 0
    assert main(["truth", "split"]) == 0
    p0 = json.loads((repo / "tests/truth/split.json").read_text())["p0"]
    other = next(m for m in ("m01", "m02", "m03", "m04") if m not in p0)
    assert main(["truth", "untestable", other, "--reason", "x"]) == 1
    assert not (repo / "tests/truth/untestable.json").exists()


def test_untestable_needs_a_reason(repo, tiny_video, capsys):
    events = repo / "e.csv"
    events.write_text(EYEBALL_TIMED, encoding="utf-8-sig")
    assert main(["truth", "add", "m01", str(tiny_video), str(events)]) == 0
    assert main(["truth", "split"]) == 0
    assert main(["truth", "untestable", "m01", "--reason", "  "]) == 1
    assert "reason" in capsys.readouterr().err
    assert not (repo / "tests/truth/untestable.json").exists()


def test_truth_score(repo, tiny_video, capsys):
    events = repo / "e.csv"
    events.write_text(EYEBALL_TIMED, encoding="utf-8-sig")
    assert main(["truth", "add", "m01", str(tiny_video), str(events)]) == 0
    capsys.readouterr()
    assert main(["truth", "score", "m01", str(events), "--label", "self"]) == 1  # no offsets saved
    assert "half 1" in capsys.readouterr().err
    assert not (repo / "tests/truth/score/m01-self.json").exists()
    assert main(["truth", "score", "m01", str(events), "--label", "self", "--assume-zero-offset"]) == 0
    out = capsys.readouterr().out
    assert "PASS" in out
    for line in out.splitlines():
        if line.startswith("| ") and line.endswith("| FAIL |"):
            assert "n/a (no events)" in line  # only groups with no events fail
        if line.startswith(("| goal recall", "| shot recall", "| shot precision", "| team", "| zone")):
            assert line.endswith("| PASS |"), line
    result = json.loads((repo / "tests/truth/score/m01-self.json").read_text())
    assert result["team_mapping"] == "by name" and "e.csv" not in json.dumps(result)
    assert (repo / "tests/truth/score/m01-self.md").exists()
    assert main(["truth", "score", "m01", str(events), "--label", "Bad Label"]) == 1
    assert main(["truth", "score", "m09", str(events), "--label", "self"]) == 1
    assert main(["truth", "score-pool", "--label", "none"]) == 1
    (repo / "tests/truth/score/m01-pre-self.json").write_text("not json", encoding="utf-8")
    assert main(["truth", "score-pool", "--label", "self"]) == 0
    assert (repo / "tests/truth/score/pool-self.md").exists()


def test_truth_score_applies_saved_offsets(repo, tiny_video, capsys):
    from spv.truth.align import add_mark, save_alignment

    events = repo / "e.csv"
    events.write_text(EYEBALL_TIMED, encoding="utf-8-sig")
    assert main(["truth", "add", "m01", str(tiny_video), str(events)]) == 0
    save_alignment("m01", {"marks": [], "kits": {}, "attack_marks": []}, repo)
    data = {"marks": [], "kits": {}, "attack_marks": []}
    add_mark(data, 1, "4", "shot", 0.0)  # a real 0.0 offset counts as aligned
    add_mark(data, 2, "10", "shot", 30.0)
    save_alignment("m01", data, repo)
    shifted = repo / "shifted.csv"
    shifted.write_text(EYEBALL_TIMED.replace(";3100.0;", ";3130.0;"), encoding="utf-8-sig")

    def shot_matches(pred, label):
        assert main(["truth", "score", "m01", str(pred), "--label", label]) == 0
        result = json.loads((repo / f"tests/truth/score/m01-{label}.json").read_text())
        return result["at_5s"]["shot"]["matched"], result["at_5s"]["shot"]["truth"]

    assert shot_matches(shifted, "shifted") == (2, 2)
    assert shot_matches(events, "plain") == (1, 2)


def test_truth_score_halves_teams_and_refusal(repo, tiny_video, capsys):
    events = repo / "e.csv"
    events.write_text(EYEBALL_TIMED, encoding="utf-8-sig")
    assert main(["truth", "add", "m01", str(tiny_video), str(events)]) == 0
    capsys.readouterr()
    base = ["truth", "score", "m01", str(events), "--assume-zero-offset"]
    assert main(base + ["--label", "h2", "--half", "2"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("pred: ") and "events read" in out and "halves scored: 2" in out
    assert json.loads((repo / "tests/truth/score/m01-h2.json").read_text())["halves"] == [2]
    assert main(base + ["--label", "sw", "--teams", "swapped"]) == 0
    result = json.loads((repo / "tests/truth/score/m01-sw.json").read_text())
    assert result["team_mapping"] == "given" and result["accuracy"]["team_right"] == 0
    assert main(base + ["--label", "sa", "--teams", "same"]) == 0
    assert json.loads((repo / "tests/truth/score/m01-sa.json").read_text())["accuracy"]["team_right"] > 0
    empty = repo / "empty.csv"
    empty.write_text(EYEBALL_TIMED.splitlines()[0] + "\n", encoding="utf-8-sig")
    capsys.readouterr()
    assert main(["truth", "score", "m01", str(empty), "--label", "none", "--assume-zero-offset"]) == 1
    assert "bar group" in capsys.readouterr().err
