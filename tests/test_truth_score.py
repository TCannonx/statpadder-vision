from spv.truth.events import TruthEvent
from spv.truth.score import BAR_KINDS, group, match, per_group, to_video


def ev(rid, t, kind="goal", half=1, x=0.5, team="A"):
    return TruthEvent(rid, half, t, kind, team, x, 0.5)


def test_exact_match():
    assert len(match([ev("a", 10)], [ev("p", 10)], 2)) == 1


def test_tolerance():
    t, p = [ev("a", 10)], [ev("p", 13)]
    assert len(match(t, p, 5)) == 1
    assert match(t, p, 2) == []


def test_one_prediction_one_truth():
    pairs = match([ev("a", 10), ev("b", 11)], [ev("p", 10.5)], 5)
    assert len(pairs) == 1


def test_groups_never_match():
    assert match([ev("a", 10, "goal")], [ev("p", 10, "corner")], 5) == []


def test_free_kick_final_third():
    assert group(ev("a", 1, "free_kick", x=0.5)) is None
    assert group(ev("a", 1, "free_kick", x=0.8)) == "free_kick_final_third"
    assert group(ev("a", 1, "free_kick", x=None)) is None
    assert group(ev("a", 1, "throw_in")) is None


def test_penalty_is_shot():
    assert group(ev("a", 1, "penalty")) == "shot"
    assert len(match([ev("a", 10, "penalty")], [ev("p", 10, "shot")], 2)) == 1


def test_to_video():
    out = to_video([ev("a", 10, half=1), ev("b", 10, half=2), ev("c", 10, half=1)], {1: 5.5})
    assert [e.video_s for e in out] == [15.5, 10, 15.5]


def test_per_group_none_when_empty():
    r = per_group([ev("a", 10, "goal")], [], 5)
    assert set(r) == set(BAR_KINDS)
    assert r["goal"] == {"truth": 1, "pred": 0, "matched": 0, "recall": 0.0, "precision": None}
    assert r["corner"]["recall"] is None and r["corner"]["precision"] is None
    r = per_group([], [ev("p", 1, "goal")], 5)
    assert r["goal"]["recall"] is None and r["goal"]["precision"] == 0.0


def test_per_group_values():
    r = per_group([ev("a", 10), ev("b", 50)], [ev("p", 11), ev("q", 90), ev("r", 200)], 5)
    assert r["goal"] == {"truth": 2, "pred": 3, "matched": 1, "recall": 0.5, "precision": 1 / 3}


def test_determinism_and_tiebreak():
    t = [ev("b", 10), ev("a", 10)]
    p = [ev("q", 10), ev("p", 10)]
    first = match(t, p, 5)
    assert first == match(list(reversed(t)), list(reversed(p)), 5)
    assert [(a.row_id, b.row_id) for a, b in first] == [("a", "p"), ("b", "q")]


def test_team_map():
    from spv.truth.score import team_map

    assert team_map(["Alpha FC", "Beta"], ["alpha  fc", "BETA"]) == {"A": "A", "B": "B"}
    assert team_map(["Alpha", "Beta"], ["Beta United", "Alpha"]) == {"A": "B", "B": "A"}
    assert team_map(["Alpha", "Beta"], ["Us", "Them"]) is None
    assert team_map(["Alpha", "Beta"], ["Alpha", "Gamma"]) is None
    assert team_map(["Alpha", "Beta"], []) is None


def test_accuracy():
    from spv.truth.score import accuracy

    def e(rid, team, x, y):
        return TruthEvent(rid, 1, 1.0, "goal", team, x, y)

    pairs = [
        (e("a", "A", 0.9, 0.5), e("p", "A", 0.8, 0.5)),  # team right, zone right
        (e("b", "B", 0.9, 0.1), e("q", "A", 0.2, 0.1)),  # team wrong, zone wrong
        (e("c", "A", None, None), e("r", "A", 0.5, 0.5)),  # no place
    ]
    assert accuracy(pairs, {"A": "A", "B": "B"}) == {"team_right": 2, "team_of": 3, "zone_right": 1, "zone_of": 2}
    # swapped mapping: pred A -> truth B
    assert accuracy(pairs, {"A": "B", "B": "A"}) == {"team_right": 1, "team_of": 3, "zone_right": 1, "zone_of": 2}


