"""Silhouettes are the figure the stage draws, and never land in the asset (an#272).

The end-user test compared two different figures and got IoU 1.000: both PNGs
were the factory's composite SVG, a headless torso that ignores build, hat and
head scale. And the PNG was written into the character's folder, so a later
`an library publish` shipped it.
"""

from __future__ import annotations

import pytest

from cutan.characters import new_character

pytestmark = [pytest.mark.browser, pytest.mark.ffmpeg]


def _project_with(tmp_path):
    chars = tmp_path / "p" / "assets" / "characters"
    new_character(chars, name="alice", use_dicebear=False, build="stick", hat="bowler", head_scale=1.7)
    new_character(chars, name="bob", use_dicebear=False, build="squat", hat="none")
    return chars


def test_two_different_figures_have_different_silhouettes(tmp_path):
    from cutan.characters.cli import silhouette

    chars = _project_with(tmp_path)
    before = {p.relative_to(chars) for p in chars.rglob("*")}
    out = silhouette("alice", other="bob", out_dir=str(chars), size=256)
    iou = float(out.rsplit("IoU: ", 1)[1].split()[0])
    assert iou < 0.75, out
    # written under the project's artifacts, nothing added to the assets
    assert (tmp_path / "p" / "artifacts" / "silhouettes" / "alice.png").is_file()
    assert {p.relative_to(chars) for p in chars.rglob("*")} == before


#: A figure drawn in pale colours: untinted, most of it would read as background.
PALE = {role: "#f4f0ea" for role in ("skin", "clothing", "leg", "hair", "accessory")}


def test_a_silhouette_is_the_whole_figure_black_on_white(tmp_path):
    from PIL import Image

    from cutan.characters.silhouette import render_character_silhouettes

    chars = tmp_path / "chars"
    new_character(chars, name="pale", use_dicebear=False, hat="bowler", palette=PALE)
    (png,) = render_character_silhouettes({"pale": chars / "pale"}, tmp_path / "out", size=256).values()
    img = Image.open(png).convert("L")
    assert set(img.getdata()) <= {0, 255}
    dark = [(x, y) for x in range(img.width) for y in range(img.height) if img.getpixel((x, y)) < 128]
    xs, ys = [x for x, _ in dark], [y for _, y in dark]
    # a head with its hat on top and legs below: the figure spans much of the frame...
    assert max(ys) - min(ys) > img.height * 0.4
    # ... and is FILLED, pale as it is drawn: the tint, not the outlines, makes it
    assert len(dark) > 0.3 * (max(xs) - min(xs) + 1) * (max(ys) - min(ys) + 1)
