from collections import Counter

import pytest

from spv.truth.events import TruthEvent
from spv.truth.spot import load_spot, record_verdict, sample_spot_rows, save_spot, spot_score


def _events(kinds):
    return [TruthEvent(str(i), 1 if i < len(kinds) // 2 else 2, float(i * 10), k, "A", 0.5, 0.5)
            for i, k in enumerate(kinds)]


def test_sample_meets_the_targets():
    events = _events(["goal"] * 2 + ["shot"] * 12 + ["corner"] * 10 + ["free_kick"] * 6
                     + ["goal_kick"] * 8 + ["throw_in"] * 30 + ["kick_off"] * 3)
    rows = sample_spot_rows(events)
    kinds = Counter(e.kind for e in events if e.row_id in rows)
    assert len(rows) == 20 == len(set(rows))
    assert kinds["goal"] == 2 and kinds["corner"] >= 4 and kinds["kick_off"] == 1
    assert sample_spot_rows(events) == rows


def test_short_file_gives_what_it_has():
    events = _events(["shot", "corner", "goal"])
    assert sorted(sample_spot_rows(events)) == ["0", "1", "2"]


def test_verdicts_and_score(tmp_path):
    d = {"rows": ["1", "2", "3"], "verdicts": {}}
    record_verdict(d, "1", moment="ok", kind="ok", place="unsure", team="ok")
    record_verdict(d, "2", moment="off", kind="ok", place="ok", team="ok")
    assert spot_score(d) == (1, 2, 3)
    with pytest.raises(ValueError):
        record_verdict(d, "9", moment="ok", kind="ok", place="ok", team="ok")
    with pytest.raises(ValueError):
        record_verdict(d, "3", moment="maybe", kind="ok", place="ok", team="ok")
    save_spot("m01", d, tmp_path)
    assert load_spot("m01", tmp_path) == d
    assert load_spot("m02", tmp_path) == {"rows": [], "verdicts": {}}
