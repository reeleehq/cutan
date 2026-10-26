"""The pre-render cadence lint (catalogue B6): a scene's timing against its style spec."""

from __future__ import annotations

from an.ir.schema import Meta, SceneIR, Shot
from an.ir.validate import validate_semantic

from cutan.verify.cadence import cadence_faults

ONLY = {"cutout.cadence"}


def _tween(duration, easing="linear", target="a"):
    return {
        "kind": "tween",
        "target": target,
        "property": "x",
        "to_value": 10.0,
        "duration": duration,
        "easing": easing,
    }


def _lint(actions, *, style="south_park", step_hz=12):
    shot = Shot.model_validate({"id": "s", "duration": 3.0, "actions": actions})
    meta = Meta(style_pack=style, step_hz=step_hz)
    scene = SceneIR(meta=meta, timeline=[shot])
    return [f.description for f in validate_semantic(scene, only=ONLY).findings]


def test_timing_inside_the_style_is_clean():
    assert _lint([_tween(0.2), _tween(0.15, "step")]) == []


def test_a_gliding_tween_in_a_snappy_style_is_a_warning():
    (msg,) = _lint([_tween(1.5)])
    assert "south_park" in msg and "a.x lasts 1.5 s" in msg


def test_an_easing_outside_the_list_is_a_warning():
    (msg,) = _lint([_tween(0.2, "ease_in_out"), _tween(0.2, "ease_in", "b")])
    assert "eases with ease_in_out" in msg and "1 more" in msg


def test_a_scene_off_the_styles_step_rate_is_a_warning():
    (msg,) = _lint([_tween(0.2)], step_hz=None)
    assert "step_hz: 12" in msg


def test_no_style_or_an_unknown_style_says_nothing():
    assert _lint([_tween(5.0)], style=None, step_hz=None) == []
    assert _lint([_tween(5.0)], style="my_own_pack", step_hz=None) == []


def test_cadence_faults_compares_a_bezier_easing_as_a_value():
    live = {"easing": [[0.34, 1.56, 0.64, 1.0]]}
    assert cadence_faults([("a.x", 1.0, (0.34, 1.56, 0.64, 1.0))], live) == {}
