"""A closed eye leaves no ring where the white of the eye was (cutan#66, finding 10 of the second end-user test).

The factory's filled closed lid used to be exactly the sclera's ellipse, so the
white's anti-aliased edge showed round a closed eye: a grey of 63 on a black
silhouette at a 720p eye's size. The lid now reaches ``LID_COVER_PAD`` units
past the white on every side (measured: none left at 3).
"""

from __future__ import annotations

import re

import pytest

from cutan.characters.factory import EYE_RX, EYE_RY, LID_COVER_PAD, new_character

pytestmark = pytest.mark.genre("cutout_animation")


def _ellipse(svg: str) -> tuple[float, float]:
    m = re.search(r'<ellipse[^>]*rx="([\d.]+)"[^>]*ry="([\d.]+)"', svg)
    return float(m.group(1)), float(m.group(2))


def test_the_closed_lid_covers_the_eye_white_with_a_margin(tmp_path):
    char = new_character(tmp_path, name="amy", use_dicebear=False).parent
    for side in ("l", "r"):
        lid = _ellipse((char / "parts" / f"eye_{side}_closed.svg").read_text(encoding="utf-8"))
        white = _ellipse((char / "parts" / f"sclera_{side}.svg").read_text(encoding="utf-8"))
        assert white == (EYE_RX, EYE_RY)
        assert lid == (EYE_RX + LID_COVER_PAD, EYE_RY + LID_COVER_PAD)
        assert LID_COVER_PAD >= 3
