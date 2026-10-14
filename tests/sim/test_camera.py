import numpy as np
import shapely

from spv.sim.camera import CameraParams, in_view, simulate_camera

from conftest import synthetic_tracks

CENTRE = np.array([52.5, 34.0])


def test_static_ball_in_view():
    path = simulate_camera(synthetic_tracks(np.tile(CENTRE, (100, 1))))
    for t in range(30, 100):
        assert in_view(path, t, CENTRE[None])[0]
        assert np.linalg.norm(path.aim_xy[t] - CENTRE) < 0.01


def test_lag():
    ball = np.tile(CENTRE, (200, 1))
    ball[50:, 0] += 30
    params = CameraParams()
    path = simulate_camera(synthetic_tracks(ball), params)
    steps = round(params.lag_s * 10)
    moved = (path.aim_xy[49 + steps, 0] - CENTRE[0]) / 30
    assert abs(moved - 0.632) < 0.03


def test_far_ball_zooms_in():
    far = simulate_camera(synthetic_tracks(np.tile([52.5, 66.0], (50, 1))))
    near = simulate_camera(synthetic_tracks(np.tile([52.5, 4.0], (50, 1))))
    assert far.hfov_deg[-1] < near.hfov_deg[-1]


def test_footprint_inside_grown_pitch():
    rng = np.random.default_rng(1)
    ball = np.cumsum(rng.normal(0, 1.5, size=(300, 2)), axis=0) + CENTRE
    ball = np.clip(ball, [0, 0], [105, 68])
    params = CameraParams()
    path = simulate_camera(synthetic_tracks(ball), params)
    grown = shapely.box(-params.margin_m, -params.margin_m, 105 + params.margin_m, 68 + params.margin_m)
    assert all(grown.buffer(1e-6).contains(p) and not p.is_empty for p in path.footprint)


def test_near_horizon_does_not_crash():
    path = simulate_camera(synthetic_tracks(np.tile([104.0, 67.0], (20, 1))), CameraParams(mast_height_m=0.5))
    assert path.footprint[-1].is_valid and path.footprint[-1].area > 0


def test_ball_nan_holds_aim():
    ball = np.tile(CENTRE, (100, 1))
    ball[40:60] = np.nan
    path = simulate_camera(synthetic_tracks(ball))
    assert np.allclose(path.aim_xy[40:60], path.aim_xy[39])
