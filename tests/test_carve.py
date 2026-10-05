"""cutan.carve against drawn fixtures with exact ground truth (tests/fixtures/carve/).

Each strategy is measured where cutan#10 says it works, by the intersection
over union of the carved alpha with the drawn subject's mask; the quality
signals are checked where they should fire. A visual check renders every
carve over a checkerboard into one sheet (``CUTAN_CARVE_SHEET=<png>`` keeps it).
"""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

pytest.importorskip("cv2", reason="carving needs OpenCV: pip install 'cutan[carve]'")

from an.ir.assets import AssetSource  # noqa: E402
from an.stage.props import PropDescriptor  # noqa: E402
from cutan.carve import (  # noqa: E402
    Chroma,
    Face,
    FlatColour,
    Focus,
    GrabCut,
    PartSpec,
    Polygon,
    carve,
    carve_head,
    frame_source,
    split_parts,
    write_prop,
)
from cutan.carve.head import HEAD_CANVAS, HEAD_CENTRE, HEAD_FACE_H  # noqa: E402

FIX = Path(__file__).resolve().parent / "fixtures" / "carve"


def _img(name):
    return Image.open(FIX / f"{name}.png").convert("RGB")


def _mask(name):
    return np.asarray(Image.open(FIX / f"{name}_mask.png")) > 127


def _iou(part, truth):
    """IoU of a carving placed back on its source with the source-sized truth mask."""
    full = np.zeros(truth.shape, bool)
    a = part.alpha > 0.5
    x0, y0 = (round(v) for v in part.offset)
    h, w = a.shape
    full[y0 : y0 + h, x0 : x0 + w] = a[: truth.shape[0] - y0, : truth.shape[1] - x0]
    return (full & truth).sum() / (full | truth).sum()


# --- the strategies, each on its own case -----------------------------------


def test_flat_colour_keeps_an_enclosed_backdrop_coloured_interior_and_flags_the_glyph():
    part = carve(_img("cartoon"), point=(160, 150))
    assert part.quality.attached_pieces >= 1
    assert any("neck under 4 px" in w for w in part.quality.warnings())
    clean = carve(_img("cartoon"), point=(160, 150), detach=3)
    assert clean.quality.detached_pieces >= 1 and clean.quality.attached_pieces == 0
    assert _iou(clean, _mask("cartoon")) > 0.97
    # the head's interior is the wall's exact colour, enclosed by its outline: kept
    x, y = (round(v) for v in clean.to_part([(160, 60)])[0])
    assert clean.alpha[y, x] > 0.99


def test_an_unconnected_colour_key_loses_the_enclosed_interior():
    part = carve(_img("cartoon"), matte=FlatColour(connected=False), point=(160, 150),
                 fill_holes=False)
    x, y = (round(v) for v in part.to_part([(160, 60)])[0])
    assert 0 <= x < part.size[0] and 0 <= y < part.size[1]
    assert part.alpha[y, x] < 0.5


def test_chroma_keys_a_saturated_drape_and_despill_cleans_the_rim():
    part = carve(_img("chroma"), matte="chroma", point=(130, 150))
    assert _iou(part, _mask("chroma")) > 0.97
    assert part.quality.rim_backdrop_share < 0.1
    hue = Chroma().band(np.asarray(_img("chroma")))
    assert 250 < (hue[0] + 30) % 360 < 320  # centred on the purple


def test_grabcut_takes_one_prop_out_of_a_busy_wall_where_no_key_holds():
    """Measured: GrabCut 0.78, a flat key 0.54. GrabCut's misses are whole stripe
    slivers beside the thin stem (its documented weakness), not the prop."""
    part = carve(_img("busy"), matte=GrabCut(box=(60, 30, 180, 185)), point=(120, 120))
    flat = carve(_img("busy"), point=(120, 120))
    assert _iou(part, _mask("busy")) > 0.75 > _iou(flat, _mask("busy")) + 0.15


def test_a_polygon_and_a_key_combine():
    img = _img("cartoon")
    outline = [(115, 35), (205, 35), (205, 205), (115, 205)]  # leaves the glyph out
    part = carve(img, matte=Polygon(outline) & FlatColour(), point=(160, 150))
    assert _iou(part, _mask("cartoon")) > 0.97
    assert part.recipe["matte"]["matte"] == "and"
    assert [m["matte"] for m in part.recipe["matte"]["of"]] == ["polygon", "flat_colour"]


