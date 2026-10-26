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
    doc = CharacterDescriptor.model_validate_json(
        (char_dir / "character.json").read_text()
    )
    return {
        n: a for slots in doc.skins["default"].slots.values() for n, a in slots.items()
    }


def test_regions_of_the_sheet_draw_the_attachments(char, sheet):
    report = sheet_to_package(sheet, RECIPE, char, source=SOURCE)
    atts = _atts(char)
    assert (
        atts["head"].path == "parts/head.png"
        and atts["mouth_a"].path == "parts/mouth/mouth_a.png"
    )
    assert (char / "parts" / "head.png").is_file()
    assert [r.attachment for r in report.parts] == ["head", "mouth_a"]
    assert atts["head"].source.license == "cc0-1.0"  # provenance travels with the part
    assert "carve" in atts["head"].source.extra
    assert not [f for f in validate_character(char).findings if f.severity == "error"]


def test_a_point_anchors_the_part_and_no_point_keeps_the_rig_s_anchor_with_a_warning(
    char, sheet
):
    before = _atts(char)["mouth_a"].anchor
    report = sheet_to_package(sheet, RECIPE, char, source=SOURCE)
    atts = _atts(char)
    assert atts["mouth_a"].anchor == before
    assert any(w.startswith("mouth_a: no `point`") for w in report.warnings)
    # the head's point (55, 60) in a crop whose carved part starts at the head's trimmed corner
    u, v = atts["head"].anchor
    img = Image.open(char / "parts" / "head.png")
    assert img.size[0] * u == pytest.approx(
        55 - 20 + 4, abs=1.5
    )  # head spans x 20..90, pad 4
    assert img.size[1] * v == pytest.approx(60 - 20 + 4, abs=1.5)


def test_the_quality_warnings_are_surfaced_and_the_carver_is_a_seam(
    char, sheet, monkeypatch
):
    from dataclasses import replace

    from cutan.carve import carve, sheet as sheet_module

    def touchy(image, **kw):
        c = carve(image, **kw)
        return replace(c, quality=replace(c.quality, touches_edge=True))

    monkeypatch.setitem(sheet_module._CARVERS, "part", touchy)
    report = sheet_to_package(sheet, RECIPE[:1], char, source=SOURCE)
    assert report.warnings == [
        "head: the subject touches the crop's edge: widen the crop"
    ]
    assert "warning: head:" in report.format()


def test_a_bad_recipe_changes_nothing(char, sheet):
    before = (char / "character.json").read_text()
    for recipe, match in [
        (
            [SheetPart("head", (0, 0, 100, 120)), SheetPart("nope", (0, 0, 9, 9))],
            "no attachment",
        ),
        (
            [
                SheetPart("head/head", (0, 0, 100, 120)),
                SheetPart("head/front", (0, 0, 9, 9)),
            ],
            "both drawn by",
        ),
        (
            [
                SheetPart("head", (0, 0, 100, 120)),
                SheetPart("mouth_a", (0, 0, 10, 10), {"point": (5, 5)}),
            ],
            "left nothing",
        ),
    ]:
        with pytest.raises(ValueError, match=match):
            sheet_to_package(sheet, recipe, char, source=SOURCE)
    assert (char / "character.json").read_text() == before
    assert (char / "parts" / "head.svg").is_file()


def test_a_failure_while_setting_restores_the_character(char, sheet, monkeypatch):
    from cutan.carve import sheet as sheet_module

    real, calls = sheet_module.set_part, []

    def flaky(*a, **kw):
        calls.append(a[1])
        if len(calls) == 2:
            raise OSError("disk full")
        return real(*a, **kw)

    monkeypatch.setattr(sheet_module, "set_part", flaky)
    before = (char / "character.json").read_text()
    with pytest.raises(OSError):
        sheet_to_package(sheet, RECIPE, char, source=SOURCE)
    assert calls == ["head", "mouth_a"]
    assert (char / "character.json").read_text() == before
    assert (char / "parts" / "head.svg").is_file() and not (
        char / "parts" / "head.png"
    ).exists()


