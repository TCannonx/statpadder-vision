"""The footage shows minors: no media file or local drive path may reach git."""

import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def _git(*args):
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True)


@pytest.mark.parametrize("name", ["frame.jpeg", "frame.JPG", "a.webp", "a.bmp", "clip.m4v", "clip.MP4",
                                  "clip.mts", "clip.webm", "clip.ts", "clip.mov", "frames/0001.png"])
def test_media_is_ignored(name):
    assert _git("check-ignore", "--no-index", "-q", name).returncode == 0, name


def test_no_local_drive_paths_tracked():
    drive_path = re.compile(r"\b[A-Za-z]:[\\/](?:Users|OneDrive)", re.IGNORECASE)
    hits = [f for f in _git("ls-files").stdout.splitlines()
            if (REPO / f).is_file() and drive_path.search((REPO / f).read_text(errors="ignore"))]
    assert hits == []
