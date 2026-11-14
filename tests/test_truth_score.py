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
