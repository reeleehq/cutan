"""A reference sheet becomes an art package (cutan#128)."""

from __future__ import annotations

import json

import numpy as np
import pytest
from PIL import Image

pytest.importorskip("cv2")

from cutan.carve import frame_source  # noqa: E402
from cutan.carve.sheet import SheetPart, sheet_to_package  # noqa: E402
from cutan.characters import new_character  # noqa: E402
from cutan.characters.schema import CharacterDescriptor  # noqa: E402
from cutan.characters.validate import validate_character  # noqa: E402

SOURCE = frame_source("https://example.com/sheet.png", license="cc0-1.0")


@pytest.fixture()
def char(tmp_path):
    return new_character(tmp_path, name="ned", seed="ned", use_dicebear=False).parent


@pytest.fixture()
def sheet():
    img = np.full((120, 200, 3), 245, np.uint8)  # flat backdrop
    img[20:100, 20:90] = (200, 60, 40)  # a head
    img[50:70, 130:170] = (40, 40, 160)  # a mouth shape
    return img


RECIPE = [
    SheetPart("head", (0, 0, 100, 120), {"point": (55, 60)}),
    SheetPart("mouth_a", (110, 30, 190, 90)),
]


def _atts(char_dir):
    doc = CharacterDescriptor.model_validate_json((char_dir / "character.json").read_text())
    return {n: a for slots in doc.skins["default"].slots.values() for n, a in slots.items()}


def test_regions_of_the_sheet_draw_the_attachments(char, sheet):
    report = sheet_to_package(sheet, RECIPE, char, source=SOURCE)
    atts = _atts(char)
    assert atts["head"].path == "parts/head.png" and atts["mouth_a"].path == "parts/mouth/mouth_a.png"
    assert (char / "parts" / "head.png").is_file()
    assert [r.attachment for r in report.parts] == ["head", "mouth_a"]
    assert atts["head"].source.license == "cc0-1.0"  # provenance travels with the part
    assert "carve" in atts["head"].source.extra
    assert not [f for f in validate_character(char).findings if f.severity == "error"]


def test_a_point_anchors_the_part_and_no_point_keeps_the_rig_s_anchor(char, sheet):
    before = _atts(char)["mouth_a"].anchor
    sheet_to_package(sheet, RECIPE, char, source=SOURCE)
    atts = _atts(char)
    assert atts["mouth_a"].anchor == before
    u, v = atts["head"].anchor
    assert (u, v) != (0.5, 0.78) and 0 < u < 1 and 0 < v < 1


def test_the_quality_warnings_are_surfaced_and_the_carver_is_a_seam(char, sheet):
    from dataclasses import replace

    from cutan.carve import carve

    def touchy(image, **kw):
        c = carve(image, **kw)
        return replace(c, quality=replace(c.quality, touches_edge=True))

    report = sheet_to_package(sheet, RECIPE[:1], char, source=SOURCE, carver=touchy)
    assert report.warnings == ["head: the subject touches the crop's edge: widen the crop"]
    assert "warning: head:" in report.format()


def test_a_bad_recipe_changes_nothing(char, sheet):
    before = (char / "character.json").read_text()
    for recipe, match in [
        ([SheetPart("head", (0, 0, 100, 120)), SheetPart("nope", (0, 0, 9, 9))], "no attachment"),
        ([SheetPart("head", (0, 0, 100, 120)), SheetPart("head", (0, 0, 9, 9))], "once per recipe"),
    ]:
        with pytest.raises(ValueError, match=match):
            sheet_to_package(sheet, recipe, char, source=SOURCE)
    # a part that carves nothing fails before the first part is set
    blank = SheetPart("mouth_a", (0, 0, 10, 10), {"point": (5, 5)})
    with pytest.raises(Exception):
        sheet_to_package(sheet, [SheetPart("head", (0, 0, 100, 120)), blank], char, source=SOURCE)
    assert (char / "character.json").read_text() == before
    assert (char / "parts" / "head.svg").is_file()


def test_provenance_is_required_unless_ours(char, sheet):
    with pytest.raises(ValueError, match="provenance"):
        sheet_to_package(sheet, RECIPE, char)
    sheet_to_package(sheet, RECIPE, char, ours=True)
    assert _atts(char)["head"].source is None


def test_a_recipe_is_json(char, sheet):
    recipe = json.loads(json.dumps([{"attachment": "head", "crop": [0, 0, 100, 120], "carve": {"matte": "flat_colour"}}]))
    assert sheet_to_package(sheet, recipe, char, source=SOURCE).parts[0].attachment == "head"


def test_the_recipe_cannot_override_the_sheet_s_region_or_source():
    with pytest.raises(ValueError, match="not recipe arguments"):
        SheetPart("head", (0, 0, 9, 9), {"source": None})


def test_a_sheet_path_works(char, sheet, tmp_path):
    path = tmp_path / "sheet.png"
    Image.fromarray(sheet).save(path)
    sheet_to_package(path, RECIPE[:1], char, source=SOURCE)
    assert _atts(char)["head"].path == "parts/head.png"


def test_the_cli_command_reads_a_json_recipe(char, sheet, tmp_path):
    from cutan.characters.cli import from_sheet

    Image.fromarray(sheet).save(tmp_path / "sheet.png")
    recipe = {"source": {"url": "https://example.com/s.png", "license": "cc0-1.0"},
              "parts": [{"attachment": "head", "crop": [0, 0, 100, 120], "carve": {"point": [55, 60]}}]}
    (tmp_path / "r.json").write_text(json.dumps(recipe))
    out = from_sheet(char.name, str(tmp_path / "sheet.png"), str(tmp_path / "r.json"), out_dir=str(char.parent))
    assert out.startswith("1 part(s)"), out
    assert _atts(char)["head"].source.license == "cc0-1.0"
    (tmp_path / "bad.json").write_text(json.dumps({"parts": recipe["parts"]}))
    bad = from_sheet(char.name, str(tmp_path / "sheet.png"), str(tmp_path / "bad.json"), out_dir=str(char.parent))
    assert "provenance" in bad
