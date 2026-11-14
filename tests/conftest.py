import shutil
import subprocess
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def tiny_video(tmp_path_factory) -> Path:
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        pytest.skip("ffmpeg not on PATH")
    folder = tmp_path_factory.mktemp("video") / "with spaces. dots"
    folder.mkdir()
    path = folder / "Home Vs. test - Tactical.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=duration=3:size=320x180:rate=25",
                    "-pix_fmt", "yuv420p", str(path)], check=True)
    return path


def synthetic_tracks(ball_xy, players_xy=None, rate=10.0, teams=None):
    """PitchTracks on a 105 x 68 pitch from arrays: ball (T, 2), players (T, N, 2)."""
    import numpy as np

    from spv.sim.tracks import PitchTracks

    ball_xy = np.asarray(ball_xy, dtype=float)
    n_moments = len(ball_xy)
    if players_xy is None:
        players_xy = np.zeros((n_moments, 0, 2))
    players_xy = np.asarray(players_xy, dtype=float)
    n = players_xy.shape[1]
    teams = teams or ["home" if i < (n + 1) // 2 else "away" for i in range(n)]
    return PitchTracks(rate=rate, pitch=(105.0, 68.0), times_s=np.arange(n_moments) / rate,
                       ids=[f"{t}_p{i}" for i, t in enumerate(teams)], teams=teams, xy=players_xy,
                       ball_xy=ball_xy)
