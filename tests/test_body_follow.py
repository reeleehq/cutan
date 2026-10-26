"""A body-attached prop follows its character's bones through the shot (cutan#104).

The `body_placement` pass places a prop that declares `metadata.body_attachment`
(no `stage.at`) from its character, once. When the character then moves in the
shot, the sockets are lowered to `pin` verbs so the solver keeps them on the
bones (and `an validate` says when motion pulls one out of reach). A shot where
nothing moves, a prop with motion of its own, and a prop placed by hand are
left as they were. No browser, no render.
"""

from __future__ import annotations

import json
import math
import tempfile
import warnings
from pathlib import Path

import pytest
from PIL import Image

from an.ir.compose import delay, sequence
from an.ir.schema import AssetRef, Shot, StagePlacement
from an.ir.validate import validate_semantic
from an.project import init, load
from an.stage.compile import compile_shot
from an.stage.solve import _local_box, joint_residuals
from an.stage.timeline import evaluate_timeline, screen_position, timeline_from_scene
from an.stage.tree import walk_children
from cutan.body_attachment import BODY_ATTACHMENT_KEY
from cutan.characters import new_character
from cutan.characters.registration import play
from cutan.compile.body import body_attachment_pins, derive_body_placements

ART = (400, 200)
PAUL_AT, PAUL_SCALE = (200.0, 300.0), 2.0
SOCKETS = [{"bone": "arm_l", "at": [0.25, -0.6]}, {"bone": "arm_r", "at": [0.75, -0.6]}]
NOD = {
    "kind": "tween",
    "target": "paul/torso",
    "property": "rotation",
    "from_value": 0.0,
    "to_value": 0.3,
    "duration": 1.0,
}


def _prop(root: Path, name: str, attachment: dict) -> None:
    d = root / "assets" / "props" / name
    (d / "parts").mkdir(parents=True)
    Image.new("RGBA", ART, (0, 0, 0, 255)).save(d / "parts" / "wheel.png")
    doc = {
        "kind": "PropDescriptor",
        "name": name,
        "slots": [{"name": "body", "bone": "root", "attachment": "wheel"}],
        "skins": {"default": {"slots": {"body": {"wheel": {"path": "parts/wheel.png"}}}}},
        "metadata": {BODY_ATTACHMENT_KEY: attachment},
    }
    (d / "prop.json").write_text(json.dumps(doc), encoding="utf-8")


@pytest.fixture(scope="module")
def project():
    with tempfile.TemporaryDirectory() as d:
        root = init(Path(d) / "p")
        new_character(root / "assets" / "characters", name="paul", seed="paul", use_dicebear=False)
        _prop(root, "wheel", {"character": "paul", "view": "front", "sockets": SOCKETS})
        _prop(
            root,
            "wheel_hips",  # a socket on a bone no part sits on
            {"character": "paul", "view": "front", "sockets": [{"bone": "root", "at": [0.5, 0.5]}] + SOCKETS},
        )
        yield load(root)


def _shot(actions=(), *, wheel_at=None, prop="wheel") -> Shot:
    wheel = AssetRef(
        kind="prop",
        id="w",
        store="props",
        ref=prop,
        stage=None if wheel_at is None else StagePlacement(at=wheel_at, scale=1.0),
    )
    paul = AssetRef(
        kind="character",
        id="paul",
        store="characters",
        ref="paul",
        stage=StagePlacement(at=PAUL_AT, scale=PAUL_SCALE),
    )
    return Shot(id="s", renderer="cutout", duration=1.0, entities=[paul, wheel], actions=list(actions))


def _pins(shot: Shot) -> list:
    return [a for a in shot.actions if getattr(a, "kind", None) == "pin"]


def _compile(project, shot):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return compile_shot(shot, project.mall, fps=24, width=640, height=480)


def test_a_character_that_moves_gets_a_pin_per_socket(project):
    shot = Shot.model_validate({**_shot([NOD]).model_dump()})
    placed = derive_body_placements(shot, project.mall)
    assert [(p.point, p.to) for p in _pins(placed)] == [
        ("w/body@0.25,-0.6", "paul/arm_l@arm_l"),
        ("w/body@0.75,-0.6", "paul/arm_r@arm_r"),
    ]
    assert placed.entities[1].stage.at is not None  # still placed by its body


@pytest.mark.parametrize(
    "why, shot",
    [
        ("nothing moves", lambda: _shot()),
        ("only a look changes", lambda: _shot([{"kind": "tween", "target": "paul/torso", "property": "alpha", "from_value": 1.0, "to_value": 0.5, "duration": 1.0}])),
        ("the prop has motion of its own", lambda: _shot([NOD, {"kind": "tween", "target": "w", "property": "rotation", "from_value": 0.0, "to_value": 0.3, "duration": 1.0}])),
        ("it is placed by hand", lambda: _shot([NOD], wheel_at=(200.0, 140.0))),
        ("a socket's bone carries no part", lambda: _shot([NOD], prop="wheel_hips")),
    ],
)
def test_no_pins_when_there_is_nothing_to_follow_or_nowhere_to_follow(project, why, shot):
    assert _pins(derive_body_placements(shot(), project.mall)) == [], why


def test_a_still_shot_compiles_to_the_scene_it_did(project):
    doc = _compile(project, _shot())
    assert "solve" not in (doc.meta.extensions or {})


