import numpy as np
import shapely

from spv.sim.camera import CameraPath, in_view
from spv.sim.detections import DetectionParams, simulate_detections

from conftest import synthetic_tracks


def whole_pitch_camera(n):
    return CameraPath(mast=(52.5, -3.0, 8.0), aim_xy=np.tile([52.5, 34.0], (n, 1)),
                      hfov_deg=np.full(n, 60.0), footprint=[shapely.box(0, 0, 105, 68)] * n)


def spread_players(n_moments, n_players=20):
    grid = np.array([[10 + 20 * (i % 5), 8 + 15 * (i // 5)] for i in range(n_players)], dtype=float)
    return np.tile(grid, (n_moments, 1, 1))


def test_rates():
    n = 2000
    tracks = synthetic_tracks(np.full((n, 2), np.nan), spread_players(n))
    det = simulate_detections(tracks, whole_pitch_camera(n), seed=0)
    people = det.truth >= 0
    assert abs(people.sum() / (n * 20) - 0.95) < 0.02
    assert abs((det.truth == -1).sum() / n - 0.5) < 0.1
    true_team = np.array([0 if t == "home" else 1 for t in tracks.teams])[det.truth[people]]
    assert abs((det.team[people] != true_team).mean() - 0.03) < 0.01


def test_crowding_raises_misses():
    n = 3000
    players = np.tile([[50.0, 30.0], [50.5, 30.0]], (n, 1, 1))
    det = simulate_detections(synthetic_tracks(np.full((n, 2), np.nan), players), whole_pitch_camera(n),
                              DetectionParams(false_per_moment=0.0), seed=0)
    assert abs(1 - (det.truth >= 0).sum() / (2 * n) - 0.30) < 0.03


def test_out_of_view_never_detected():
    from spv.sim.camera import simulate_camera
    n = 300
    rng = np.random.default_rng(3)
    players = rng.uniform([0, 0], [105, 68], size=(n, 22, 2))
    ball = np.clip(np.cumsum(rng.normal(0, 1, (n, 2)), axis=0) + [30, 30], 0, 68)
    tracks = synthetic_tracks(ball, players)
    cam = simulate_camera(tracks)
    det = simulate_detections(tracks, cam, seed=0)
    for m, truth in zip(det.moment, det.truth):
        if truth >= 0:
            assert in_view(cam, m, tracks.xy[m, truth][None])[0]
        elif truth == -2:
            assert in_view(cam, m, tracks.ball_xy[m][None])[0]


def test_seed_reproducible():
    n = 200
    tracks = synthetic_tracks(np.tile([50.0, 30.0], (n, 1)), spread_players(n))
    a = simulate_detections(tracks, whole_pitch_camera(n), seed=7)
    b = simulate_detections(tracks, whole_pitch_camera(n), seed=7)
    assert all(np.array_equal(getattr(a, f), getattr(b, f)) for f in ("moment", "xy", "team", "is_ball", "conf", "truth"))
