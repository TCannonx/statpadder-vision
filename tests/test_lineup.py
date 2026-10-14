import json

import numpy as np
import pytest

from spv.lineup import LineupError, load_lineup, slot_ids, slot_occupancy

FIXTURES = __import__("pathlib").Path(__file__).parent / "fixtures"


def test_slot_ids():
    ids = slot_ids()
    assert len(ids) == 22
    assert ids[0] == "home_01" and ids[10] == "home_11" and ids[11] == "away_01" and ids[21] == "away_11"


def test_on_pitch_counts_starters_and_reds():
    lineup = load_lineup(FIXTURES / "lineup_9_red.json")
    assert lineup.on_pitch("home", 0) == 9
    assert lineup.on_pitch("away", 99.9) == 9
    assert lineup.on_pitch("away", 100) == 8


def test_sub_keeps_count():
    lineup = load_lineup(FIXTURES / "lineup_11.json")
    assert lineup.on_pitch("home", 60) == 11


def test_slot_occupancy_shape_and_unused_slots():
    lineup = load_lineup(FIXTURES / "lineup_9_red.json")
    occ = slot_occupancy(lineup, np.arange(2000) / 10)
    assert occ.shape == (2000, 22)
    assert not occ[0, 9:11].any()
    assert occ[999, 11:20].all()
    assert occ[1000, 11:22].sum() == 8


def _write(tmp_path, data):
    path = tmp_path / "lineup.json"
    path.write_text(json.dumps(data))
    return path


def test_more_than_11_starters_rejected(tmp_path):
    data = json.loads((FIXTURES / "lineup_11.json").read_text())
    data["home"]["players"][11]["starter"] = True
    with pytest.raises(LineupError, match="starters"):
        load_lineup(_write(tmp_path, data))


def test_event_unknown_player_rejected(tmp_path):
    data = json.loads((FIXTURES / "lineup_11.json").read_text())
    data["events"][0]["on"] = "h99"
    with pytest.raises(LineupError, match="h99"):
        load_lineup(_write(tmp_path, data))
