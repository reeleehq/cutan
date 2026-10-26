"""Hinge limits per part type (cutan#104): the table, the factory step, and what a range does in the solver.

No browser, no render: the shots are compiled and the poses read from the
compiled timeline, as `test_hands.py` does.
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
from an.stage.solve import _local_box, _pivot
from an.stage.timeline import evaluate_timeline, screen_position, timeline_from_scene
from an.stage.tree import walk_children
from cutan.characters import new_character
from cutan.characters.factory import _replayable, add_limits
from cutan.characters.limits import (
    GENRE_LIMITS,
    LOOSE_LIMITS,
    apply_limits,
    limits_for,
    limits_table,
    part_type,
)
from cutan.characters.schema import Bone

W, H = 640, 480


@pytest.mark.parametrize(
    "bone, kind",
    [
        ("head", "neck"),
        ("arm_l", "shoulder"),
        ("upper_arm_r", "shoulder"),
        ("forearm_r", "elbow"),
        ("fore_l", "elbow"),
        ("hand_r", "wrist"),
        ("leg_l", "hip"),
        ("shin_r", "knee"),
        ("torso", None),
        ("root", None),
        ("grip", None),
    ],
)
def test_a_bone_has_the_part_type_its_name_says(bone, kind):
    assert part_type(bone) == kind


def test_the_left_side_is_the_mirror_of_the_right():
    for name in ("arm", "forearm", "hand", "leg", "shin"):
        lo, hi = limits_for(f"{name}_r")
        assert limits_for(f"{name}_l") == (-hi, -lo)
    assert limits_for("head") == GENRE_LIMITS["neck"]  # not sided: the same both ways


def test_an_elbow_folds_inward():
    """Positive turns clockwise on screen: a right arm's hand swings toward the body."""
    lo, hi = limits_for("forearm_r")
    assert hi > 90 > 0 > lo > -30
    lo, hi = limits_for("forearm_l")
    assert lo < -90 < 0 < hi < 30


def test_a_style_overrides_by_part_type_and_nothing_else():
    table = limits_table({"joints": {"limits": {"elbow": [0, 90]}}})
    assert table["elbow"] == (0.0, 90.0)
    assert {k: v for k, v in table.items() if k != "elbow"} == {
        k: v for k, v in GENRE_LIMITS.items() if k != "elbow"
    }
    with pytest.raises(ValueError, match="unknown part type 'tail'"):
        limits_table({"joints": {"limits": {"tail": [0, 10]}}})
    with pytest.raises(ValueError, match="-180 <= lo <= hi <= 180"):
        limits_table({"joints": {"limits": {"elbow": [0, 270]}}})
    with pytest.raises(ValueError, match="\\[lo, hi\\]"):
        limits_table({"joints": {"limits": {"elbow": 90}}})


def test_the_loose_table_covers_every_part_type_and_contains_the_genre_ranges():
    assert set(LOOSE_LIMITS) == set(GENRE_LIMITS)
    for kind, (lo, hi) in GENRE_LIMITS.items():
        assert LOOSE_LIMITS[kind][0] <= lo and hi <= LOOSE_LIMITS[kind][1]


def test_an_artists_range_is_kept_unless_overwritten():
    rig = [Bone(name="head", limits=(-10, 10)), Bone(name="arm_r")]
    assert apply_limits(rig) == ["arm_r"]
    assert rig[0].limits == (-10, 10)
    assert apply_limits(rig, overwrite=True) == ["head", "arm_r"]
    assert rig[0].limits == GENRE_LIMITS["neck"]


# -----------------------------------------------------------------------------
# the factory step
# -----------------------------------------------------------------------------


def _character(root: Path, *, limits: bool, style: str | None = None) -> Path:
    init(root)
    chars = root / "assets" / "characters"
    new_character(chars, name="ned", seed="ned", use_dicebear=False, feet_origin=True)
    if limits:
        add_limits(chars / "ned", style=style)
    return root


def _bones(root: Path) -> dict[str, list | None]:
    desc = json.loads(
        (root / "assets/characters/ned/character.json").read_text(encoding="utf-8")
    )
    return {b["name"]: b.get("limits") for b in desc["bones"]}


def test_a_new_character_carries_no_limits(tmp_path):
    """The default factory character is as it was: its contract hashes must not move."""
    assert set(_bones(_character(tmp_path / "p", limits=False)).values()) == {None}


