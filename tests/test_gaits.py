"""Locomotion gaits (an#224): methods with declared requirements, defaults, and a capability-based choice.

What is pinned here, and why:

- every gait ``walk`` knows is a locomotion method of that spelling, and the
  aspect's chain is ``legs`` then the requirement-free ``glide``;
- the matcher answers which gaits apply to a character and, for the rest,
  what is missing and how to add it (``profile`` needs a side view);
- every gait compiles on a descriptor rig and on the placeholder, lands where
  it was asked to and leaves the body and the limbs at rest;
- default lengths scale with the figure's drawn scale (an#224's comment: a
  ``scale: 2`` character used to shuffle), an explicit length does not;
- ``an validate`` says when a requested gait will not be used, and why.
"""

from __future__ import annotations

import json
import shutil
import warnings
from pathlib import Path

import pytest

from an.adapters.cutout.compile import compile_shot
from an.adapters.cutout.timeline import evaluate_timeline, timeline_from_scene
from an.ir.compose import duration_of, flatten, parallel, sequence, set_, tween
from an.motion import stage_poses
from an.ir.schema import AssetRef, Meta, SceneIR, Shot, StagePlacement, TweenAction
from an.ir.validate import validate_semantic
from an.semantic import applicable, aspect, why_not
from an.stores.characters import CharactersStore
from cutan.characters.methods import LOCOMOTION, compile_profile
from cutan.characters.registration import PlayAction
from cutan.characters.schema import CharacterDescriptor
from cutan.motion import (
    DFLT_LEGLESS_GAIT,
    DFLT_WALK_STEP_LENGTH,
    DFLT_WALK_STEP_S,
    GAITS,
    LEGGED_GAITS,
    gait_params,
    walk,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "characters"


@pytest.fixture()
def store(tmp_path):
    shutil.copytree(FIXTURES / "gale", tmp_path / "gale")
    shutil.copytree(FIXTURES / "gale", tmp_path / "gale_side")
    path = tmp_path / "gale_side" / "character.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["rest_view"] = "side"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return CharactersStore(tmp_path)


def _profile(store, ref):
    desc = CharacterDescriptor.model_validate(store[ref])
    return compile_profile(desc)


def _walk_shot(ref: str, *, scale: float = 1.0, **args) -> Shot:
    stage = StagePlacement(scale=scale) if scale != 1.0 else None
    return Shot(
        id="walk",
        duration=4.0,
        entities=[AssetRef(kind="character", id="w", store="characters", ref=ref, stage=stage)],
        actions=[PlayAction(target="w", animation="walk", args={"distance": 160, **args})],
    )


def _compile(shot, mall):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return compile_shot(shot, mall)


def _pose(doc, t):
    return evaluate_timeline(timeline_from_scene(doc), t)


def test_every_gait_is_a_locomotion_method_and_the_chain_ends_requirement_free():
    from an.semantic import lookup

    spelled = {lookup("method", g, aspect=LOCOMOTION).term for g in GAITS}
    assert spelled == set(GAITS)
    chain = aspect(LOCOMOTION).chain
    assert chain == ("loco.legged_cycle", "loco.glide")
    assert lookup("method", DFLT_LEGLESS_GAIT, aspect=LOCOMOTION).requires == ()


def test_the_matcher_says_which_gaits_apply_and_what_the_rest_need(store):
    front = {m.term for m in applicable(LOCOMOTION, _profile(store, "gale"))}
    assert front == set(GAITS) - {"profile"}
    (missing,) = why_not("loco.profile_cycle", _profile(store, "gale"))
    assert missing.term == "swap.view:side" and "add-views" in missing.remedy
    side = {m.term for m in applicable(LOCOMOTION, _profile(store, "gale_side"))}
    assert side == set(GAITS)
    legless = {m.term for m in applicable(LOCOMOTION, {})}
    assert legless == set(GAITS) - LEGGED_GAITS


@pytest.mark.parametrize("gait", GAITS)
@pytest.mark.parametrize("ref", ["gale_side", "placeholder"])
def test_each_gait_travels_and_lands_at_rest(gait, ref, store):
    mall = {"characters": store}
    shot = _walk_shot(ref, gait=gait, steps=3)
    doc = _compile(shot, mall)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        home = stage_poses(shot, mall=mall)
    end = _pose(doc, 3.9)
    assert end[("w", "x")] == pytest.approx(home["w"]["x"] + 160.0)
    for path, pose in home.items():
        for prop in ("y", "rotation"):
            got = end.get((path, prop), pose[prop])
            assert got == pytest.approx(pose[prop], abs=1e-6), (path, prop)


def test_default_lengths_scale_with_the_figure_and_explicit_ones_do_not():
    assert gait_params("legs", scale=2.0)["step_length"] == 2 * DFLT_WALK_STEP_LENGTH
    one = walk("k", distance=320.0, legs=())
    two = walk("k", distance=320.0, legs=(), rest={"scale_y": 2.0})
    assert duration_of(one) == pytest.approx(4 * DFLT_WALK_STEP_S)
    assert duration_of(two) == pytest.approx(2 * DFLT_WALK_STEP_S)
    pinned = walk("k", distance=320.0, legs=(), rest={"scale_y": 2.0}, step_length=80.0)
    assert duration_of(pinned) == pytest.approx(4 * DFLT_WALK_STEP_S)


def test_a_staged_character_strides_at_its_size(store):
    """an#224's comment: at `scale: 2` the steps were tiny shuffles."""
    mall = {"characters": store}
    big = _compile(_walk_shot("gale", scale=2.0, distance=320), mall)
    small = _compile(_walk_shot("gale", distance=320), mall)

    def contacts(doc):
        return max(ch.keyframes[-1].time for a in doc.animations.values() for ch in a.channels
                   if ch.target == "w" and ch.property == "x")

    assert contacts(big) == pytest.approx(contacts(small) / 2, rel=0.05)


def test_the_pre_an224_gaits_expand_as_before_at_scale_one():
    """legs, hem and rock keep their shared defaults: no pixel moves for them."""
    for gait in ("legs", "hem", "rock"):
        assert gait_params(gait) == gait_params("legs")
    leaves = [f for f in flatten(walk("b", distance=160, steps=2, gait="rock", legs=())) if isinstance(f.action, TweenAction)]
    assert {f.action.property for f in leaves if f.action.target == "b"} == {"x", "y", "rotation"}


def test_profile_sinks_after_contact_and_rises_before_the_next():
    leaves = sorted(
        (f for f in flatten(walk("p", steps=1, gait="profile", step_s=0.4))
         if isinstance(f.action, TweenAction) and f.action.target == "p" and f.action.property == "y"),
        key=lambda f: f.start,
    )
    assert [round(f.action.to_value, 2) for f in leaves] == [3.0, -6.0, 0.0]


def _gait_warnings(store, ref, **args):
    from an.ir.validate import validate_semantic

    scene = SceneIR(meta=Meta(title="t", duration=4.0), timeline=[_walk_shot(ref, **args)])
    report = validate_semantic(scene, available_characters=store)
    return [f.description for f in report.findings if "locomotion" in f.description]


def test_validate_says_why_a_requested_gait_will_not_be_used(store):
    (said,) = _gait_warnings(store, "gale", gait="profile")
    assert "loco.profile_cycle" in said and "loco.legged_cycle" in said
    assert "swap.view:side" in said and "add-views" in said
    assert _gait_warnings(store, "gale_side", gait="profile") == []
    assert _gait_warnings(store, "gale", gait="hop") == []


# --------------------------------------------------------------- cutan#12, cutan#13


def _gale_shot(*actions, scale: float = 1.0, ref: str = "gale") -> Shot:
    stage = StagePlacement(scale=scale) if scale != 1.0 else None
    return Shot(
        id="s",
        duration=4.0,
        entities=[AssetRef(kind="character", id="w", store="characters", ref=ref, stage=stage)],
        actions=list(actions),
    )


def _walk_then_head_turn(store, ref, *, scale=1.0, **args):
    """``(when the walk lands, when the next action in the sequence starts)``."""
    shot = _gale_shot(
        sequence(
            PlayAction(target="w", animation="walk", args={"distance": 160, **args}),
            tween("w/head", "rotation", to=0.5, duration=0.5, from_=0.0, easing="linear"),
        ),
        scale=scale,
        ref=ref,
    )
    tl = timeline_from_scene(_compile(shot, {"characters": store}))
    ts = [i / 100 for i in range(300)]
    ev = [evaluate_timeline(tl, t) for t in ts]
    lands = next(t for t, e in zip(ts, ev) if abs(e.get(("w", "x"), 0.0) - 160) < 1e-6)
    nxt = next(t for t, e in zip(ts, ev) if e.get(("w/head", "rotation"), 0.0) > 1e-6) - 0.01
    return lands, round(nxt, 2)


@pytest.fixture()
def gait_store(tmp_path):
    """``gale``; ``gale_shuffle`` (declares ``gait: shuffle``); ``legless`` (a parts rig)."""
    shutil.copytree(FIXTURES / "gale", tmp_path / "gale")
    shutil.copytree(FIXTURES / "gale", tmp_path / "gale_shuffle")
    path = tmp_path / "gale_shuffle" / "character.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["gait"] = "shuffle"
    path.write_text(json.dumps(doc), encoding="utf-8")
    store = CharactersStore(tmp_path)
    store["legless"] = {"name": "legless", "parts": ["head", "torso", "left_arm", "right_arm"]}
    return store


@pytest.mark.parametrize(
    "ref,scale,args",
    [
        ("gale", 2.0, {}),  # the scaled step: 1 step of 0.4 s, not 2
        ("gale_shuffle", 1.0, {}),  # the descriptor's gait: 4 steps of 0.3 s
        ("legless", 1.0, {"gait": "shuffle"}),  # substituted to glide: 2 steps of 0.4 s
    ],
)
def test_a_sequence_waits_exactly_as_long_as_the_walk(gait_store, ref, scale, args):
    """cutan#12: the extent sees the gait and the scale the expansion uses."""
    lands, nxt = _walk_then_head_turn(gait_store, ref, scale=scale, **args)
    assert nxt == pytest.approx(lands, abs=0.011), (ref, scale, lands, nxt)


def test_validate_places_a_sequence_where_compile_does(gait_store):
    """`an validate`'s extent resolver reads the same gait and scale as the compiler's."""
    from cutan.characters.checks import _preset_context_of
    from cutan.characters.play import play_extent_for
    from cutan.compile.lowering import PLAY_LOWERING

    for ref, scale, args in (("gale", 2.0, {}), ("gale_shuffle", 1.0, {}), ("legless", 1.0, {"gait": "shuffle"})):
        shot = _gale_shot(PlayAction(target="w", animation="walk", args={"distance": 160, **args}), scale=scale, ref=ref)
        play = shot.actions[0]
        doc = _compile(shot, {"characters": gait_store})
        walked = max(ch.keyframes[-1].time for a in doc.animations.values() for ch in a.channels if ch.target == "w" and ch.property == "x")
        rigs = {e.id: e for e in shot.entities}
        extent = play_extent_for(lambda e: None, context_of=_preset_context_of(rigs, {"characters": gait_store}))
        assert extent(play) == pytest.approx(walked, abs=1e-6), (ref, scale, args)
        # and the shot-end warning validate gives reads the same length
        long = _gale_shot(PlayAction(target="w", animation="walk", args={"distance": 160, **args}), scale=scale, ref=ref).model_copy(update={"duration": walked - 0.1})
        report = validate_semantic(SceneIR(meta=Meta(title="t", duration=4.0), timeline=[long]), available_characters=gait_store)
        assert any("past the shot's end" in f.description for f in report.findings), (ref, scale, args)


def test_an_explicit_step_count_does_not_need_a_step_length():
    """cutan#13: `step_length` is read only to count the steps; a zero from the
    figure's scale is reported as the scale."""
    walk("k", steps=2, gait="hop", legs=(), arms=(), rest={"scale_y": 0.0})
    with pytest.raises(ValueError, match="drawn scale is 0.0"):
        walk("k", distance=160, legs=(), arms=(), rest={"scale_y": 0.0})
    assert duration_of(walk("k", distance=160, legs=(), scale=0.0, step_length=80.0)) == pytest.approx(0.8)


def test_the_drawn_scale_is_the_stage_scale_not_the_pose_at_the_plays_start(store):
    """cutan#13: a walk that starts while the figure pops in still hops."""
    hidden = [set_("w", "scale_x", 0.0), set_("w", "scale_y", 0.0)]
    play = parallel(
        PlayAction(target="w", animation="pop_in"),
        PlayAction(target="w", animation="walk", args={"gait": "hop", "steps": 2, "distance": 160}),
    )
    doc = _compile(_gale_shot(sequence(*hidden, play)), {"characters": store})
    y0, apex = _pose(doc, 0.0)[("w", "y")], _pose(doc, 0.2)[("w", "y")]
    assert apex == pytest.approx(y0 - 18.0)
    big = _compile(_gale_shot(sequence(*hidden, play), scale=2.0), {"characters": store})
    assert _pose(big, 0.2)[("w", "y")] == pytest.approx(_pose(big, 0.0)[("w", "y")] - 36.0)


def test_scale_is_the_compilers_to_fill_not_the_authors():
    from cutan.characters.play import play_problems

    (problem,) = play_problems(None, "walk", args={"scale": 2.0, "distance": 80})
    assert "scale" in problem
