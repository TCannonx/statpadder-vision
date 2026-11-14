from collections import Counter

import pytest

from spv.truth.events import TruthEvent
from spv.truth.spot import (judged_rows, load_spot, record_verdict, sample_spot_rows, save_spot, spot_score,
                            top_up)


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


def test_unseen_is_accepted_and_ignored_by_the_score():
    d = {"rows": ["1", "2", "3"], "verdicts": {}}
    record_verdict(d, "1", moment="ok", kind="ok", place="ok", team="ok")
    record_verdict(d, "2", moment="unseen", kind="ok", place="unsure", team="ok")
    record_verdict(d, "3", moment="off", kind="ok", place="ok", team="ok")
    assert judged_rows(d) == ["1", "3"]
    assert spot_score(d) == (1, 2, 2)
    with pytest.raises(ValueError):
        record_verdict(d, "3", moment="unseen", kind="maybe", place="ok", team="ok")
    with pytest.raises(ValueError):
        record_verdict(d, "3", moment="gone", kind="ok", place="ok", team="ok")


def _unseen(rows, *unseen):
    d = {"rows": list(rows), "verdicts": {}}
    for r in unseen:
        record_verdict(d, r, moment="unseen", kind="ok", place="ok", team="ok")
    return d


def test_top_up_prefers_same_kind_nearest_in_time():
    events = _events(["corner", "corner", "shot", "corner", "corner", "goal"])
    d = _unseen(["1"], "1")
    assert top_up(d, events, n=1) == ["0"]
    assert d["rows"] == ["1", "0"]
    assert top_up(_unseen(["1"], "1"), events, exclude={"0"}, n=1) == ["3"]


def test_top_up_falls_back_to_another_kind():
    events = _events(["corner", "goal", "throw_in", "kick_off"])
    assert top_up(_unseen(["0"], "0"), events, n=1) == ["2"]  # goal and kick_off are no fallback
    assert top_up(_unseen(["0", "2"], "0"), events, n=2) == []


def test_top_up_is_deterministic_and_idle_without_unseen():
    events = _events(["corner"] * 6)
    assert top_up({"rows": ["0", "1"], "verdicts": {}}, events) == []
    assert top_up(_unseen(["2", "3"], "2", "3"), events) == top_up(_unseen(["2", "3"], "2", "3"), events)
    assert len(top_up(_unseen(["2", "3"], "2", "3"), events)) == 2


def test_top_up_kinds_limits_candidates():
    events = _events(["free_kick", "free_kick", "corner", "throw_in", "shot"])
    d = _unseen(["0"], "0")
    pick = top_up(d, events, n=1, kinds={"corner", "throw_in"})
    assert pick == ["2"]
    d = _unseen(["0", "2"], "0")
    assert top_up(d, events, n=2, kinds=["throw_in"]) == ["3"]
    assert all(events[int(r)].kind != "free_kick" for r in pick)


def test_top_up_kinds_unknown_raises():
    events = _events(["corner", "corner"])
    with pytest.raises(ValueError):
        top_up(_unseen(["0"], "0"), events, kinds={"cornerr"})
