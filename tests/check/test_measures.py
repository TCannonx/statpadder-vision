import pytest

from spv.check.measures import Measure, compare, load_baseline, results_table, save_baseline, update_baseline


def lower(name, value, margin=0.1, relative=False):
    return Measure(name, value, "lower", margin, relative)


def test_compare_statuses():
    baseline = {"a": 1.0, "b": 1.0, "c": 1.0, "gone": 1.0}
    outcomes = {o.name: o.status for o in compare(
        [lower("a", 1.05), lower("b", 1.2), lower("c", 0.8), lower("fresh", 3.0)], baseline)}
    assert outcomes == {"a": "same", "b": "worse", "c": "better", "fresh": "new", "gone": "missing"}


def test_higher_is_better():
    outcomes = compare([Measure("h", 0.5, "higher", 0.01)], {"h": 0.6})
    assert outcomes[0].status == "worse"


def test_relative_margin():
    assert compare([lower("r", 14.0, 0.5, True)], {"r": 10.0})[0].status == "same"
    assert compare([lower("r", 16.0, 0.5, True)], {"r": 10.0})[0].status == "worse"


def test_update_refuses_when_worse(tmp_path):
    path = tmp_path / "base.json"
    save_baseline(path, [lower("a", 1.0)])
    with pytest.raises(ValueError, match="worse"):
        update_baseline(path, [lower("a", 2.0)])
    assert load_baseline(path) == {"a": 1.0}


def test_update_writes_better_and_new_only(tmp_path):
    path = tmp_path / "base.json"
    save_baseline(path, [lower("a", 1.0), lower("b", 1.0)])
    update_baseline(path, [lower("a", 0.5), lower("b", 1.05), lower("c", 7.0)])
    assert load_baseline(path) == {"a": 0.5, "b": 1.0, "c": 7.0}


def test_table_has_every_measure():
    table = results_table(compare([lower("a", 1.0), lower("b", 2.0)], {"a": 1.0, "z": 3.0}))
    for name in ("a", "b", "z"):
        assert f"| {name} |" in table
