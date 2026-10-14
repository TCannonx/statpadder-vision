import urllib.request

import numpy as np

from spv.sim.tracks import ensure_metrica, load_metrica

from conftest import FIXTURES


def load(rate=10.0):
    return load_metrica(FIXTURES / "metrica_home.csv", FIXTURES / "metrica_away.csv", rate=rate)


def test_axes():
    raw = load(rate=25.0)  # 25 Hz keeps the source frames: t = 0.04 is frame 1
    p1, p2 = raw.ids.index("home_p1"), raw.ids.index("home_p2")
    assert np.allclose(raw.xy[0, p1], [0.0, 0.0])
    assert np.allclose(raw.xy[1, p2], [105.0, 68.0])
    assert raw.pitch == (105.0, 68.0)


def test_resample_rate():
    tracks = load()
    assert tracks.rate == 10.0
    assert len(tracks.times_s) == 20
    assert np.allclose(np.diff(tracks.times_s), 0.1)
    assert tracks.times_s[0] >= 0.04 - 1e-9 and tracks.times_s[-1] <= 2.0 + 1e-9


def test_absent_player_stays_nan():
    tracks = load()
    sub = tracks.ids.index("home_p12")
    before = tracks.times_s < 0.4
    after = tracks.times_s > 0.44
    assert np.isnan(tracks.xy[before, sub]).all()
    assert not np.isnan(tracks.xy[after, sub]).any()


def test_ids_and_teams():
    tracks = load()
    assert tracks.ids == ["home_p1", "home_p2", "home_p12", "away_p25", "away_p26"]
    assert tracks.teams.count("home") == 3
    assert tracks.xy.shape == (20, 5, 2) and tracks.ball_xy.shape == (20, 2)


def test_ensure_metrica_skips_existing(tmp_path, monkeypatch):
    folder = tmp_path / "metrica"
    folder.mkdir()
    for side in ("Home", "Away"):
        (folder / f"Sample_Game_2_RawTrackingData_{side}_Team.csv").write_text("x")

    def no_network(*args, **kwargs):
        raise AssertionError("network used")

    monkeypatch.setattr(urllib.request, "urlopen", no_network)
    home, away = ensure_metrica(2, tmp_path)
    assert home.exists() and away.exists()