def test_the_report_names_the_factory_drawings_derived_from_a_replaced_part(
    char, sheet
):
    report = sheet_to_package(sheet, RECIPE[:1], char, source=SOURCE)
    assert report.derived == [d for r in report.parts for d in r.replacement.derived]


def test_provenance_is_required_unless_ours(char, sheet):
    with pytest.raises(ValueError, match="provenance"):
        sheet_to_package(sheet, RECIPE, char)
    sheet_to_package(sheet, RECIPE, char, ours=True)
    assert _atts(char)["head"].source is None


def test_a_recipe_is_json(char, sheet):
    recipe = json.loads(
        json.dumps(
            [
                {
                    "attachment": "head",
                    "crop": [0, 0, 100, 120],
                    "carve": {"matte": "flat_colour"},
                }
            ]
        )
    )
    assert (
        sheet_to_package(sheet, recipe, char, source=SOURCE).parts[0].attachment
        == "head"
    )


def test_the_recipe_cannot_override_the_sheet_s_region_or_source():
    with pytest.raises(ValueError, match="not recipe arguments"):
        SheetPart("head", (0, 0, 9, 9), {"source": None})
    with pytest.raises(ValueError, match="needs its `crop`"):
        SheetPart("head")
    with pytest.raises(ValueError, match="mode is one of"):
        SheetPart("head", (0, 0, 9, 9), mode="body")


def test_a_sheet_path_works(char, sheet, tmp_path):
    path = tmp_path / "sheet.png"
    Image.fromarray(sheet).save(path)
    sheet_to_package(path, RECIPE[:1], char, source=SOURCE)
    assert _atts(char)["head"].path == "parts/head.png"


def test_the_cli_command_reads_a_json_recipe(char, sheet, tmp_path):
    from cutan.characters.cli import from_sheet

    Image.fromarray(sheet).save(tmp_path / "sheet.png")
    recipe = {
        "schema_version": 1,
        "source": {"url": "https://example.com/s.png", "license": "cc0-1.0"},
        "parts": [
            {
                "attachment": "head",
                "crop": [0, 0, 100, 120],
                "carve": {"point": [55, 60]},
            }
        ],
    }
    (tmp_path / "r.json").write_text(json.dumps(recipe))
    out = from_sheet(
        char.name,
        str(tmp_path / "sheet.png"),
        str(tmp_path / "r.json"),
        out_dir=str(char.parent),
    )
    assert out.startswith("1 part(s)"), out
    assert _atts(char)["head"].source.license == "cc0-1.0"
    (tmp_path / "bad.json").write_text(json.dumps({"parts": recipe["parts"]}))
    bad = from_sheet(
        char.name,
        str(tmp_path / "sheet.png"),
        str(tmp_path / "bad.json"),
        out_dir=str(char.parent),
    )
    assert "provenance" in bad


def test_a_recipe_of_another_version_is_refused():
    from cutan.carve.sheet import load_recipe

    with pytest.raises(ValueError, match="schema_version 2"):
        load_recipe({"schema_version": 2, "parts": []})


def test_cli_reports_recipe_typos_instead_of_a_traceback(char, sheet, tmp_path):
    from cutan.characters.cli import from_sheet

    Image.fromarray(sheet).save(tmp_path / "sheet.png")
    for i, doc in enumerate(
        [
            [],
            {"parts": [{"attachment": "head", "crop": [0, 0, 9, 9], "typo": 1}]},
            {"ours": True},
        ]
    ):
        (tmp_path / f"{i}.json").write_text(json.dumps(doc))
        out = from_sheet(
            char.name,
            str(tmp_path / "sheet.png"),
            str(tmp_path / f"{i}.json"),
            out_dir=str(char.parent),
        )
        assert "Error" in out and "Traceback" not in out


def test_a_head_needs_its_face():
    with pytest.raises(ValueError, match="needs carve"):
        SheetPart("head", mode="head")


def _width(char_dir, name):
    return _atts(char_dir)[name].width


