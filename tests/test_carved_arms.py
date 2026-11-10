"""A carved character's one-stroke raster arms split at the elbow (cutan#208).

The rig under test is a factory character whose arms are replaced by raster
strokes (a `(` and a `)`, as the carved OverSimplified persona's are), plus a
drawn-face swap set whose pose hides the head, as the carved persona's faces do.
No browser, no render: shots are compiled and points measured on the compiled
nodes.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

from an.ir.schema import Shot
from an.project import init, load
from an.stage.compile import compile_shot
from an.stage.solve import _local_box, _pivot
from an.stage.timeline import evaluate_timeline, screen_position, timeline_from_scene
from an.stage.tree import walk_children
from cutan.characters import new_character
from cutan.characters.carved_arms import has_raster_arms, split_carved_arms
from cutan.characters.cli import add_forearms as cli_add_forearms
from cutan.characters.descriptor_io import load_descriptor

W, H = 640, 480
ARM_W, ARM_H, STROKE = 36, 170, 11


def _stroke_png(path: Path, *, bulge_right: bool) -> None:
    """A curved black stroke top to bottom, bulging to one side (`)` or `(`)."""
    im = Image.new("RGBA", (ARM_W, ARM_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    xs = np.linspace(0, 1, 60)
    pts = [
        (
            (7 + 20 * np.sin(np.pi * t)) if bulge_right else (ARM_W - 7 - 20 * np.sin(np.pi * t)),
            6 + t * (ARM_H - 12),
        )
        for t in xs
    ]
    d.line(pts, fill=(23, 26, 28, 255), width=STROKE, joint="curve")
    for x, y in (pts[0], pts[-1]):
        r = STROKE / 2
        d.ellipse([x - r, y - r, x + r, y + r], fill=(23, 26, 28, 255))
    im.save(path)


def _carved_project(root: Path) -> Path:
    init(root)
    chars = root / "assets" / "characters"
    new_character(chars, name="ned", seed="ned", use_dicebear=False, feet_origin=True)
    char = chars / "ned"
    _stroke_png(char / "parts" / "arm_r.png", bulge_right=True)
    _stroke_png(char / "parts" / "arm_l.png", bulge_right=False)
    Image.new("RGBA", (40, 40), (255, 255, 255, 255)).save(char / "parts" / "face_x.png")
    desc = json.loads((char / "character.json").read_text(encoding="utf-8"))
    skin = desc["skins"]["default"]["slots"]
    for side in "lr":
        slot = next(s for s in desc["slots"] if s["name"] == f"arm_{side}")
        skin[f"arm_{side}"][slot["attachment"]].update(
            {"path": f"parts/arm_{side}.png", "anchor": [0.5, 0.02]}
        )
    # a drawn face on a `face` bone under the head, whose pose hides the head and the mouth
    desc["bones"].append({"name": "face", "parent": "head", "x": 0.0, "y": 0.0})
    desc["slots"].append({"name": "face", "bone": "face", "draw_order": 50, "attachment": "face_none"})
    skin["face"] = {
        "face_none": {"path": "parts/face_x.png", "anchor": [0.5, 0.5]},
        "face_x": {"path": "parts/face_x.png", "anchor": [0.5, 0.5]},
    }
    desc.setdefault("asset_sets", {})["face"] = {"cartoon": "face_none", "x": "face_x"}
    desc.setdefault("swap_poses", {})["face"] = {
        "x": {"head": {"alpha": 0.0}, "mouth": {"alpha": 0.0}}
    }
    (char / "character.json").write_text(json.dumps(desc), encoding="utf-8")
    return root


def _char(root: Path) -> Path:
    return root / "assets" / "characters" / "ned"


def _compile(root: Path, shot: Shot):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return compile_shot(shot, load(root).mall, fps=24, width=W, height=H)


def _shot(entities: list[dict] | None = None, actions: list[dict] | None = None, **extra) -> Shot:
    return Shot.model_validate(
        {
            "id": "s",
            "duration": 1.0,
            "entities": [
                {"kind": "character", "id": "ned", "store": "characters", "ref": "ned",
                 "stage": {"at": [0, 150]}},
                *(entities or []),
            ],
            "actions": actions or [],
            **extra,
        }
    )


def _screen(doc, path: str, local_fraction: tuple[float, float] | None = None, *, t: float = 0.0):
    nodes = dict(walk_children(doc.scene))
    pose = evaluate_timeline(timeline_from_scene(doc), t)
    if local_fraction is None:
        point = _pivot(nodes[path])
    else:
        left, top, w, h = _local_box(nodes[path])
        point = (left + local_fraction[0] * w, top + local_fraction[1] * h)
    return screen_position(doc, path, pose=pose, point=point)


def test_a_carved_rig_has_raster_arms_and_a_factory_rig_does_not(tmp_path):
    root = tmp_path / "f"
    init(root)
    new_character(root / "assets/characters", name="ned", seed="ned", use_dicebear=False)
    assert not has_raster_arms(load_descriptor(_char(root)))
    assert has_raster_arms(load_descriptor(_char(_carved_project(tmp_path / "c"))))


def test_the_split_adds_forearms_hand_bones_and_nests_by_bones(tmp_path):
    root = _carved_project(tmp_path / "p")
    report = split_carved_arms(_char(root))
    desc = json.loads((_char(root) / "character.json").read_text(encoding="utf-8"))
    bones = {b["name"]: b for b in desc["bones"]}
    slots = {s["name"]: s for s in desc["slots"]}
    assert desc["nesting"] == "bones" and desc["metadata"]["arms"] == "split-carved"
    for side in "lr":
        assert bones[f"forearm_{side}"]["parent"] == f"arm_{side}"
        assert bones[f"hand_{side}"]["parent"] == f"forearm_{side}"
        assert f"hand_{side}" not in slots  # the hand is the stroke's end, not a drawing
        assert slots[f"forearm_{side}"]["draw_order"] == slots[f"arm_{side}"]["draw_order"]
        for name in (f"arm_{side}_upper.png", f"forearm_{side}.png"):
            assert (_char(root) / "parts" / name).is_file()
    r = next(a for a in report.arms if a.side == "r")
    assert r.stroke_width == pytest.approx(STROKE, abs=2)
    # the hand is at the bottom of the stroke, the elbow halfway down it
    assert r.hand[1] == pytest.approx(ARM_H - 6, abs=1.0)  # the centre of its round end
    assert r.elbow[1] == pytest.approx(ARM_H / 2, abs=2)


def test_the_two_halves_are_the_stroke_with_a_cap_on_the_elbow(tmp_path):
    root = _carved_project(tmp_path / "p")
    original = np.array(Image.open(_char(root) / "parts/arm_r.png"))[:, :, 3] > 128
    report = split_carved_arms(_char(root))
    parts = _char(root) / "parts"
    up = np.array(Image.open(parts / "arm_r_upper.png"))[:, :, 3] > 128
    fo = np.array(Image.open(parts / "forearm_r.png"))[:, :, 3] > 128
    ex, ey = next(a for a in report.arms if a.side == "r").elbow
    assert ((up | fo) == original).mean() > 0.995  # nothing lost, little added (the caps)
    assert up[int(ey), int(ex)] and fo[int(ey), int(ex)]  # both halves carry the joint
    assert not up[int(ey) + STROKE :].any() and not fo[: int(ey) - STROKE].any()


def test_the_split_arm_is_the_one_piece_arm_at_rest(tmp_path):
    """The elbow pivots where the cut crosses the stroke on the unsplit drawing."""
    one = _carved_project(tmp_path / "one")
    two = _carved_project(tmp_path / "two")
    report = split_carved_arms(_char(two))
    r = next(a for a in report.arms if a.side == "r")
    before = _compile(one, _shot())
    after = _compile(two, _shot())
    elbow_on_arm = _screen(before, "ned/arm_r", (r.elbow[0] / ARM_W, r.elbow[1] / ARM_H))
    elbow_pivot = _screen(after, "ned/torso/arm_r/forearm_r")
    assert elbow_pivot == pytest.approx(elbow_on_arm, abs=0.05)
    assert _screen(before, "ned/head") == pytest.approx(_screen(after, "ned/torso/head"), abs=0.01)


def test_a_bent_forearm_carries_the_held_item_at_the_stroke_end(tmp_path):
    """`held_by: ned@hand_r` holds at the end of the drawn stroke, and follows the bend (an#816)."""
    root = _carved_project(tmp_path / "p")
    report = split_carved_arms(_char(root))
    r = next(a for a in report.arms if a.side == "r")
    cup = root / "assets/props/cup"
    (cup / "parts").mkdir(parents=True)
    Image.new("RGBA", (40, 40), (200, 200, 200, 255)).save(cup / "parts/body.png")
    (cup / "prop.json").write_text(json.dumps({
        "kind": "PropDescriptor", "schema_version": "0.2.0", "name": "cup",
        "view_box": [0, 0, 40, 40], "origin": [20.0, 20.0],
        "bones": [{"name": "root", "x": 20.0, "y": 20.0}, {"name": "grip", "parent": "root", "x": 0.0, "y": 0.0}],
        "slots": [{"name": "body", "bone": "root", "draw_order": 0, "attachment": "body"}],
        "skins": {"default": {"name": "default", "slots": {"body": {"body": {"path": "parts/body.png", "anchor": [0.5, 0.5]}}}}},
    }), encoding="utf-8")
    cup_entity = {"kind": "prop", "id": "cup", "store": "props", "ref": "cup",
                  "stage": {"at": [300, 0], "scale": 0.5}, "overrides": {"held_by": "ned@hand_r"}}
    bend = [{"kind": "set", "target": "ned/torso/arm_r/forearm_r", "property": "rotation", "value": 1.4, "at": 0.0}]
    for actions in ([], bend):
        doc = _compile(root, _shot([cup_entity], actions, solve={"ground": 300, "mode": "pose"}))
        hand = _screen(doc, "ned/torso/arm_r/forearm_r", (r.hand[0] / ARM_W, r.hand[1] / ARM_H), t=0.5)
        grip = _screen(doc, "cup", None, t=0.5)
        assert grip == pytest.approx(hand, abs=1.0), actions


def test_the_poses_that_hid_the_part_the_face_now_draws_inside_are_dropped(tmp_path):
    root = _carved_project(tmp_path / "p")
    report = split_carved_arms(_char(root))
    assert report.dropped_poses == (("face", "x", "head"),)
    desc = json.loads((_char(root) / "character.json").read_text(encoding="utf-8"))
    assert set(desc["swap_poses"]["face"]["x"]) == {"mouth"}  # a sibling on the head stays hidden


def test_the_split_is_idempotent_and_refuses_what_it_cannot_cut(tmp_path):
    root = _carved_project(tmp_path / "p")
    split_carved_arms(_char(root))
    before = (_char(root) / "character.json").read_bytes()
    assert split_carved_arms(_char(root)).already_split
    assert (_char(root) / "character.json").read_bytes() == before
    with pytest.raises(ValueError, match="already split"):
        split_carved_arms(_char(root), elbow_at=0.4)
    with pytest.raises(ValueError, match="within 0.1..0.9"):
        split_carved_arms(_char(_carved_project(tmp_path / "q")), elbow_at=0.95)
    factory = tmp_path / "f"
    init(factory)
    new_character(factory / "assets/characters", name="ned", seed="ned", use_dicebear=False)
    with pytest.raises(ValueError, match="not raster drawings"):
        split_carved_arms(_char(factory))


def test_the_cli_runs_the_carved_split_on_raster_arms(tmp_path):
    root = _carved_project(tmp_path / "p")
    out = cli_add_forearms("ned", out_dir=str(root / "assets" / "characters"))
    assert "split the carved arms" in out and "dropped the pose face:x hiding 'head'" in out
