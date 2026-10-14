import numpy as np
import shapely

from spv.sim.camera import CameraPath
from spv.sim.scenes import find_scenes

from conftest import synthetic_tracks


def test_scenes_on_synthetic():
    rate, n = 10.0, 6000
    rng = np.random.default_rng(0)
    players = np.tile(rng.uniform([30, 5], [75, 63], size=(23, 2)), (n, 1, 1))
    players[1200:1800, :12] = [5.0, 34.0]  # a crowd in the left box from 120 s to 180 s
    players[:3000, 22] = np.nan  # a substitute coming on at 300 s
    players[3000:, 0] = np.nan
    ball = np.tile([52.5, 34.0], (n, 1))
    cam = CameraPath(mast=(52.5, -3, 8), aim_xy=ball, hfov_deg=np.full(n, 40.0),
                     footprint=[shapely.box(40, 20, 65, 48)] * n)
    scenes = {s.name: s for s in find_scenes(synthetic_tracks(ball, players, rate=rate), cam)}
    assert list(scenes) == ["crowded_box", "long_out_of_view", "substitution"]
    assert scenes["crowded_box"].start <= 1200 < scenes["crowded_box"].stop
    assert scenes["substitution"].start == round(290 * rate)
    assert all(s.stop - s.start == 600 for s in scenes.values())
