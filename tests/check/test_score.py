import numpy as np

from spv.check.score import score_positions, track_from_truth
from spv.sim.scenes import null_solver

from conftest import synthetic_tracks


def truth(n=100):
    rng = np.random.default_rng(0)
    players = rng.uniform([0, 0], [105, 68], size=(1, 22, 2)) + np.linspace(0, 5, n)[:, None, None]
    return synthetic_tracks(np.tile([52.5, 34.0], (n, 1)), players)


def test_score_perfect():
    t = truth()
    result = score_positions(track_from_truth(t, 0, 100), t, 0, 100)
    assert result["within_2m"] == 1.0 and result["false_players"] == 0.0 and result["seen_share"] == 1.0


def test_score_null():
    t = truth()
    result = score_positions(null_solver(None, 100, 10.0, (105.0, 68.0)), t, 0, 100)
    assert result == {"within_2m": 0.0, "seen_share": 0.0, "false_players": 0.0}


def test_score_slot_order_irrelevant():
    t = truth()
    track = track_from_truth(t, 0, 100)
    order = np.r_[np.random.default_rng(1).permutation(11), 11 + np.random.default_rng(2).permutation(11)]
    track.positions = track.positions[:, order]
    assert score_positions(track, t, 0, 100)["within_2m"] == 1.0


def test_track_from_truth_substitute_takes_freed_slot():
    t = truth()
    t.xy = np.concatenate([t.xy, t.xy[:, :1] + 1], axis=1)
    t.ids.append("home_p99")
    t.teams.append("home")
    t.xy[:50, 22] = np.nan
    t.xy[50:, 0] = np.nan
    track = track_from_truth(t, 0, 100)
    assert (track.positions["state"][:, :11] == 0).all()
    x_slot0 = track.positions["x"][:, 0] / 100
    assert np.allclose(x_slot0[:50], t.xy[:50, 0, 0], atol=0.005)
    assert np.allclose(x_slot0[50:], t.xy[50:, 22, 0], atol=0.005)