def _res(goal=(10, 10, 9), other=(4, 4, 3), acc=(9, 10, 7, 10), mapping="by name"):
    def grp(n, m, k):
        return {"truth": n, "pred": m, "matched": k, "recall": k / n if n else None, "precision": k / m if m else None}

    at = {"goal": grp(*goal)}
    for g in ("corner", "free_kick_final_third", "shot"):
        at[g] = grp(*other)
    return {
        "at_2s": at,
        "at_5s": at,
        "accuracy": {"team_right": acc[0], "team_of": acc[1], "zone_right": acc[2], "zone_of": acc[3]},
        "team_mapping": mapping,
    }


def test_score_match():
    from spv.truth.score import score_match

    r = score_match([ev("a", 10)], [ev("p", 13)], {1: 0.0}, None)
    assert r["at_2s"]["goal"]["matched"] == 0 and r["at_5s"]["goal"]["matched"] == 1
    assert r["accuracy"]["team_of"] == 1 and r["accuracy"]["team_right"] == 1
    assert r["team_mapping"] == "unverified"
    r = score_match([ev("a", 10)], [ev("p", 10, team="B")], {1: 0.0}, {"A": "B", "B": "A"})
    assert r["team_mapping"] == "by name" and r["accuracy"]["team_right"] == 1
    r = score_match([ev("a", 10)], [ev("p", 15)], {1: 5.0}, None)
    assert r["at_2s"]["goal"]["matched"] == 1


def test_bar_edges_pass():
    from spv.truth.score import bar

    rows = bar(_res())
    assert len(rows) == 1 + 3 * 2 + 2
    assert all(set(r) == {"test", "value", "need", "pass"} for r in rows)
    assert [r["pass"] for r in rows] == [True] * 9
    # precision exactly 0.70 passes, just under fails
    assert all(r["pass"] for r in bar(_res(other=(9, 10, 7))))
    assert not all(r["pass"] for r in bar(_res(other=(90, 100, 69))))


def test_bar_fail_and_none():
    from spv.truth.score import bar

    rows = {r["test"]: r for r in bar(_res(goal=(10, 10, 8)))}
    assert not rows["goal recall"]["pass"]
    rows = {r["test"]: r for r in bar(_res(goal=(0, 0, 0), acc=(0, 0, 0, 0)))}
    assert rows["goal recall"]["value"] is None and not rows["goal recall"]["pass"]
    assert not rows["team"]["pass"] and not rows["zone"]["pass"]
    rows = {r["test"]: r for r in bar(_res(acc=(8, 10, 7, 10)))}
    assert not rows["team"]["pass"] and rows["zone"]["pass"]


def test_pool():
    from spv.truth.score import pool

    p = pool([_res(goal=(10, 10, 9), acc=(9, 10, 7, 10)), _res(goal=(10, 20, 8), acc=(5, 10, 3, 5), mapping="unverified")])
    g = p["at_5s"]["goal"]
    assert g == {"truth": 20, "pred": 30, "matched": 17, "recall": 17 / 20, "precision": 17 / 30}
    assert p["accuracy"] == {"team_right": 14, "team_of": 20, "zone_right": 10, "zone_of": 15}
    assert p["team_mapping"] == "unverified"
    assert pool([_res(), _res()])["team_mapping"] == "by name"


def test_markdown():
    from spv.truth.score import score_markdown

    md = score_markdown("m01", "held-out", _res(goal=(0, 0, 0)))
    assert "m01" in md and "held-out" in md
    for name in ("goal recall", "corner precision", "shot recall", "team", "zone", "free_kick_final_third"):
        assert name in md
    assert "90%" in md and "PASS" in md and "FAIL" in md and "-" in md


def test_empty_mapping_is_not_by_name():
    from spv.truth.score import score_match

    assert score_match([ev("a", 10)], [ev("p", 10)], {}, {})["team_mapping"] == "by name"
    assert score_match([ev("a", 10)], [ev("p", 10)], {}, None)["team_mapping"] == "unverified"
