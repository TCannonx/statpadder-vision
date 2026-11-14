import pytest

from spv.truth.frames import clock, contact_sheet, offsets


def test_offsets():
    assert offsets("-2:2:1") == [-2.0, -1.0, 0.0, 1.0, 2.0]
    assert offsets("-1:1:0.5") == [-1.0, -0.5, 0.0, 0.5, 1.0]


@pytest.mark.parametrize("bad", ["1:2", "2:1:1", "0:1:0", "a:b:c"])
def test_offsets_refuses_bad_specs(bad):
    with pytest.raises(ValueError):
        offsets(bad)


def test_clock():
    assert clock(3725.25) == "1:02:05.2"
    assert clock(-3) == "0:00:00.0"


def test_contact_sheet(tiny_video, tmp_path):
    from PIL import Image

    out = contact_sheet(tiny_video, [0.5, 1.0, 1.5, 30.0], ["a", "b", "c", "after the end"],
                        tmp_path / "sheet.png", columns=4, width=160)
    assert Image.open(out).size == (4 * 160, 90 + 22)  # 320x180 scaled to 160x90, plus a label band
