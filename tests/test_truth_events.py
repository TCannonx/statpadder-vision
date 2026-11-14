from pathlib import Path

import pytest

from spv.truth.events import TruthEvent, read_events, read_eyeball, read_eyeball_xml, read_statpadder, zone
from truth_samples import EYEBALL_SAMPLE, EYEBALL_TIMED, EYEBALL_XML_SAMPLE, STATPADDER_SAMPLE


def _write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8-sig")
    return path


def test_eyeball_kinds_teams_and_times(tmp_path):
    tf = read_eyeball(_write(tmp_path, "e.csv", EYEBALL_SAMPLE))
    assert (tf.source, tf.rows, tf.timed_rows) == ("eyeball", 12, 11)
    got = [(e.row_id, e.half, e.video_s, e.kind, e.team) for e in tf.events]
    assert got == [
        ("1", 1, 30.0, "kick_off", "A"),
        ("3", 1, 95.2, "corner", "B"),
        ("4", 1, 120.0, "shot", "A"),
        ("5", 1, 121.0, "goal", "A"),
        ("7", 1, 180.0, "kick_off", "B"),
        ("8", 1, 200.5, "throw_in", "B"),
        ("9", 2, 3000.0, "kick_off", "B"),
        ("10", 2, 3100.0, "penalty", "A"),
        ("11", 2, 3200.0, "goal_kick", "A"),
    ]
    shot = tf.events[2]
    assert (shot.x, shot.y, shot.outcome) == (0.9, 0.5, "on")


def test_names_are_never_kept(tmp_path):
    text = repr(read_eyeball(_write(tmp_path, "e.csv", EYEBALL_SAMPLE)))
    for name in ("PLAYER", "Alpha", "Beta"):
        assert name not in text


def test_statpadder_export(tmp_path):
    tf = read_statpadder(_write(tmp_path, "s.csv", STATPADDER_SAMPLE))
    assert (tf.source, tf.rows, tf.timed_rows) == ("statpadder", 5, 4)
    got = [(e.row_id, e.half, e.video_s, e.kind, e.team, e.outcome) for e in tf.events]
    assert got == [
        ("r1", 1, 65.0, "corner", "A", None),
        ("r2", 1, 300.0, "shot", "A", "goal"),
        ("r2g", 1, 300.0, "goal", "A", None),
        ("r4", 2, 2800.0, "penalty", "B", "saved"),
    ]
    assert "Test Player" not in repr(tf)


def test_read_events_detects_the_format(tmp_path):
    assert read_events(_write(tmp_path, "e.csv", EYEBALL_SAMPLE)).source == "eyeball"
    assert read_events(_write(tmp_path, "s.csv", STATPADDER_SAMPLE)).source == "statpadder"
    with pytest.raises(ValueError):
        read_events(_write(tmp_path, "x.csv", "a,b,c\n1,2,3\n"))


def test_zone():
    assert zone(0.9, 0.1) == "final third, left (as the team attacks)"
    assert zone(0.5, 0.5) == "middle third, centre (as the team attacks)"
    assert zone(None, 0.5) == "no place"


def test_truth_event_is_frozen():
    event = TruthEvent("1", 1, 1.0, "shot", "A", None, None)
    with pytest.raises(AttributeError):
        event.kind = "goal"


def test_eyeball_xml_matches_the_csv(tmp_path):
    csv_file = read_eyeball(_write(tmp_path, "e.csv", EYEBALL_TIMED))
    xml_file = read_eyeball_xml(_write(tmp_path, "e.xml", EYEBALL_XML_SAMPLE))
    assert xml_file.events == csv_file.events
    assert (xml_file.source, xml_file.rows, xml_file.timed_rows) == ("eyeball", 11, 11)


def test_eyeball_xml_drops_names(tmp_path):
    text = repr(read_eyeball_xml(_write(tmp_path, "e.xml", EYEBALL_XML_SAMPLE)))
    for name in ("PLAYER", "Alpha", "Beta"):
        assert name not in text


def test_read_events_detects_xml(tmp_path):
    tf = read_events(_write(tmp_path, "e.xml", EYEBALL_XML_SAMPLE))
    assert tf.source == "eyeball"
    assert len(tf.events) == 9


def test_team_names_in_order_for_every_format(tmp_path):
    from spv.truth.events import team_names

    assert team_names(_write(tmp_path, "e.csv", EYEBALL_SAMPLE)) == ["Alpha", "Beta"]
    assert team_names(_write(tmp_path, "e.xml", EYEBALL_XML_SAMPLE)) == ["Alpha", "Beta"]
    assert team_names(_write(tmp_path, "s.csv", STATPADDER_SAMPLE)) == ["Us", "Them"]
    bad = _write(tmp_path, "x.csv", "a,b\n1,2\n")
    with pytest.raises(ValueError):
        team_names(bad)


def test_read_events_repr_holds_no_names(tmp_path):
    for name, text in (("e.csv", EYEBALL_SAMPLE), ("e.xml", EYEBALL_XML_SAMPLE), ("s.csv", STATPADDER_SAMPLE)):
        r = repr(read_events(_write(tmp_path, name, text)))
        for n in ("Alpha", "Beta", "Us", "Them"):
            assert f"'{n}'" not in r and f"={n}" not in r