def test_the_sockets_stay_on_the_shoulders_at_every_frame_of_a_nod(project):
    shot = _shot([NOD])
    doc = _compile(project, shot)
    report = doc.meta.extensions["solve"]
    assert report["dropped"] == []
    expanded = derive_body_placements(shot, project.mall)
    puppet, times, gaps, _ = joint_residuals(doc, expanded, project.mall)
    pins = [j for j, row in enumerate(puppet.rows) if row.source == "pin"]
    assert len(pins) == 2 and len(times) == 25
    assert max(gaps[k][j] for k in range(len(times)) for j in pins) < 0.25
    # ...and the prop really moved with them: it is not a held pose
    nodes = dict(walk_children(doc.scene))
    timeline = timeline_from_scene(doc)
    left, top, w, h = _local_box(nodes["w/body"])
    at = lambda t: screen_position(  # noqa: E731
        doc, "w/body", pose=evaluate_timeline(timeline, t), point=(left + w / 2, top + h / 2)
    )
    assert math.dist(at(0.0), at(1.0)) > 5


def test_the_joint_checks_pass_for_an_ordinary_nod(project):
    scene = project.scene.model_copy(update={"timeline": [_shot([NOD])]})
    report = validate_semantic(
        scene,
        available_characters=project.mall["characters"],
        available_props=project.mall["props"],
        available_environments=project.mall["environments"],
        only={"unknown_body", "unreachable_pin", "joint_violation"},
    )
    assert [f.description for f in report.findings] == []


def test_the_consistency_check_is_a_constraint_with_the_name_it_had():
    from cutan.genre import CUTOUT
    from cutan.verify.body import BODY_ATTACHMENT_CONSISTENCY

    assert BODY_ATTACHMENT_CONSISTENCY.term is None  # lint-only: placement is derived
    registered = {c.name: c for c in CUTOUT.checks}["cutout.body_attachment_consistency"]
    assert (registered.stage, registered.order) == ("finish", 11)


#: Sockets whose spacing does not match the shoulders': no placement fits both.
SKEWED = [{"bone": "arm_l", "at": [0.25, -0.6]}, {"bone": "arm_r", "at": [0.75, -0.1]}]


def _validate(project, shot, only):
    scene = project.scene.model_copy(update={"timeline": [shot]})
    return validate_semantic(
        scene,
        available_characters=project.mall["characters"],
        available_props=project.mall["props"],
        available_environments=project.mall["environments"],
        only=only,
    )


def test_sockets_that_do_not_fit_the_bones_are_placed_once_and_validate_says_so(tmp_path):
    root = init(tmp_path / "p")
    new_character(root / "assets" / "characters", name="paul", seed="paul", use_dicebear=False)
    _prop(root, "wheel_skew", {"character": "paul", "view": "front", "sockets": SKEWED})
    project = load(root)
    shot = _shot([NOD], prop="wheel_skew")
    assert _pins(derive_body_placements(shot, project.mall)) == []
    report = _validate(project, shot, {"cutout.body_attachment"})
    messages = [(f.severity, f.description) for f in report.findings]
    assert any(
        sev == "warning" and "not followed through the shot" in text and "px from the bones" in text
        for sev, text in messages
    ), messages


def test_a_prop_with_motion_of_its_own_is_noted_not_warned(project):
    own = {"kind": "tween", "target": "w", "property": "rotation", "from_value": 0.0, "to_value": 0.3, "duration": 1.0}
    report = _validate(project, _shot([NOD, own]), {"cutout.body_attachment"})
    assert [f.severity for f in report.findings if "not followed" in f.description] == ["info"]


def test_validate_says_when_the_motion_pulls_a_followed_socket_off_its_bone(project):
    """The lowered pins are added at compile, so the core joint checks never see
    them: `cutout.body_attachment` reads the compiled shot's solve report. A
    character stretched sideways while it wears a rigid prop pulls a socket off."""
    stretch = {
        "kind": "tween",
        "target": "paul",
        "property": "scale_x",
        "from_value": PAUL_SCALE,
        "to_value": PAUL_SCALE * 1.4,
        "duration": 1.0,
    }
    shot = _shot([stretch])
    assert _compile(project, shot).meta.extensions["solve"]["dropped"]
    report = _validate(project, shot, {"cutout.body_attachment"})
    said = [f.description for f in report.findings if "cannot stay on its bone" in f.description]
    assert said and "px off" in said[0] and " s to " in said[0], [f.description for f in report.findings]
    # and a nod it can follow is silent
    quiet = _validate(project, _shot([NOD]), {"cutout.body_attachment"})
    assert [f for f in quiet.findings if "bone" in f.description and "socket" in f.description] == []


# --- a view change mid-shot (cutan#98) -----------------------------------------


def _swap_said(project, actions):
    report = _validate(project, _shot(actions), {"cutout.body_attachment"})
    return [f.description for f in report.findings if "changes to the" in f.description]


def test_validate_says_when_the_character_changes_view_under_a_prop_drawn_from_the_front(project):
    set_side = {"kind": "set", "target": "paul", "property": "view", "value": "side", "at": 0.5}
    said = _swap_said(project, [set_side])
    assert len(said) == 1 and "'side' view at 0.50 s" in said[0], said
    turn = sequence(delay(0.4), play("paul", "turn", args={"to": "side"}))
    said = _swap_said(project, [turn])
    assert len(said) == 1 and "0.55 s" in said[0], said


def test_a_view_that_never_changes_or_changes_at_the_start_is_not_a_swap(project):
    at_start = {"kind": "set", "target": "paul", "property": "view", "value": "front", "at": 0.5}
    assert _swap_said(project, [at_start]) == []  # to the view the art shows
    assert _swap_said(project, [NOD]) == []