def test_a_unit_keeps_the_relative_scale_of_parts_from_one_sheet(char, sheet):
    from cutan.carve.sheet import load_recipe

    sheet_to_package(sheet, RECIPE, char, source=SOURCE, unit=0.5)
    sizes = {
        n: Image.open(char / a.path).size[0]
        for n, a in _atts(char).items()
        if n in ("head", "mouth_a")
    }
    assert _width(char, "head") == pytest.approx(sizes["head"] * 0.5)
    assert _width(char, "mouth_a") == pytest.approx(sizes["mouth_a"] * 0.5)
    assert _width(char, "head") / _width(char, "mouth_a") == pytest.approx(
        sizes["head"] / sizes["mouth_a"]
    )
    assert load_recipe({"unit": 0.5, "parts": []}).unit == 0.5
    with pytest.raises(ValueError, match="positive"):
        sheet_to_package(sheet, RECIPE, char, source=SOURCE, unit=0)


def test_no_unit_keeps_the_factory_width(char, sheet):
    sheet_to_package(sheet, RECIPE[:1], char, source=SOURCE)
    assert _width(char, "head") > 0  # the old drawing's width, as before


@pytest.fixture()
def torso_sheet():
    img = np.full((140, 200, 3), 245, np.uint8)
    img[20:120, 70:130] = (60, 120, 60)  # a body
    img[30:90, 40:70] = (200, 60, 40)  # a left arm, beside it
    img[30:90, 130:160] = (40, 40, 200)  # a right arm
    return img


SPLIT = {
    "arm_l": {"mask": [(35, 25), (70, 25), (70, 95), (35, 95)], "pivot": (55, 30)},
    "arm_r": {"mask": [(130, 25), (165, 25), (165, 95), (130, 95)], "pivot": (145, 30)},
}


def test_moving_parts_are_split_off_one_carving_at_their_pivots(char, torso_sheet):
    recipe = [SheetPart("torso", (0, 0, 200, 140), {"point": (100, 119)}, split=SPLIT)]
    report = sheet_to_package(torso_sheet, recipe, char, source=SOURCE, unit=1.0)
    assert [r.attachment for r in report.parts] == ["torso", "arm_l", "arm_r"]
    atts = _atts(char)
    arm = Image.open(char / atts["arm_l"].path)
    u, v = atts["arm_l"].anchor
    assert arm.size[0] * u == pytest.approx(55 - 40, abs=5)  # the pivot, in the part
    assert 0 <= arm.size[1] * v < 12  # at the shoulder, the arm's top
    assert atts["arm_l"].width == pytest.approx(
        arm.size[0]
    )  # one unit across the sheet
    assert atts["arm_l"].source.license == "cc0-1.0"
    base = np.asarray(Image.open(char / atts["torso"].path).convert("RGBA"))
    alpha = base[..., 3]
    assert (
        alpha[:, 5:20].max() == 0 and alpha[:, -20:-5].max() == 0
    )  # the arms left the body's picture
    assert alpha[60, 65] == 255  # the body stays
    assert not [f for f in validate_character(char).findings if f.severity == "error"]


# --- placing a split part (cutan#140), checked against an's own rig builder ---


def _edit(char_dir, change):
    raw = json.loads((char_dir / "character.json").read_text())
    change(raw)
    (char_dir / "character.json").write_text(json.dumps(raw))


def _bone(raw, name):
    return next(b for b in raw["bones"] if b["name"] == name)


def _built(char_dir):
    """``{slot: (x, y)}``: where an's builder draws each slot's node, view_box
    units from the rig's origin (scene px / k), composing the nodes' transforms."""
    from an.ir.schema import AssetRef
    from an.stage.rig import SCENE_PX_PER_VIEW_BOX, build_rig_subtree

    from cutan.characters.schema import CHARACTER_DOCUMENT_KIND

    raw = json.loads((char_dir / "character.json").read_text())
    root = build_rig_subtree(
        AssetRef(kind="character", id="c", store="characters", ref="c"),
        raw,
        textures={},
        descriptor_model=CharacterDescriptor,
        document_kind=CHARACTER_DOCUMENT_KIND,
        skip_slots=(),
    )
    k = SCENE_PX_PER_VIEW_BOX / raw["view_box"][3]
    out = {}

    def walk(node, at, m):
        t = node.transform
        here = at + m @ np.array([t.x, t.y])
        out[node.name] = tuple(here / k)
        r, sx, sy = t.rotation or 0.0, t.scale_x or 1.0, t.scale_y or 1.0
        c, s = np.cos(r), np.sin(r)
        own = np.array([[c * sx, -s * sy], [s * sx, c * sy]])
        for kid in node.children or []:
            walk(kid, here, m @ own)

    for kid in root.children:
        walk(kid, np.zeros(2), np.eye(2))
    return out


