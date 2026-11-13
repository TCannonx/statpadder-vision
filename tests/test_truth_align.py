import pytest

from spv.truth.align import (add_attack_mark, add_mark, attack_consistent, attack_summary, half_offset,
                             half_spread, load_alignment, save_alignment, set_kit)


def _empty():
    return {"marks": [], "kits": {}, "attack_marks": []}


def test_offset_and_spread():
    d = _empty()
    add_mark(d, 1, "1", "kick_off", 3.0)
    add_mark(d, 1, "3", "corner", 3.5)
    add_mark(d, 1, "8", "throw_in", 4.0)
    assert half_offset(d, 1) == 3.5 and half_spread(d, 1) == 1.0
    assert half_offset(d, 2) is None and half_spread(d, 2) is None
    add_mark(d, 1, "8", "throw_in", 3.2)  # marking a row again replaces it
    assert half_spread(d, 1) == 0.5 and len(d["marks"]) == 3


def test_save_and_load(tmp_path):
    d = _empty()
    add_mark(d, 2, "9", "kick_off", -12.5)
    set_kit(d, "A", "white shirts, black shorts")
    save_alignment("m01", d, tmp_path)
    assert load_alignment("m01", tmp_path) == d
    assert load_alignment("m02", tmp_path) == _empty()


def test_attack_direction():
    d = _empty()
    add_attack_mark(d, 1, "4", "A", "right")
    add_attack_mark(d, 1, "x", "B", "left")  # B shooting left means A attacks right
    add_attack_mark(d, 1, "y", "A", "right")
    for row in ("p", "q", "r"):
        add_attack_mark(d, 2, row, "A", "left")
    summary = attack_summary(d)
    assert summary[1] == {"A": "right", "agree": 3, "of": 3}
    assert attack_consistent(summary)
    add_attack_mark(d, 2, "z", "A", "right")
    assert not attack_consistent(attack_summary(d))
    with pytest.raises(ValueError):
        add_attack_mark(d, 1, "s", "A", "up")


def test_attack_needs_both_halves_switched():
    d = _empty()
    for row in ("a", "b", "c"):
        add_attack_mark(d, 1, row, "A", "right")
    assert not attack_consistent(attack_summary(d))
    for row in ("d", "e", "f"):
        add_attack_mark(d, 2, row, "A", "right")  # same end both halves: wrong
    assert not attack_consistent(attack_summary(d))
