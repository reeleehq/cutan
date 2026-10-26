"""A factory character's split arm, its hands, and a prop's grip points (cutan#104).

`add_forearms` cuts each arm at the elbow and gives it a hand (bones `forearm_*`,
`hand_*`, `nesting: bones`); the acceptance case is the steering wheel: a prop
with two grip bones, the hands pinned to them, the torso nodding and the wheel
turning, held at every frame of a two-shot and of a close-up. No browser, no
render: shots are compiled and the joints measured on the compiled nodes.
"""

from __future__ import annotations

import json
import math
import shutil
import warnings
from pathlib import Path

import pytest

from an.ir.schema import Shot
from an.ir.validate import validate_semantic
from an.project import init, load
from an.stage.compile import compile_shot
from an.stage.solve import _local_box, _pivot, joint_residuals
from an.stage.timeline import evaluate_timeline, screen_position, timeline_from_scene
from an.stage.tree import walk_children
from cutan.characters import new_character
from cutan.characters.factory import _replayable, add_forearms, add_limits, add_views
from cutan.characters.hands import character_landmarks
from cutan.characters.validate import validate_character

W, H = 640, 480
JOINT_CHECKS = {"unknown_body", "unreachable_pin", "joint_violation"}

WHEEL = {
    "kind": "PropDescriptor",
    "schema_version": "0.2.0",
    "name": "wheel",
    "view_box": [0, 0, 400, 400],
    "origin": [200.0, 200.0],
    "bones": [
        {"name": "root", "x": 200.0, "y": 200.0},
        {"name": "grip_l", "parent": "root", "x": -50.0, "y": 0.0},
        {"name": "grip_r", "parent": "root", "x": 50.0, "y": 0.0},
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
RIM = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" width="400" '
    'height="400"><circle cx="200" cy="200" r="190" fill="none" stroke="#333" '
    'stroke-width="30"/></svg>'
)


def _project(root: Path, *, split: bool = True, views: bool = False) -> Path:
    init(root)
    chars = root / "assets" / "characters"
    new_character(chars, name="ned", seed="ned", use_dicebear=False, feet_origin=True)
    if split:
        add_forearms(chars / "ned")
    wheel = root / "assets" / "props" / "wheel"
    (wheel / "parts").mkdir(parents=True)
    (wheel / "prop.json").write_text(json.dumps(WHEEL), encoding="utf-8")
    (wheel / "parts" / "body.svg").write_text(RIM, encoding="utf-8")
    return root


def _compile(root: Path, shot: Shot):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return compile_shot(shot, load(root).mall, fps=24, width=W, height=H)


def _character_shot(actions: list[dict] | None = None, **stage) -> Shot:
    return Shot.model_validate(
        {
            "id": "s",
            "duration": 1.0,
            "entities": [
                {
                    "kind": "character",
                    "id": "ned",
                    "store": "characters",
                    "ref": "ned",
                    "stage": {"at": [0, 150], **stage},
                }
            ],
            "actions": actions or [],
        }
    )


def _desc(root: Path) -> dict:
    return json.loads(
        (root / "assets/characters/ned/character.json").read_text(encoding="utf-8")
    )


# -----------------------------------------------------------------------------
# the factory step
# -----------------------------------------------------------------------------


def test_a_new_character_keeps_its_one_piece_arms(tmp_path):
    desc = _desc(_project(tmp_path / "p", split=False))
    assert not {"forearm_l", "forearm_r", "hand_l", "hand_r"} & {
        b["name"] for b in desc["bones"]
    }
    assert desc.get("nesting") is None


def test_add_forearms_adds_the_bones_slots_and_art_and_nests_by_bones(tmp_path):
    root = _project(tmp_path / "p")
    desc = _desc(root)
    bones = {b["name"]: b for b in desc["bones"]}
    for side in "lr":
        assert bones[f"forearm_{side}"]["parent"] == f"arm_{side}"
        assert bones[f"hand_{side}"]["parent"] == f"forearm_{side}"
        for part in ("arm", "forearm", "hand"):
            assert (root / f"assets/characters/ned/parts/{part}_{side}.svg").is_file()
    assert desc["nesting"] == "bones" and desc["metadata"]["arms"] == "split"
    slots = {s["name"]: s for s in desc["slots"]}
    assert slots["forearm_r"]["draw_order"] > slots["arm_r"]["draw_order"]
    assert slots["hand_r"]["draw_order"] > slots["forearm_r"]["draw_order"]


def test_the_split_arm_is_the_one_piece_arm_at_rest(tmp_path):
    """The head stays where it was and the hand's centre is where the old hand circle was."""
    one = _compile(_project(tmp_path / "one", split=False), _character_shot())
    two = _compile(_project(tmp_path / "two"), _character_shot())

    def at(doc, path, *, end=False):
        nodes = dict(walk_children(doc.scene))
        pose = evaluate_timeline(timeline_from_scene(doc), 0.0)
        left, top, w, h = _local_box(nodes[path])
        point = (left + w / 2, top + h) if end else _pivot(nodes[path])
        return screen_position(doc, path, pose=pose, point=point)

    assert at(one, "ned/head") == at(two, "ned/torso/head")
    wrist_before = at(one, "ned/arm_r", end=True)
    wrist_after = at(two, "ned/torso/arm_r/forearm_r/hand_r")
    # the old circle's centre is `hand_radius` above the arm art's bottom edge
    assert wrist_after[0] == pytest.approx(wrist_before[0], abs=0.01)
    assert wrist_before[1] - wrist_after[1] == pytest.approx(
        20 * 345 / 1024 + 4 * 345 / 1024, abs=0.5
    )


def test_add_forearms_is_idempotent_and_a_replayable_recipe_step(tmp_path):
    root = _project(tmp_path / "p")
    path = root / "assets/characters/ned"
    before = (path / "character.json").read_bytes()
    add_forearms(path)
    assert (path / "character.json").read_bytes() == before
    steps = _replayable(_desc(root)["metadata"])
    assert steps is not None and "add_forearms" in [c for c, _ in steps]


def test_add_forearms_refuses_an_arm_it_did_not_draw(tmp_path):
    root = _project(tmp_path / "p", split=False)
    arm = root / "assets/characters/ned/parts/arm_r.svg"
    arm.write_text(arm.read_text(encoding="utf-8").replace("<g ", "<g data-x='1' "))
    with pytest.raises(ValueError, match="not the factory's drawing"):
        add_forearms(root / "assets/characters/ned")
    with pytest.raises(ValueError, match="leaves no sleeve"):
        add_forearms(root / "assets/characters/ned", elbow_at=1.5)


@pytest.mark.parametrize("build", ["regular", "squat", "stick", "tall"])
def test_the_elbow_can_be_cut_anywhere_the_build_leaves_a_sleeve(tmp_path, build):
    from cutan.characters.factory import BUILDS, _elbow_bounds

    lo, hi = _elbow_bounds(BUILDS[build])
    for at in (lo, hi):
        root = tmp_path / f"{build}-{at:.2f}"
        init(root)
        chars = root / "assets" / "characters"
        new_character(chars, name="ned", seed="ned", use_dicebear=False, build=build)
        add_forearms(chars / "ned", elbow_at=at)
        assert validate_character(chars / "ned", name="ned").findings == []
    again = tmp_path / f"{build}-past"
    init(again)
    new_character(again / "assets/characters", name="ned", seed="ned", use_dicebear=False, build=build)
    with pytest.raises(ValueError, match="leaves no sleeve"):
        add_forearms(again / "assets/characters/ned", elbow_at=hi + 0.05)


def test_a_second_cut_at_another_place_is_refused_not_ignored(tmp_path):
    root = _project(tmp_path / "p")
    with pytest.raises(ValueError, match="already split"):
        add_forearms(root / "assets/characters/ned", elbow_at=0.3)


def test_a_split_character_validates_and_takes_its_limits_and_views(tmp_path):
    root = _project(tmp_path / "p")
    path = root / "assets/characters/ned"
    add_limits(path)
    add_views(path)  # views after the split: the hidden arm hides its hand
    report = validate_character(path, name="ned")
    assert report.passed and report.findings == [], [f.description for f in report.findings]
    bones = {b["name"]: b.get("limits") for b in _desc(root)["bones"]}
    assert bones["forearm_r"] == [-10.0, 150.0] and bones["forearm_l"] == [-150.0, 10.0]
    assert bones["hand_r"] == [-70.0, 70.0]
    for view in ("side", "three_quarter", "back"):
        doc = _compile(
            root,
            _character_shot(
                [{"kind": "set", "target": "ned", "property": "view", "value": view}]
            ),
        )
        assert any(p.endswith("hand_l") for p, _ in walk_children(doc.scene))


def test_a_hand_bone_is_read_by_the_core_and_the_hands_stay_named(tmp_path):
    desc = _desc(_project(tmp_path / "p"))
    assert character_landmarks(desc) == {}  # the bones are read first


# -----------------------------------------------------------------------------
# the steering wheel: grips, pinned hands, a nodding torso, a turning wheel
# -----------------------------------------------------------------------------

#: (stage.scale, the wheel's y): a two-shot, and a close-up on the same driver.
FRAMINGS = {"two_shot": (1.0, 20.0), "close_up": (1.6, -64.0)}


def _wheel_shot(scale: float, wheel_y: float, *, pins: bool = True) -> Shot:
    actions = [
        {
            "kind": "tween",
            "target": "ned/torso",
            "property": "rotation",
            "from_value": 0.0,
            "to_value": 0.12,
            "duration": 1.0,
        },
        {
            "kind": "tween",
            "target": "wheel",
            "property": "rotation",
            "from_value": 0.0,
            "to_value": 0.7,
            "duration": 1.0,
        },
    ]
    if pins:
        actions += [
            {"kind": "pin", "point": "ned/hand_l@hand_l", "to": "wheel@grip_l"},
            {"kind": "pin", "point": "ned/hand_r@hand_r", "to": "wheel@grip_r"},
        ]
    return Shot.model_validate(
        {
            "id": "s",
            "duration": 1.0,
            "entities": [
                {
                    "kind": "character",
                    "id": "ned",
                    "store": "characters",
                    "ref": "ned",
                    "stage": {"at": [0, 150], "scale": scale},
                },
                {
                    "kind": "prop",
                    "id": "wheel",
                    "store": "props",
                    "ref": "wheel",
                    "stage": {"at": [0, wheel_y], "scale": scale, "after": "ned"},
                },
            ],
            "actions": actions,
        }
    )


@pytest.mark.parametrize("framing", FRAMINGS)
def test_both_hands_are_on_the_wheel_at_every_frame(tmp_path, framing):
    root = _project(tmp_path / "p")
    shot = _wheel_shot(*FRAMINGS[framing])
    doc = _compile(root, shot)
    assert doc.meta.extensions["solve"]["dropped"] == []
    puppet, times, gaps, excess = joint_residuals(doc, shot, load(root).mall)
    pins = [j for j, row in enumerate(puppet.rows) if "pin" in str(row.id)]
    assert len(pins) == 2 and len(times) == 25
    assert max(gaps[k][j] for k in range(len(times)) for j in pins) < 0.25
    assert all(e == 0 for row in excess for e in row)


@pytest.mark.parametrize("framing", FRAMINGS)
def test_the_wheel_case_passes_the_joint_checks(tmp_path, framing):
    root = _project(tmp_path / "p")
    project = load(root)
    scene = project.scene.model_copy(update={"timeline": [_wheel_shot(*FRAMINGS[framing])]})
    report = validate_semantic(
        scene,
        available_characters=project.mall["characters"],
        available_props=project.mall["props"],
        available_environments=project.mall["environments"],
        only=JOINT_CHECKS,
    )
    assert [f.description for f in report.findings] == []


def test_the_wheel_really_turns_and_the_torso_really_nods(tmp_path):
    """The hold is not a held pose: the hands travel with the grips."""
    root = _project(tmp_path / "p")
    doc = _compile(root, _wheel_shot(1.0, 20.0))
    timeline = timeline_from_scene(doc)
    nodes = dict(walk_children(doc.scene))
    hand = "ned/torso/arm_r/forearm_r/hand_r"
    at = lambda t: screen_position(  # noqa: E731
        doc, hand, pose=evaluate_timeline(timeline, t), point=_pivot(nodes[hand])
    )
    assert math.dist(at(0.0), at(1.0)) > 10


def test_a_grip_beyond_reach_is_refused_with_where_to_put_it(tmp_path):
    root = _project(tmp_path / "p")
    shot = _wheel_shot(1.0, 20.0)
    far = shot.model_copy(
        update={
            "entities": [
                e.model_copy(update={"stage": e.stage.model_copy(update={"at": (0.0, -150.0)})})
                if e.id == "wheel"
                else e
                for e in shot.entities
            ]
        }
    )
    project = load(root)
    scene = project.scene.model_copy(update={"timeline": [far]})
    report = validate_semantic(
        scene,
        available_characters=project.mall["characters"],
        available_props=project.mall["props"],
        available_environments=project.mall["environments"],
        only={"unreachable_pin"},
    )
    messages = [f.description for f in report.findings]
    assert messages and "Move the target within reach" in messages[0], messages


def test_the_old_one_piece_character_is_untouched_by_all_of_it(tmp_path):
    """A rig without the new bones compiles to the very scene it did (no joint declared)."""
    root = _project(tmp_path / "p", split=False)
    doc = _compile(root, _character_shot())
    assert "forearm" not in doc.scene.model_dump_json()
    assert "solve" not in (doc.meta.extensions or {})


def test_a_hand_takes_a_cup_by_its_hand_bone(tmp_path):
    """The hold verbs name the hand as before (`ned@hand_r`); the bone is what they reach with."""
    from tests.test_hands import CUP, _shot

    root = _project(tmp_path / "p")
    cup = root / "assets" / "props" / "cup"
    (cup / "parts").mkdir(parents=True)
    (cup / "prop.json").write_text(json.dumps(CUP), encoding="utf-8")
    (cup / "parts" / "body.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 100" width="80" height="100"><rect width="80" height="100" fill="#c33"/></svg>',
        encoding="utf-8",
    )
    doc = _compile(root, _shot((50.0, 60.0)))
    (g,) = doc.meta.extensions["solve"]["holds"]["gestures"]
    assert g["by"] == "ned@hand_r" and g["gap"] <= 0.5, g
    contact = g["contact"]
    nodes = dict(walk_children(doc.scene))
    pose = evaluate_timeline(timeline_from_scene(doc), contact)
    hand = "ned/torso/arm_r/forearm_r/hand_r"
    at_hand = screen_position(doc, hand, pose=pose, point=_pivot(nodes[hand]))
    grip = screen_position(doc, "cup", pose=pose, point=(30.0 * 345.0 / 400.0, 0.0))
    assert math.dist(at_hand, grip) < 1.0  # the hold converges to its own 0.5 px gap


def test_a_preset_drives_the_joined_rig_and_is_unchanged_without_joints(tmp_path):
    """`nod` is a driver (cutan#104): with the hands pinned the solver keeps them
    on the grips while the head nods, and the preset's own keys are the same
    whether or not joints are declared."""
    root = _project(tmp_path / "p")
    nod = {"kind": "play", "target": "ned", "animation": "nod", "start": 0.2}
    free = _wheel_shot(1.0, 20.0, pins=False)
    pinned = _wheel_shot(1.0, 20.0)
    with_nod = [*free.actions, nod.copy()]
    free = free.model_copy(update={"actions": Shot.model_validate({**free.model_dump(), "actions": with_nod}).actions})
    pinned = pinned.model_copy(
        update={"actions": Shot.model_validate({**pinned.model_dump(), "actions": [*pinned.actions, nod]}).actions}
    )
    bare, joined = _compile(root, free), _compile(root, pinned)
    assert "solve" not in (bare.meta.extensions or {})
    assert joined.meta.extensions["solve"]["dropped"] == []
    puppet, times, gaps, _ = joint_residuals(joined, pinned, load(root).mall)
    pins = [j for j, row in enumerate(puppet.rows) if "pin" in str(row.id)]
    assert max(gaps[k][j] for k in range(len(times)) for j in pins) < 0.25
    keep = {k: v.model_dump() for k, v in bare.animations.items()}
    assert keep and all(joined.animations[k].model_dump() == v for k, v in keep.items())
