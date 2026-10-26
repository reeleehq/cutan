"""The marionette style: a figure hung from a control bar (cutan#104).

The style spec's `joints` block, `cutan.marionette.marionette_joints` and the
control bar, held to a compiled shot: the bar is tweened, the figure follows on
its strings, swings and settles; no string is stretched past its length and no
hinge is bent past its range. No browser, no render.
"""

from __future__ import annotations

import json
import math
import warnings
from pathlib import Path

import pytest

from an.ir.schema import Shot
from an.ir.validate import validate_semantic
from an.project import init, load
from an.stage.compile import compile_shot
from an.stage.solve import joint_residuals
from an.stage.timeline import evaluate_timeline, screen_position, timeline_from_scene
from cutan.characters import new_character
from cutan.characters.factory import add_limits
from cutan.marionette import marionette_joints, write_control_bar
from cutan.styles import style_spec

W, H = 640, 480


def test_a_figure_is_tied_by_head_hands_and_knees_and_hinged_at_the_hips():
    joints = marionette_joints("ned", "bar")
    assert [j["name"] for j in joints] == [
        "ned.hip_l",
        "ned.hip_r",
        "ned.head",
        "ned.hand_l",
        "ned.hand_r",
        "ned.knee_l",
        "ned.knee_r",
    ]
    assert {j["type"] for j in joints[:2]} == {"hinge"}
    assert {j["type"] for j in joints[2:]} == {"string"}
    assert all(j["b"].startswith("bar@") for j in joints[2:])
    assert joints[0]["limits"] == [-120.0, 120.0] and joints[1]["limits"] == [-120.0, 120.0]


def test_a_rig_with_hands_is_tied_by_them_and_a_subset_ties_only_those():
    hands = {"bones": [{"name": "hand_l"}, {"name": "hand_r"}]}
    by = {j["name"]: j for j in marionette_joints("ned", "bar", rig=hands)}
    assert by["ned.hand_l"]["a"] == "ned/hand_l@hand_l"
    assert marionette_joints("ned", "bar")[3]["a"] == "ned/arm_l@0.5,0.95"
    only = marionette_joints("ned", "bar", strings=["head"])
    assert [j["name"] for j in only] == ["ned.hip_l", "ned.hip_r", "ned.head"]
    with pytest.raises(ValueError, match="no string named \\['tail'\\]"):
        marionette_joints("ned", "bar", strings=["tail"])


def test_the_spec_carries_gravity_and_loose_ranges():
    spec = style_spec("marionette")
    assert spec["live"]["style_pack"]["gravity"].startswith("down")
    from cutan.characters.limits import GENRE_LIMITS, limits_table

    loose = limits_table("marionette")
    assert all(loose[k][0] <= GENRE_LIMITS[k][0] and GENRE_LIMITS[k][1] <= loose[k][1] for k in loose)


def _project(root: Path, *, hands: bool = False) -> Path:
    init(root)
    chars = root / "assets" / "characters"
    new_character(chars, name="ned", seed="ned", use_dicebear=False, feet_origin=True)
    if hands:
        from cutan.characters.factory import add_forearms

        add_forearms(chars / "ned")
    add_limits(chars / "ned", style="marionette")
    write_control_bar(root / "assets" / "props", "control_bar", width_px=120)
    return root


def _shot(root: Path, *, bar_to: float = 150.0, hands: bool = False) -> Shot:
    desc = json.loads((root / "assets/characters/ned/character.json").read_text("utf-8"))
    return Shot.model_validate(
        {
            "id": "s",
            "duration": 4.0,
            "entities": [
                {
                    "kind": "character",
                    "id": "ned",
                    "store": "characters",
                    "ref": "ned",
                    "stage": {"at": [0, 150], "scale": 0.8},
                    "overrides": {"free": True},
                },
                {
                    "kind": "prop",
                    "id": "bar",
                    "store": "props",
                    "ref": "control_bar",
                    "stage": {"at": [0, -120], "after": "ned"},
                },
            ],
            "joints": marionette_joints("ned", "bar", rig=desc),
            "actions": [
                {
                    "kind": "tween",
                    "target": "bar",
                    "property": "x",
                    "from_value": 0.0,
                    "to_value": bar_to,
                    "duration": 1.5,
                }
            ],
        }
    )


def _compile(root: Path, shot: Shot):
    pack = style_spec("marionette")["live"]["style_pack"]
    from an.styles import StylePack

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return compile_shot(
            shot,
            load(root).mall,
            fps=24,
            width=W,
            height=H,
            style_pack=StylePack(**pack),
        )


def _head_x(doc, t):
    from an.stage.tree import walk_children

    head = next(p for p, _ in walk_children(doc.scene) if p.split("/")[-1] == "head" and p.startswith("ned/"))
    pose = evaluate_timeline(timeline_from_scene(doc), t)
    return screen_position(doc, head, pose=pose)[0]


def test_the_figure_follows_the_bar_swings_and_settles(tmp_path):
    root = _project(tmp_path / "p")
    shot = _shot(root)
    doc = _compile(root, shot)
    report = doc.meta.extensions["solve"]
    assert report["mode"] == "dynamic" and report["gravity"] is not None
    assert report["dropped"] == []
    xs = [_head_x(doc, k / 24) for k in range(0, 97)]
    bar_x = 320.0 + 150.0
    assert xs[0] == pytest.approx(320.0, abs=1.0)
    assert bar_x - _head_x(doc, 1.0) > 40  # it lags the hand that moves it
    assert xs[-1] == pytest.approx(bar_x, abs=5.0)  # and ends up under it
    assert abs(xs[-1] - xs[-6]) < 1.0  # settled
    # no string stretched past its length, no hinge bent past its range
    puppet, times, gaps, excess = joint_residuals(doc, shot, load(root).mall)
    assert max(max(g) for g in gaps) < 0.5
    assert max(max(e) for e in excess) == 0.0


def test_a_bar_that_stays_leaves_the_figure_hanging_where_it_was(tmp_path):
    root = _project(tmp_path / "p")
    doc = _compile(root, _shot(root, bar_to=0.0))
    assert abs(_head_x(doc, 4.0) - _head_x(doc, 0.0)) < 1.0


def test_the_solve_is_deterministic(tmp_path):
    root = _project(tmp_path / "p")
    one = _compile(root, _shot(root)).scene.model_dump_json()
    assert one == _compile(root, _shot(root)).scene.model_dump_json()


def test_a_figure_with_hands_hangs_by_them_too(tmp_path):
    root = _project(tmp_path / "p", hands=True)
    shot = _shot(root)
    assert any(j.a == "ned/hand_l@hand_l" for j in shot.joints)
    doc = _compile(root, shot)
    assert doc.meta.extensions["solve"]["dropped"] == []
    assert _head_x(doc, 4.0) - _head_x(doc, 0.0) > 100


def test_the_joint_checks_pass_for_the_marionette(tmp_path):
    root = _project(tmp_path / "p")
    project = load(root)
    from an.styles import StylePack

    scene = project.scene.model_copy(update={"timeline": [_shot(root)]})
    scene.meta.style_pack = "marionette"
    pack = StylePack(**style_spec("marionette")["live"]["style_pack"])
    report = validate_semantic(
        scene,
        available_characters=project.mall["characters"],
        available_props=project.mall["props"],
        available_environments=project.mall["environments"],
        available_styles={"marionette": pack.model_dump(mode="json")},
        only={"unknown_body", "unreachable_pin", "joint_violation"},
    )
    assert [f.description for f in report.findings] == []
