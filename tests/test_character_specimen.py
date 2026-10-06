"""A character's specimen for `an library sheet` (cutan#40, an#347).

The sheet asks a kind for the shot that shows one entity on its own and tiles
its first frame; without one, a character was a labelled grey placeholder.
"""

from __future__ import annotations

import io

import pytest

from an.genres import entity_kind, load
from an.ir.schema import AssetRef, Meta, Resolution, SceneIR

from cutan.characters import new_character


def test_the_character_kind_has_a_specimen():
    load()
    kind = entity_kind("character")
    shot = kind.specimen(AssetRef(kind="character", id="ned", store="characters", ref="ned"))
    assert shot.renderer == "cutout" and [e.ref for e in shot.entities] == ["ned"]
    assert not shot.actions  # at rest, facing the camera


@pytest.mark.browser
@pytest.mark.ffmpeg
def test_the_specimen_frame_shows_the_character(tmp_path):
    """Drawn the way the sheet draws it (`an.probe.frame`), the first frame holds
    the figure: a centred mass of non-background pixels, not a blank."""
    from PIL import Image

    from an.probe import frame
    from an.project import init, load as load_project

    load()
    root = init(tmp_path / "p")
    new_character(root / "assets" / "characters", name="ned", use_dicebear=False)
    shot = entity_kind("character").specimen(
        AssetRef(kind="character", id="ned", store="characters", ref="ned")
    )
    load_project(root).mall["scenes"]["main"] = SceneIR(
        meta=Meta(resolution=Resolution(width=256, height=256), default_renderer=shot.renderer),
        timeline=[shot],
    )
    img = Image.open(io.BytesIO(frame(root, shot.id, 0.0))).convert("RGB")
    background = img.getpixel((0, 0))
    differs = [
        (x, y)
        for x in range(0, img.width, 4)
        for y in range(0, img.height, 4)
        if img.getpixel((x, y)) != background
    ]
    assert len(differs) > 50
    xs = [x for x, _ in differs]
    assert abs((min(xs) + max(xs)) / 2 - img.width / 2) < img.width * 0.15  # centred