def test_focus_finds_the_sharp_object_on_a_blurred_background():
    part = carve(_img("blurred"), matte=Focus(), point=(120, 90), despill=0)
    assert _iou(part, _mask("blurred")) > 0.85


def test_any_callable_is_a_matte_and_a_wrong_shape_is_refused():
    def left_half(rgb, hint):
        a = np.zeros(rgb.shape[:2], np.float32)
        a[:, : rgb.shape[1] // 2] = 1
        return a

    part = carve(_img("busy"), matte=left_half, keep="all", despill=0)
    assert part.size[0] < 130
    assert part.recipe["matte"]["ref"].endswith(":test_any_callable_is_a_matte_and_a_wrong_shape_is_refused.<locals>.left_half")
    with pytest.raises(ValueError, match="returned"):
        carve(_img("busy"), matte=lambda rgb, hint: np.ones((3, 3)))


def test_upscale_keeps_the_source_resolution():
    a = carve(_img("cartoon"), point=(160, 150), detach=3)
    b = carve(_img("cartoon"), point=(160, 150), detach=3, upscale=2.0)
    assert abs(a.size[0] - b.size[0]) <= 2 and b.scale == 1.0
    with pytest.raises(ValueError, match="whole factor"):
        carve(_img("cartoon"), upscale=1.5)
    assert _iou(b, _mask("cartoon")) > 0.97


def test_an_empty_matte_says_what_to_check():
    with pytest.raises(ValueError, match="left nothing"):
        carve(_img("busy"), matte=lambda rgb, hint: np.zeros(rgb.shape[:2]))


# --- head mode ---------------------------------------------------------------


def _head_face():
    from tests.fixtures.carve.make_fixtures import HEAD_FACE_BOX, HEAD_JAW

    return Face(HEAD_FACE_BOX, jaw=HEAD_JAW)


def test_a_head_lands_on_the_canvas_with_its_face_box_at_the_fixed_height_and_centre():
    part = carve_head(_img("head"), face=_head_face())
    assert part.size == (HEAD_CANVAS, HEAD_CANVAS)
    assert part.anchor == (HEAD_CENTRE[0] / HEAD_CANVAS, HEAD_CENTRE[1] / HEAD_CANVAS)
    assert part.meta["face_box_h_on_canvas"] == pytest.approx(HEAD_FACE_H, rel=0.01)
    assert not part.meta["scaled_to_fit"]
    a = part.alpha
    cx, cy = (int(v) for v in HEAD_CENTRE)
    assert a[cy, cx] > 0.99  # the face centre is solid
    # the neck is cut just under the jaw: nothing of the shoulders survives
    chin = part.meta["chin_y_on_canvas"]
    assert chin + 0.25 * HEAD_FACE_H < HEAD_CANVAS
    assert a[int(chin + 0.25 * HEAD_FACE_H) :, :].max() < 0.02
    assert a[int(chin + 0.02 * HEAD_FACE_H), cx] > 0.9  # a little neck stays
    assert part.meta["cut"] == "jaw"
    # what a rig needs to hang the head: the neck point, the head's box
    nx, ny = part.meta["neck_on_canvas"]
    assert chin < ny < chin + 0.25 * HEAD_FACE_H and abs(nx - cx) < 0.1 * HEAD_FACE_H
    x0, y0, x1, y1 = part.meta["head_bbox_on_canvas"]
    assert y1 <= ny + 0.06 * HEAD_FACE_H and x0 < cx < x1


def test_a_flat_cut_for_a_box_without_a_jaw_and_a_locator_is_a_seam():
    face = _head_face()
    flat = carve_head(_img("head"), face=face.box)
    assert flat.meta["cut"] == "flat"
    found = carve_head(_img("head"), locate=lambda rgb: [Face((0, 0, 5, 5)), face])
    assert found.meta["face_box_in_source"] == list(face.box)
    with pytest.raises(LookupError, match="by hand"):
        carve_head(_img("head"), locate=lambda rgb: [])


def test_a_head_too_big_for_the_canvas_is_scaled_to_fit():
    part = carve_head(_img("head"), face=_head_face(), face_h=480)
    assert part.meta["scaled_to_fit"]
    a = part.alpha
    assert a[:4].max() < 0.05 and a[:, :4].max() < 0.05 and a[:, -4:].max() < 0.05


# --- parts ---------------------------------------------------------------------


def _clock_parts():
    clock = carve(_img("clock"), point=(110, 110))
    hub = (110.0, 110.0)  # source px, like every coordinate carve takes
    x0, y0 = (round(v) for v in clock.offset)
    h, w = clock.alpha.shape
    parts = {}
    for name in ("hour", "minute"):
        truth = _mask(f"clock_{name}").astype(np.float32)  # an array: the carving's size
        parts[name] = PartSpec(mask=truth[y0 : y0 + h, x0 : x0 + w], pivot=hub)
    r = 7  # the hub cap, listed last: drawn on top, so it owns the hub's pixels
    parts["cap"] = PartSpec(mask=[(110 + r * np.cos(t), 110 + r * np.sin(t))
                                  for t in np.linspace(0, 2 * np.pi, 24)],
                            pivot=hub, grow=0)
    return clock, hub, parts


def test_split_lifts_the_hands_and_paints_the_face_in_under_them():
    clock, hub, parts = _clock_parts()
    split = split_parts(clock, parts)
    assert [p.name for p in split.parts] == ["hour", "minute", "cap"]
    assert [p.draw_order for p in split.parts] == [1, 2, 3]
    cap = split.parts[2]
    assert np.asarray(cap.image)[round(cap.pivot[1]), round(cap.pivot[0]), 3] == 255
    base = np.asarray(split.base)
    # where the minute hand lay, the base is face-coloured again and still opaque
    import math

    a = math.radians(60)
    x, y = (round(v) for v in clock.to_part([(110 + 45 * math.sin(a), 110 - 45 * math.cos(a))])[0])
    assert base[y, x, 3] == 255
    assert np.abs(base[y, x, :3].astype(int) - (250, 244, 220)).max() < 30
    for p in split.parts:
        px, py = p.origin[0] + p.pivot[0], p.origin[1] + p.pivot[1]
        assert (px, py) == pytest.approx(clock.to_part([hub])[0])


def test_a_split_prop_is_one_bone_per_part_at_its_pivot(tmp_path):
    clock, hub, parts = _clock_parts()
    with pytest.raises(ValueError, match="no provenance"):
        write_prop(split_parts(clock, parts), tmp_path / "nope")
    assert not (tmp_path / "nope" / "parts").exists()  # nothing written on a refusal
    doc = write_prop(split_parts(clock, parts), tmp_path / "wall-clock", max_side=100, ours=True)
    assert doc.source is None  # our own drawing: "we made this"
    assert [b.name for b in doc.bones] == ["root", "hour", "minute", "cap"]
    assert [s.name for s in doc.slots] == ["body", "hour", "minute", "cap"]
    unit = 100 / max(clock.size)
    ax, ay = clock.anchor[0] * clock.size[0], clock.anchor[1] * clock.size[1]
    hour = doc.bones[1]
    hx, hy = clock.to_part([hub])[0]
    assert (hour.x, hour.y) == pytest.approx(((hx - ax) * unit, (hy - ay) * unit), abs=1e-3)
    for slot in ("body", "hour", "minute", "cap"):
        att = doc.skins["default"].slots[slot][slot]
        assert (tmp_path / "wall-clock" / att.path).is_file()
    # the file is a valid PropDescriptor as written
    again = PropDescriptor.model_validate_json((tmp_path / "wall-clock" / "prop.json").read_text())
    assert again == doc


# --- provenance and the library ------------------------------------------------


def test_frame_source_needs_a_licence_and_the_prop_carries_the_recipe(tmp_path):
    with pytest.raises(TypeError):
        frame_source("https://www.youtube.com/watch?v=abc")  # no licence: refused
    src = frame_source("https://www.youtube.com/watch?v=abcdefghijk", t=12.5,
                       license="all-rights-reserved", author="Someone")
    part = carve(_img("busy"), matte=GrabCut(box=(60, 30, 180, 185)), point=(120, 120),
                 source=src)
    doc = write_prop(part, tmp_path / "lamp")
    s = doc.source
    assert s.url.endswith("&t=12") and s.license == "all-rights-reserved"
    assert s.extra["frame_time_s"] == 12.5
    assert s.extra["carve"]["recipe"]["matte"]["matte"] == "grabcut"
    assert s.extra["carve"]["recipe"]["matte"]["box"] == [60, 30, 180, 185]
    assert s.extra["carve"]["mode"] == "part"
    assert set(s.extra["carve"]["quality"]) >= {"coverage", "rim_backdrop_share"}
    with pytest.raises(FileExistsError):
        write_prop(part, tmp_path / "lamp")


def test_a_published_carving_gets_its_rights_by_construction(tmp_path):
    from an.library import open_library, publish_dir

    src = frame_source("https://www.youtube.com/watch?v=abcdefghijk", t=3,
                       license="all-rights-reserved")
    part = carve(_img("cartoon"), point=(160, 150), detach=3, source=src)
    folder = tmp_path / "figure"
    write_prop(part, folder)
    lib = open_library("cutan", root=tmp_path / "lib")
    res = publish_dir(lib, folder, "prop.figure", origin="carved")
    record = lib.versions[f"prop.figure@{res.version}"] if hasattr(res, "version") else None
    record = record or next(iter(lib.versions.values()))
    assert record["rights"]["publishable"] is False
    assert record["doc"]["source"]["license"] == "all-rights-reserved"


def test_write_prop_records_a_given_source_beside_the_recipe(tmp_path):
    part = carve(_img("busy"), matte=GrabCut(box=(60, 30, 180, 185)), point=(120, 120),
                 source=frame_source(None, license="cc0-1.0"))
    other = AssetSource(provider="studio", license="cc-by-4.0", author="Us")
    doc = write_prop(part, tmp_path / "lamp", source=other)
    assert doc.source.provider == "studio"
    assert doc.source.extra["carve"]["recipe"]["matte"]["matte"] == "grabcut"
    assert doc.source.extra["carved_from"]["license"] == "cc0-1.0"


# --- optional strategies (skipped without their models) ------------------------


@pytest.mark.skipif(
    importlib.util.find_spec("rembg") is None
    or not (Path.home() / ".u2net" / "isnet-general-use.onnx").exists(),
    reason="rembg or its isnet-general-use model is not installed",
)
def test_rembg_mattes_a_photo():
    """skimage's astronaut (a NASA photo, public domain; skimage comes with rembg)."""
    from skimage import data

    photo = data.astronaut()
    part = carve(photo, matte="rembg", point=(250, 120), keep="largest")
    face = part.to_part([(250, 120)])[0]
    assert part.alpha[round(face[1]), round(face[0])] > 0.9
    assert 0.15 < part.quality.coverage < 0.9
    assert part.recipe["matte"] == {"matte": "rembg", "model": "isnet-general-use", "post_process": True}


# --- the visual check ----------------------------------------------------------


def _checker(size, k=8):
    w, h = size
    yy, xx = np.mgrid[:h, :w]
    c = np.where(((xx // k) + (yy // k)) % 2, 200, 255).astype(np.uint8)
    return Image.fromarray(np.dstack([c, c, c, np.full_like(c, 255)]), "RGBA")


def carve_sheet() -> Image.Image:
    """Every fixture's carve over a checkerboard, side by side: the visual check."""
    cases = [
        carve(_img("cartoon"), point=(160, 150), detach=3),
        carve(_img("chroma"), matte="chroma", point=(130, 150)),
        carve(_img("busy"), matte=GrabCut(box=(60, 30, 180, 185)), point=(120, 120)),
        carve(_img("blurred"), matte=Focus(), point=(120, 90), despill=0),
        carve_head(_img("head"), face=_head_face()),
    ]
    clock, _, parts = _clock_parts()
    split = split_parts(clock, parts)
    tiles = []
    for c in cases + [None]:
        im = (split.base if c is None else c.image).copy()
        im.thumbnail((256, 256))
        tile = _checker((256, 256))
        tile.alpha_composite(im, ((256 - im.width) // 2, (256 - im.height) // 2))
        tiles.append(tile)
    sheet = Image.new("RGBA", (256 * len(tiles), 256), (255, 255, 255, 255))
    for i, t in enumerate(tiles):
        sheet.paste(t, (256 * i, 0))
    return sheet


def test_the_visual_check_sheet_renders(tmp_path):
    sheet = carve_sheet()
    out = Path(os.environ.get("CUTAN_CARVE_SHEET") or tmp_path / "carve_sheet.png")
    sheet.save(out)
    assert sheet.size == (256 * 6, 256)
    # every tile shows its carve: a fair share of it differs from the bare checker
    arr = np.asarray(sheet.convert("RGB")).astype(int)
    empty = np.asarray(_checker((256, 256)).convert("RGB")).astype(int)
    for i in range(6):
        tile = arr[:, 256 * i : 256 * (i + 1)]
        assert (np.abs(tile - empty).max(axis=2) > 30).mean() > 0.05, f"tile {i} is empty"


def test_a_colour_selects_a_part_through_an_inverted_key():
    """The clock's hands are its only mid-grey: ``~FlatColour`` selects them."""
    clock = carve(_img("clock"), point=(110, 110))
    grey = ~FlatColour(colours=[(95, 95, 100)], connected=False, tolerance=12, softness=8)
    split = split_parts(clock, {"hands": PartSpec(mask=grey, pivot=(110, 110), reach=10)})
    hands = split.parts[0]
    truth = (_mask("clock_hour") | _mask("clock_minute"))
    full = np.zeros(truth.shape, bool)
    x0 = round(clock.offset[0] + hands.origin[0])
    y0 = round(clock.offset[1] + hands.origin[1])
    a = np.asarray(hands.image)[..., 3] > 127
    full[y0 : y0 + a.shape[0], x0 : x0 + a.shape[1]] = a
    yy, xx = np.mgrid[: truth.shape[0], : truth.shape[1]]
    off_hub = np.hypot(xx - 110, yy - 110) > 8  # the black hub is drawn over the hands
    # thin strokes: a 1-px edge dominates an IoU, so measure recall, and
    # precision against the truth widened by 2 px
    import cv2

    near = cv2.dilate(truth.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    recall = (full & truth & off_hub).sum() / (truth & off_hub).sum()
    precision = (full & near & off_hub).sum() / (full & off_hub).sum()
    assert recall > 0.95 and precision > 0.95, (recall, precision)
    assert (~grey).recipe()["matte"] == "not"


# --- findings of the adversarial reviews (PR #26) --------------------------------


def _two_tone():
    img = np.full((120, 160, 3), 250, np.uint8)
    img[20:60, 40:120] = (180, 30, 30)  # a dark red top half
    img[60:100, 40:120] = 212  # a light grey bottom half, close to the backdrop
    return img


def test_despill_repaints_the_edge_band_only_never_a_whole_region():
    part = carve(_two_tone(), point=(80, 40))
    x, y = (round(v) for v in part.to_part([(80, 85)])[0])
    px = np.asarray(part.image)[y, x]
    assert tuple(px[:3]) == (212, 212, 212) and px[3] == 255  # still grey, still solid
    assert part.quality.repainted_share < 0.1
    assert part.quality.soft_interior_share == 0.0


def test_despill_is_bounded_on_a_large_soft_matte():
    import time

    from cutan.carve.refine import despill

    rgb = np.random.default_rng(0).integers(0, 255, (1080, 1920, 3), dtype=np.uint8)
    alpha = np.zeros((1080, 1920), np.float32)
    alpha[100:1000, 200:1700] = 0.97  # a neural matte unsure everywhere inside
    alpha[500:520, 900:920] = 1.0
    t = time.perf_counter()
    out, share = despill(rgb, alpha, 1)
    assert time.perf_counter() - t < 3.0
    assert share < 0.02  # the interior (a distance from the edge) is trusted, alpha or not
    assert np.array_equal(out[600, 1000], rgb[600, 1000])


def test_a_thin_part_cut_off_by_detach_is_reported():
    img = np.full((140, 120, 3), 250, np.uint8)
    yy, xx = np.mgrid[:140, :120]
    img[np.hypot(xx - 60, yy - 90) < 35] = (40, 120, 200)  # a disc
    img[20:60, 59:62] = (40, 120, 200)  # a 3-px antenna on it
    part = carve(img, point=(60, 90), detach=2)
    assert part.quality.detached_pieces >= 1
    assert any("detach cut off" in w for w in part.quality.warnings())


def test_a_split_part_and_its_base_composite_back_without_a_seam():
    img = np.full((60, 80, 3), 250, np.uint8)
    img[10:50, 10:70] = (60, 140, 90)
    square = carve(img, point=(40, 30), despill=0)
    split = split_parts(square, {"right": PartSpec(mask=[(40.5, 5), (75, 5), (75, 55), (40.5, 55)],
                                                    pivot=(40, 30))})
    base = split.base.copy()
    p = split.parts[0]
    base.alpha_composite(p.image, (round(p.origin[0]), round(p.origin[1])))
    a = np.asarray(base)[..., 3].astype(float) / 255
    inside = square.alpha > 0.99
    assert a[inside].min() > 0.99


def test_grabcut_on_an_image_too_small_for_a_frame_says_so():
    with pytest.raises(ValueError, match="frame of background"):
        GrabCut()(np.zeros((3, 3, 3), np.uint8), __import__("cutan.carve", fromlist=["Hint"]).Hint())


def test_a_recipe_replays_the_carve_and_a_matte_round_trips_as_data():
    from cutan.carve import Levels, as_matte

    img = _img("cartoon")
    part = carve(img, matte=Polygon([(115, 35), (205, 35), (205, 205), (115, 205)]) & FlatColour(),
                 point=(160, 150), detach=3)
    again = carve(img, **json.loads(json.dumps(part.recipe)))  # through JSON, as a batch spec
    assert np.array_equal(np.asarray(again.image), np.asarray(part.image))
    head = carve_head(_img("head"), face=_head_face())
    head_again = carve_head(_img("head"), **json.loads(json.dumps(head.recipe)))
    assert np.array_equal(np.asarray(head_again.image), np.asarray(head.image))
    lv = Levels(of=Chroma(width=40), lo=0.3)
    assert as_matte(lv.recipe()).recipe() == lv.recipe()
    fallback = FlatColour(colours=[(1, 2, 3)]).otherwise("chroma")
    fallback(np.asarray(_img("chroma")), __import__("cutan.carve", fromlist=["Hint"]).Hint())
    assert fallback.recipe()["used"] in (0, 1)
    with pytest.raises(ValueError, match="cannot be replayed"):
        as_matte({"matte": "callable", "ref": "x:y"})


def test_write_prop_refuses_to_loosen_rights_without_a_relicense(tmp_path):
    src = frame_source("https://www.youtube.com/watch?v=abcdefghijk", t=3,
                       license="all-rights-reserved")
    part = carve(_img("busy"), matte=GrabCut(box=(60, 30, 180, 185)), point=(120, 120),
                 source=src)
    free = AssetSource(provider="us", license="cc0-1.0")
    with pytest.raises(ValueError, match="loosen"):
        write_prop(part, tmp_path / "a", source=free)
    doc = write_prop(part, tmp_path / "b", source=free,
                     relicense={"by": "the maintainer", "reason": "redrawn by hand"})
    assert doc.source.extra["relicensed"]["by"] == "the maintainer"
    assert doc.source.extra["carved_from"]["license"] == "all-rights-reserved"
    stricter = AssetSource(provider="us", license="all-rights-reserved-private-study")
    assert write_prop(part, tmp_path / "c", source=stricter).source.license.endswith("study")


def test_a_carve_from_a_local_file_records_its_name_not_its_path(tmp_path):
    clip = tmp_path / "private" / "clip.png"
    clip.parent.mkdir()
    _img("busy").save(clip)
    src = frame_source(str(clip), license="all-rights-reserved")
    part = carve(clip, matte=GrabCut(box=(60, 30, 180, 185)), point=(120, 120), source=src)
    write_prop(part, tmp_path / "lamp")
    text = (tmp_path / "lamp" / "prop.json").read_text()
    assert str(tmp_path) not in text and "clip.png" in text
