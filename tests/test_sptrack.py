import json
import zipfile

import numpy as np
import pytest

from spv.lineup import slot_ids
from spv.sptrack import (POS_DTYPE, Manifest, SptrackError, SptrackVersionError, State, TrackFile,
                         decode, encode, read_sptrack, write_sptrack)


def make_manifest(n: int) -> Manifest:
    return Manifest(format_version="1.0", module_version="0.1.0", rate=10.0, pitch_length_m=105.0,
                    pitch_width_m=68.0, pitch_source="default", coordinate_system="test",
                    teams={"home": "Home", "away": "Away"}, slots=slot_ids(),
                    substitutions=[{"team": "home", "time_s": 1.0, "off": "h4", "on": "h12"}],
                    quality={"camera_share": 0.5, "seen_share": 0.25, "mean_uncertainty_m": 1.5},
                    n_moments=n)


def random_track(n: int = 50, seed: int = 0) -> TrackFile:
    rng = np.random.default_rng(seed)
    xy = rng.uniform([0, 0], [105, 68], size=(n, 22, 2))
    state = rng.integers(0, 4, size=(n, 22))
    xy[state >= State.NOT_ON_PITCH] = np.nan
    positions = encode(xy, rng.uniform(0, 10, size=(n, 22)), state)
    ball = encode(rng.uniform([0, 0], [105, 68], size=(n, 2)), np.ones(n), np.zeros(n, dtype=int))
    view = [np.array([[0.0, 0.0], [10.5, 0.0], [10.5, 6.8]])] * 3 + [np.zeros((0, 2))] * (n - 3)
    return TrackFile(manifest=make_manifest(n), positions=positions, ball=ball,
                     ball_in_air=rng.integers(0, 2, size=n).astype(bool), view=view,
                     pieces=[{"piece": 0, "slot": "home_01"}],
                     corrections=[{"frames": [1, 2], "change": "dropped", "why": "too fast"}])


def test_dtype_is_six_bytes():
    assert POS_DTYPE.itemsize == 6


def test_roundtrip(tmp_path):
    track = random_track()
    write_sptrack(tmp_path / "m.sptrack", track)
    back = read_sptrack(tmp_path / "m.sptrack")
    assert back.manifest == track.manifest
    xy0, _, st0 = decode(track.positions)
    xy1, _, st1 = decode(back.positions)
    assert np.array_equal(st0, st1)
    shown = st0 <= State.PREDICTED
    assert np.abs(xy1[shown] - xy0[shown]).max() <= 0.005
    assert np.isnan(xy1[~shown]).all()
    assert np.array_equal(back.ball_in_air, track.ball_in_air)
    assert len(back.view) == len(track.view)
    for a, b in zip(track.view, back.view):
        assert a.shape == b.shape and (a.size == 0 or np.abs(a - b).max() <= 0.005)
    assert back.pieces == track.pieces and back.corrections == track.corrections


def test_uncertainty_steps():
    pos = encode(np.zeros((3, 2)), np.array([0.1, 0.13, 70.0]), np.zeros(3, dtype=int))
    _, unc, _ = decode(pos)
    assert unc.tolist() == [0.0, 0.25, 63.75]


def test_out_of_range_raises():
    with pytest.raises(SptrackError):
        encode(np.array([[400.0, 1.0]]), np.zeros(1), np.zeros(1, dtype=int))


def test_nan_seen_raises():
    with pytest.raises(SptrackError):
        encode(np.array([[np.nan, 1.0]]), np.zeros(1), np.array([State.SEEN]))


def _set_version(path, version):
    with zipfile.ZipFile(path) as z:
        members = {n: z.read(n) for n in z.namelist()}
    manifest = json.loads(members["manifest.json"])
    manifest["format_version"] = version
    members["manifest.json"] = json.dumps(manifest).encode()
    with zipfile.ZipFile(path, "w") as z:
        for n, b in members.items():
            z.writestr(n, b)


def test_newer_major_version_rejected(tmp_path):
    path = tmp_path / "m.sptrack"
    write_sptrack(path, random_track())
    _set_version(path, "1.3")
    read_sptrack(path)
    _set_version(path, "2.0")
    with pytest.raises(SptrackVersionError):
        read_sptrack(path)


def test_size_full_match(tmp_path):
    n = 54_000
    state = np.full((n, 22), State.UNKNOWN)
    positions = encode(np.full((n, 22, 2), np.nan), np.zeros((n, 22)), state)
    ball = encode(np.full((n, 2), np.nan), np.zeros(n), np.full(n, State.UNKNOWN))
    track = TrackFile(manifest=make_manifest(n), positions=positions, ball=ball,
                      ball_in_air=np.zeros(n, dtype=bool), view=[np.zeros((0, 2))] * n,
                      pieces=[], corrections=[])
    write_sptrack(tmp_path / "m.sptrack", track)
    assert (tmp_path / "m.sptrack").stat().st_size < 7.5e6
