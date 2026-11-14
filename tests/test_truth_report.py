from spv.truth.align import add_attack_mark, add_mark
from spv.truth.report import match_result, p0_report
from spv.truth.spot import record_verdict


def _aligned():
    d = {"marks": [], "kits": {}, "attack_marks": []}
    for half in (1, 2):
        for i, offset in enumerate([2.0, 2.4, 2.8]):
            add_mark(d, half, f"{half}-{i}", "corner", offset)
    for i in range(3):
        add_attack_mark(d, 1, f"a{i}", "A", "right")
        add_attack_mark(d, 2, f"b{i}", "A", "left")
    return d


def _spots(right):
    rows = [str(i) for i in range(20)]
    d = {"rows": rows, "verdicts": {}}
    for i, row in enumerate(rows):
        record_verdict(d, row, moment="ok" if i < right else "off", kind="ok", place="ok", team="ok")
    return d


def test_usable_match():
    result = match_result(_aligned(), _spots(18))
    assert result["usable"], result["reasons"]
    assert result["offsets"] == {1: 2.4, 2: 2.4}


def test_too_few_right():
    result = match_result(_aligned(), _spots(17))
    assert not result["usable"]
    assert result["reasons"] == ["spot checks: 17 of 20 right, need 18"]


def test_drifting_offset():
    d = _aligned()
    add_mark(d, 2, "late", "corner", 4.0)
    assert "half 2: anchors spread 2.0 s" in match_result(d, _spots(20))["reasons"]


def test_unfinished_work_is_not_usable():
    result = match_result({"marks": [], "kits": {}, "attack_marks": []}, {"rows": [], "verdicts": {}})
    assert not result["usable"] and len(result["reasons"]) == 4


def test_report_verdicts():
    good = match_result(_aligned(), _spots(20))
    bad = match_result(_aligned(), _spots(10))
    assert "**Verdict:** GO" in p0_report({"m01": good, "m02": good, "m03": good})
    text = p0_report({"m01": good, "m02": bad})
    assert "**Verdict:** STOP" in text and "| m02 |" in text


def test_unseen_rows_leave_too_few_visible_rows_until_topped_up():
    d = _spots(18)
    for row in ("18", "19"):
        record_verdict(d, row, moment="unseen", kind="ok", place="ok", team="ok")
    result = match_result(_aligned(), d)
    assert not result["usable"]
    assert result["reasons"] == ["spot checks: only 18 visible rows, need 20"]
    assert result["unseen"] == 2
    d["rows"] += ["20", "21"]
    for row in ("20", "21"):
        record_verdict(d, row, moment="ok", kind="ok", place="ok", team="ok")
    result = match_result(_aligned(), d)
    assert result["usable"], result["reasons"]
    assert "Not visible (replaced)" in p0_report({"m01": result})
    assert "| 20/20 | 2 |" in p0_report({"m01": result})
