"""A character's hands as named points for the core's hold verbs (an#502, cutan#104).

`cutan.characters.hands.character_landmarks` names `hand_l` / `hand_r` for any
character rig; the core resolves `ned@hand_r` through `EntityKind.landmarks`.
Held to the compiled shot: a factory character grasps a cup off a crate and its
hand is on the cup's grip at the frame it takes it, with a one-piece arm and
with an elbow (`nesting: bones`). No browser, no render.
"""

from __future__ import annotations

import json
import math
import warnings
from pathlib import Path

import pytest

from an.ir.schema import Shot
from an.project import init, load
from an.stage.compile import compile_shot
from an.stage.timeline import evaluate_timeline, screen_position, timeline_from_scene
from cutan.characters import new_character
from cutan.characters.hands import character_landmarks

W, H = 640, 480

CUP = {
    "kind": "PropDescriptor",
    "schema_version": "0.2.0",
    "name": "cup",
    "view_box": [0, 0, 400, 400],
    "origin": [200.0, 200.0],
    "bones": [
        {"name": "root", "x": 200.0, "y": 200.0},
        {"name": "grip", "parent": "root", "x": 30.0, "y": 0.0},
    ],
    "slots": [{"name": "body", "bone": "root", "draw_order": 0, "attachment": "body"}],
    "skins": {
        "default": {
            "name": "default",
            "slots": {
                "body": {"body": {"path": "parts/body.svg", "anchor": [0.5, 0.5]}}
            },
        }
    },
}


def _project(root: Path, *, elbow: bool) -> Path:
    init(root)
    chars = root / "assets" / "characters"
    new_character(chars, name="ned", seed="ned", use_dicebear=False, feet_origin=True)
    if elbow:
        _split_arm(chars / "ned")
    cup = root / "assets" / "props" / "cup"
    (cup / "parts").mkdir(parents=True)
    (cup / "prop.json").write_text(json.dumps(CUP), encoding="utf-8")
    (cup / "parts" / "body.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 100" width="80" height="100"><rect width="80" height="100" fill="#c33"/></svg>',
        encoding="utf-8",
    )
    return root


def _split_arm(d: Path) -> None:
    """The skill's recipe: an elbow on the right arm (a forearm under `nesting: bones`)."""
    from cutan.characters.schema import Attachment, Bone, CharacterDescriptor, Slot

    desc = CharacterDescriptor.model_validate_json((d / "character.json").read_text())
    svg = (d / "parts/arm_r.svg").read_text()
    box = 'viewBox="0 0 64 256" width="64" height="256"'
    (d / "parts/upper_r.svg").write_text(
        svg.replace(box, 'viewBox="0 0 64 128" width="64" height="128"')
    )
    (d / "parts/fore_r.svg").write_text(
        svg.replace(box, 'viewBox="0 128 64 128" width="64" height="128"')
    )
    desc.nesting = "bones"
    desc.skins["default"].slots["arm_r"]["arm_r"] = Attachment(
        path="parts/upper_r.svg", anchor=(0.5, 0.0)
    )
    desc.bones.append(Bone(name="fore_r", parent="arm_r", y=128, rotation_deg=-20))
    desc.slots.append(
        Slot(name="fore_r", bone="fore_r", draw_order=2, attachment="fore_r")
    )
    desc.skins["default"].slots["fore_r"] = {
        "fore_r": Attachment(path="parts/fore_r.svg", anchor=(0.5, 0.0))
    }
    (d / "character.json").write_text(desc.model_dump_json(indent=2))


def _shot(cup_at: tuple[float, float]) -> Shot:
    return Shot.model_validate(
        {
            "id": "s",
            "duration": 2.0,
            "entities": [
                {
                    "kind": "character",
                    "id": "ned",
                    "store": "characters",
                    "ref": "ned",
                    "stage": {"at": [0, 150]},
                },
                {
                    "kind": "prop",
                    "id": "cup",
                    "store": "props",
                    "ref": "cup",
                    "stage": {"at": list(cup_at), "scale": 0.3, "after": "ned"},
                },
            ],
            "actions": [
                {"kind": "grasp", "by": "ned@hand_r", "item": "cup", "start": 0.3}
            ],
        }
    )


def test_a_character_rig_names_its_hands():
    one_piece = {
        "bones": [{"name": "arm_r"}, {"name": "arm_l"}],
        "slots": [
            {"name": "arm_r", "bone": "arm_r"},
            {"name": "arm_l", "bone": "arm_l"},
        ],
    }
    assert character_landmarks(one_piece) == {
        "hand_l": ("arm_l", None),
        "hand_r": ("arm_r", None),
    }
    with_bone = dict(
        one_piece, bones=[*one_piece["bones"], {"name": "hand_r", "parent": "arm_r"}]
    )
    assert "hand_r" not in character_landmarks(
        with_bone
    )  # a hand bone is read by the core
    assert character_landmarks({"bones": [], "slots": []}) == {}


@pytest.mark.parametrize("elbow", [False, True], ids=["one-piece arm", "elbow"])
def test_a_character_takes_a_cup_by_its_hand(tmp_path, elbow):
    project = load(_project(tmp_path / "p", elbow=elbow))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        doc = compile_shot(_shot((70.0, 60.0)), project.mall, fps=24, width=W, height=H)
    holds = doc.meta.extensions["solve"]["holds"]
    (g,) = holds["gestures"]
    assert g["by"] == "ned@hand_r" and g["gap"] <= 0.5, g
    contact = round(g["contact"] * 24) / 24
    pose = evaluate_timeline(timeline_from_scene(doc), contact)
    k = 345.0 / 400.0 * 0.3  # the cup's scene px per view-box unit at stage scale 0.3
    grip = screen_position(doc, "cup", pose=pose, point=(30.0 * 345.0 / 400.0, 0.0))
    hand = holds["gestures"][0]["hand"]
    assert math.dist(grip, (hand[0] + W / 2, hand[1] + H / 2)) < 0.5 + k