def test_add_limits_writes_the_typed_bones_only_and_is_idempotent(tmp_path):
    root = _character(tmp_path / "p", limits=True)
    first = (root / "assets/characters/ned/character.json").read_bytes()
    assert _bones(root) == {
        "root": None,
        "torso": None,
        "head": [-45.0, 45.0],
        "arm_l": [-60.0, 180.0],
        "arm_r": [-180.0, 60.0],
        "leg_l": [-80.0, 80.0],
        "leg_r": [-80.0, 80.0],
    }
    add_limits(root / "assets/characters/ned")
    assert (root / "assets/characters/ned/character.json").read_bytes() == first


def test_add_limits_is_a_replayable_step_of_the_recipe(tmp_path):
    root = _character(tmp_path / "p", limits=True)
    desc = json.loads(
        (root / "assets/characters/ned/character.json").read_text(encoding="utf-8")
    )
    steps = _replayable(desc["metadata"])
    assert steps is not None and [c for c, _ in steps][-1] == "add_limits"


def test_add_limits_refuses_a_style_that_does_not_ship(tmp_path):
    root = _character(tmp_path / "p", limits=False)
    with pytest.raises(ValueError, match="no style spec named 'pixar'"):
        add_limits(root / "assets/characters/ned", style="pixar")


# -----------------------------------------------------------------------------
# what a range does in the solver
# -----------------------------------------------------------------------------


def _compile(root: Path, actions: list[dict]):
    shot = Shot.model_validate(
        {
            "id": "s",
            "duration": 1.0,
            "entities": [
                {
                    "kind": "character",
                    "id": "ned",
                    "store": "characters",
                    "ref": "ned",
                    "stage": {"at": [0, 150]},
                }
            ],
            "actions": actions,
        }
    )
    project = load(root)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return compile_shot(shot, project.mall, fps=24, width=W, height=H)


def _head_tip(doc, t):
    nodes = dict(walk_children(doc.scene))
    left, top, w, _ = _local_box(nodes["ned/head"])
    pose = evaluate_timeline(timeline_from_scene(doc), t)
    return screen_position(doc, "ned/head", pose=pose, point=(left + w / 2, top))


def _turn_the_head_to(root: Path, degrees: float):
    """Pin the top of the head to where turning it ``degrees`` about the neck puts it."""
    rest = _compile(root, [])
    nodes = dict(walk_children(rest.scene))
    pose = evaluate_timeline(timeline_from_scene(rest), 0.0)
    neck = screen_position(
        rest, "ned/head", pose=pose, point=_pivot(nodes["ned/head"])
    )
    tip = _head_tip(rest, 0.0)
    a = math.radians(degrees)
    dx, dy = tip[0] - neck[0], tip[1] - neck[1]
    goal = (
        neck[0] + dx * math.cos(a) - dy * math.sin(a),
        neck[1] + dx * math.sin(a) + dy * math.cos(a),
    )
    doc = _compile(
        root,
        [
            {
                "kind": "pin",
                "point": "ned/head@0.5,0",
                "to": [goal[0] - W / 2, goal[1] - H / 2],
            }
        ],
    )
    return doc, goal


@pytest.mark.parametrize("limits", [False, True], ids=["free", "limited"])
def test_a_turn_inside_the_neck_range_is_reached_with_or_without_it(tmp_path, limits):
    root = _character(tmp_path / "p", limits=limits)
    doc, goal = _turn_the_head_to(root, 30)
    assert doc.meta.extensions["solve"]["dropped"] == []
    assert math.dist(_head_tip(doc, 1.0), goal) < 0.5


def test_a_turn_beyond_the_neck_range_is_refused_only_when_the_neck_has_one(tmp_path):
    free, goal = _turn_the_head_to(_character(tmp_path / "a", limits=False), 70)
    assert free.meta.extensions["solve"]["dropped"] == []
    assert math.dist(_head_tip(free, 1.0), goal) < 0.5
    limited, goal = _turn_the_head_to(_character(tmp_path / "b", limits=True), 70)
    (dropped,) = limited.meta.extensions["solve"]["dropped"]
    assert dropped["gap"] > 10  # the pin was given up, the head stays inside its range
    assert math.dist(_head_tip(limited, 1.0), goal) > 10


def test_limits_change_nothing_in_a_shot_that_declares_no_joint(tmp_path):
    """The range acts only where a shot declares a joint: same scene, byte for byte."""
    nod = [{"kind": "tween", "target": "ned/head", "property": "rotation", "to_value": 1.4, "duration": 0.5}]
    docs = [
        _compile(_character(tmp_path / name, limits=limits), nod)
        for name, limits in (("free", False), ("limited", True))
    ]
    assert docs[0].scene.model_dump_json() == docs[1].scene.model_dump_json()
    assert docs[0].meta.extensions.get("solve") == docs[1].meta.extensions.get("solve")