def _pivot_offset(char_dir, base, part):
    """The part's pivot from the base's anchor in SHEET px, from what was written:
    the part's split origin and anchor, the base's anchor, and the carving's scale
    (carved px per sheet px, from a picture's px against its declared width)."""
    atts = _atts(char_dir)
    b, p = atts[base], atts[part]
    bw, bh = Image.open(char_dir / b.path).size
    pw, ph = Image.open(char_dir / p.path).size
    ox, oy = p.source.extra["carve"]["split"]["origin"]
    pivot = (ox + p.anchor[0] * pw, oy + p.anchor[1] * ph)
    anchor = (b.anchor[0] * bw, b.anchor[1] * bh)
    return pivot, anchor


def _assert_placed(char_dir, base_slot, base, parts, *, unit):
    nodes = _built(char_dir)
    for slot, name in parts:
        pivot, anchor = _pivot_offset(char_dir, base, name)
        pw = Image.open(char_dir / _atts(char_dir)[name].path).size[0]
        scale = pw * unit / _atts(char_dir)[name].width
        want = tuple(
            nodes[base_slot][i] + (pivot[i] - anchor[i]) / scale * unit for i in (0, 1)
        )
        assert nodes[slot] == pytest.approx(want, abs=1e-6), name


TORSO = [SheetPart("torso", (0, 0, 200, 140), {"point": (100, 119)}, split=SPLIT)]
ARMS = [("arm_l", "arm_l"), ("arm_r", "arm_r")]


def test_a_unit_places_a_split_part_at_its_pivot_from_the_base_anchor(
    char, torso_sheet
):
    report = sheet_to_package(torso_sheet, TORSO, char, source=SOURCE, unit=0.5)
    _assert_placed(char, "torso", "torso", ARMS, unit=0.5)
    atts = _atts(char)
    assert (atts["torso"].x, atts["torso"].y) == (0, 0)  # the base is not moved
    assert not report.warnings


def test_a_part_nested_flat_under_its_base_is_placed_from_the_base_s_offset(
    char, torso_sheet
):
    def head_offset(raw):
        for att in raw["skins"]["default"]["slots"]["head"].values():
            att["x"] = 20.0

    _edit(char, head_offset)
    recipe = [
        SheetPart(
            "head",
            (0, 0, 200, 140),
            {"point": (100, 119)},
            split={"pupil_l": SPLIT["arm_l"]},
        )
    ]
    report = sheet_to_package(torso_sheet, recipe, char, source=SOURCE, unit=0.5)
    _assert_placed(char, "head", "head", [("left_pupil", "pupil_l")], unit=0.5)
    assert _atts(char)["sclera_l"].x == -41.6  # another slot is left alone
    assert not report.warnings


def test_bones_nesting_is_placed_by_its_own_rule(char, torso_sheet):
    def bones(raw):
        raw["nesting"] = "bones"
        for att in raw["skins"]["default"]["slots"]["torso"].values():
            att["x"], att["y"] = 15.0, -5.0  # a chain does not inherit it

    _edit(char, bones)
    sheet_to_package(torso_sheet, TORSO, char, source=SOURCE, unit=0.5)
    _assert_placed(char, "torso", "torso", ARMS, unit=0.5)


def test_a_superresolved_carving_is_placed_in_sheet_pixels(char, torso_sheet):
    carve_args = {
        "point": (100, 119),
        "superres": {"superres": "resample", "factor": 2},
    }
    recipe = [SheetPart("torso", (0, 0, 200, 140), carve_args, split=SPLIT)]
    sheet_to_package(torso_sheet, recipe, char, source=SOURCE, unit=1.0)
    _assert_placed(char, "torso", "torso", ARMS, unit=1.0)
    a = _atts(char)
    assert a["arm_l"].x == pytest.approx(-a["arm_r"].x, abs=3)  # the arms are mirrored


