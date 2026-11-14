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
