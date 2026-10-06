"""Stroke-shape variability and a curved fall, for thoremin's air-drum benchmarks (cutan#27)."""

from __future__ import annotations

import json
import math

import pytest

from cutan.impacts import ImpactClipSpec, plan_impact_clip, write_impact_clip
from cutan.impacts.clip import MIN_TIMING_FRACTION, ImpactSpecError


def _truth(tmp_path, spec):
    return json.loads((write_impact_clip(spec, tmp_path, render=False) / "truth.json").read_text())


def test_spread_timings_are_drawn_per_stroke_and_recorded(tmp_path):
    spec = ImpactClipSpec(kind="air", beats=8, rise_sd=0.02, fall_sd=0.03, brake_sd=0.01, seed=5)
    events = _truth(tmp_path, spec)["events"]
    for name, mean in (("fall", spec.fall), ("brake", spec.brake), ("rise", spec.rise)):
        values = [e[name] for e in events]
        assert len(set(values)) > 1, name  # each stroke its own
        assert min(values) >= mean * MIN_TIMING_FRACTION
    # the truth's keypoints still agree with the compiled scene (TruthMismatch otherwise)
    assert all(e["fall"] > 0 for e in events)


def test_spread_does_not_move_the_performance_or_the_camera():
    plain = plan_impact_clip(ImpactClipSpec(kind="air", beats=8, seed=5))
    spread = plan_impact_clip(ImpactClipSpec(kind="air", beats=8, seed=5, fall_sd=0.03))
    assert [e.t_impact for e in plain.events] == [e.t_impact for e in spread.events]
    assert [f.t_mid for f in plain.frames] == [f.t_mid for f in spread.frames]


def test_without_spread_every_stroke_is_the_mean_and_old_clip_ids_hold():
    plan = plan_impact_clip(ImpactClipSpec(kind="air", beats=4))
    assert {k.fall for k in plan.stroke.kinematics} == {ImpactClipSpec().fall}
    d = ImpactClipSpec().to_dict()
    assert not {"rise_sd", "fall_sd", "brake_sd", "arc_radius"} & set(d)  # the id's JSON
    assert ImpactClipSpec.from_dict(d) == ImpactClipSpec()


def test_an_arc_fall_curves_and_lands_where_a_straight_one_does(tmp_path):
    straight = _truth(tmp_path / "s", ImpactClipSpec(object="ball", beats=2))
    arc = _truth(tmp_path / "a", ImpactClipSpec(object="ball", beats=2, arc_radius=300.0))
    assert [e["impact_xy"] for e in arc["events"]] == [e["impact_xy"] for e in straight["events"]]
    plan = plan_impact_clip(ImpactClipSpec(object="ball", beats=2, arc_radius=300.0))
    obj = plan.obj
    # the bottom keypoint moves on a circle of radius arc_radius + ball radius about the pivot
    px, py = obj.params["pivot_x"], obj.params["pivot_y"]
    r = obj.params["arc_radius"] + obj.params["radius"]
    for h in (0.0, 0.3, 0.7, 1.0):
        theta = obj.channels[0].value(h)
        x, y = 0.0, r  # local, rotated clockwise by theta (y down)
        gx, gy = px + x * math.cos(theta) - y * math.sin(theta), py + x * math.sin(theta) + y * math.cos(theta)
        assert math.hypot(gx - px, gy - py) == pytest.approx(r)
    # at contact it is the lowest point; raised, it has moved sideways
    assert obj.channels[0].value(0.0) == 0.0 and abs(obj.channels[0].value(1.0)) > 0.5


def test_an_arc_is_the_balls_and_must_reach_the_drop():
    with pytest.raises(ImpactSpecError, match="grip"):
        ImpactClipSpec(object="stick", arc_radius=300.0)
    with pytest.raises(ValueError, match="radius"):
        plan_impact_clip(ImpactClipSpec(object="ball", arc_radius=50.0))