def test_a_character_with_two_skins_is_split_and_placed(char, torso_sheet):
    _edit(char, lambda raw: raw["skins"].update(alt=raw["skins"]["default"]))
    report = sheet_to_package(torso_sheet, TORSO, char, source=SOURCE)
    assert any("arm_l" in w and "`unit`" in w for w in report.warnings)
    sheet_to_package(torso_sheet, TORSO, char, source=SOURCE, unit=0.5)
    _assert_placed(char, "torso", "torso", ARMS, unit=0.5)


def test_without_a_unit_the_report_gives_the_pivot_offset(char, torso_sheet):
    report = sheet_to_package(torso_sheet, TORSO, char, source=SOURCE)
    atts = _atts(char)
    assert (atts["arm_l"].x, atts["arm_l"].y) == (0, 0)  # the factory's, untouched
    (note,) = [w for w in report.warnings if w.startswith("arm_l:")]
    assert "sheet px from the anchor of 'torso'" in note and "`unit`" in note
    (dx, dy) = (
        float(v) for v in note.split("its pivot is ")[1].split(" sheet")[0].split(",")
    )
    pivot, anchor = _pivot_offset(char, "torso", "arm_l")
    assert (dx, dy) == pytest.approx(
        (pivot[0] - anchor[0], pivot[1] - anchor[1]), abs=0.06
    )
    assert (dx, dy) == pytest.approx(
        (-45, -89), abs=1.5
    )  # the sheet's (55, 30) - (100, 119)


def test_a_turned_base_is_reported_not_guessed_and_a_turned_part_is_placed(
    char, torso_sheet
):
    _edit(char, lambda raw: _bone(raw, "torso").update(rotation_deg=10.0))
    report = sheet_to_package(torso_sheet, TORSO, char, source=SOURCE, unit=0.5)
    (note,) = [w for w in report.warnings if w.startswith("arm_l:")]
    assert "not placed: 'torso' is drawn turned or scaled at rest" in note
    assert _atts(char)["arm_l"].x == 0

    _edit(char, lambda raw: _bone(raw, "torso").update(rotation_deg=0.0))
    _edit(char, lambda raw: _bone(raw, "arm_l").update(rotation_deg=25.0))
    report = sheet_to_package(torso_sheet, TORSO, char, source=SOURCE, unit=0.5)
    assert not report.warnings
    _assert_placed(char, "torso", "torso", ARMS, unit=0.5)


def test_a_bone_cycle_is_refused_not_walked_forever(char, tmp_path):
    import threading

    from cutan.characters.placement import place_attachment, rest_anchor
    from cutan.characters.set_part import SetPartError

    _edit(char, lambda raw: _bone(raw, "root").update(parent="torso"))
    errors = []

    def attempt():
        for call in (
            lambda: rest_anchor(char, "arm_l"),
            lambda: place_attachment(char, "arm_l", world=(0.0, 0.0)),
        ):
            try:
                call()
            except Exception as e:  # noqa: BLE001 — the type is the assertion
                errors.append(e)

    worker = threading.Thread(target=attempt, daemon=True)
    worker.start()
    worker.join(timeout=10)
    assert not worker.is_alive(), "the walk did not stop on a bone cycle"
    assert len(errors) == 2 and all(isinstance(e, SetPartError) for e in errors)
    assert "cycle" in str(errors[0])


def test_an_unknown_or_ambiguous_attachment_is_a_set_part_error(char):
    from cutan.characters.placement import place_attachment
    from cutan.characters.set_part import SetPartError

    with pytest.raises(SetPartError, match="no attachment"):
        place_attachment(char, "nope", world=(0.0, 0.0))
    with pytest.raises(SetPartError, match="several slots"):
        place_attachment(char, "open", world=(0.0, 0.0))  # both eyes
    _edit(char, lambda raw: raw["slots"].append({"name": "x", "bone": "nope"}))
    _edit(
        char,
        lambda raw: raw["skins"]["default"]["slots"].update(
            x={"x": {"path": "parts/head.svg"}}
        ),
    )
    with pytest.raises(SetPartError, match="bone 'nope'"):
        place_attachment(char, "x/x", world=(0.0, 0.0))


