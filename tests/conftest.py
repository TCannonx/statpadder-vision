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
    path = folder / "Bohemians Vs. test - Tactical.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=duration=3:size=320x180:rate=25",
                    "-pix_fmt", "yuv420p", str(path)], check=True)
    return path