def test_a_split_that_shares_a_file_or_takes_everything_changes_nothing(
    char, torso_sheet
):
    before = (char / "character.json").read_text()
    with pytest.raises(ValueError, match="both drawn by"):
        sheet_to_package(
            torso_sheet,
            [
                SheetPart(
                    "torso", (0, 0, 200, 140), split={"torso/front": SPLIT["arm_l"]}
                )
            ],
            char,
            source=SOURCE,
        )
    with pytest.raises(ValueError, match="cannot share a name"):
        SheetPart("torso", (0, 0, 9, 9), split={"torso": SPLIT["arm_l"]})
    everything = {
        "arm_l": {"mask": [(0, 0), (200, 0), (200, 140), (0, 140)], "pivot": (100, 70)}
    }
    with pytest.raises(ValueError, match="nothing is left"):
        sheet_to_package(
            torso_sheet,
            [SheetPart("torso", (0, 0, 200, 140), split=everything)],
            char,
            source=SOURCE,
        )
    assert (char / "character.json").read_text() == before


def test_a_unit_counts_sheet_pixels_even_when_the_carving_is_superresolved(
    char, torso_sheet
):
    carve_args = {
        "point": (100, 119),
        "superres": {"superres": "resample", "factor": 2},
    }
    recipe = [SheetPart("torso", (0, 0, 200, 140), carve_args, split=SPLIT)]
    sheet_to_package(torso_sheet, recipe, char, source=SOURCE, unit=1.0)
    atts = _atts(char)
    arm = Image.open(char / atts["arm_l"].path)
    assert atts["arm_l"].width == pytest.approx(
        arm.size[0] / 2
    )  # carved px are half a sheet px
    assert (
        28 < atts["arm_l"].width < 40
    )  # the arm is 30 sheet px wide, plus its pad (4 carved px, not 4 sheet px)


def test_a_split_part_s_provenance_is_its_own(char, torso_sheet):
    recipe = [SheetPart("torso", (0, 0, 200, 140), {"point": (100, 119)}, split=SPLIT)]
    sheet_to_package(torso_sheet, recipe, char, source=SOURCE)
    atts = _atts(char)
    base, arm = (a.source.extra["carve"] for a in (atts["torso"], atts["arm_l"]))
    assert "split" not in base and arm["split"]["part"] == "arm_l"
    ox, oy = arm["split"]["origin"]
    assert arm["source_to_part"][0][2] == pytest.approx(
        base["source_to_part"][0][2] - ox
    )
    assert arm["source_to_part"][1][2] == pytest.approx(
        base["source_to_part"][1][2] - oy
    )


def test_a_declared_width_replaces_a_declared_height_and_must_be_finite(char, sheet):
    from cutan.carve.sheet import load_recipe
    from cutan.characters.set_part import SetPartError, set_part

    pic = char.parent / "p.png"
    Image.fromarray(np.full((20, 40, 4), 200, np.uint8)).save(pic)
    for bad in (float("inf"), float("nan"), 0, True):
        with pytest.raises(SetPartError, match="finite positive"):
            set_part(char, "head", pic, width=bad)
    with pytest.raises(ValueError, match="finite and positive"):
        sheet_to_package(sheet, RECIPE, char, source=SOURCE, unit=float("inf"))
    with pytest.raises(ValueError, match="a number"):
        load_recipe({"unit": "0.5", "parts": []})
    raw = json.loads((char / "character.json").read_text())
    raw["skins"]["default"]["slots"]["head"]["head"]["height"] = 99.0
    (char / "character.json").write_text(json.dumps(raw))
    set_part(char, "head", pic, width=12.0)
    att = _atts(char)["head"]
    assert att.width == 12.0 and not att.height


def test_a_typo_in_a_split_spec_fails_before_anything_is_carved():
    with pytest.raises(TypeError):
        SheetPart(
            "torso",
            (0, 0, 9, 9),
            split={"arm_l": {"mask": [], "pivot": (1, 1), "typo": 1}},
        )
