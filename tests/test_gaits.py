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
from an.motion import _tweens, stage_poses
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


def _body_y(steps: int) -> list[float]:
    leaves = sorted(
        (f for f in flatten(walk("p", steps=steps, gait="profile", step_s=0.4))
         if isinstance(f.action, TweenAction) and f.action.target == "p" and f.action.property == "y"),
        key=lambda f: f.start,
    )
    return [round(f.action.to_value, 2) for f in leaves]


def test_profile_sinks_after_contact_and_rises_before_the_next():
    """cutan#18: the four poses are phased to the CONTACTS (the legs at their
    widest, a step boundary): up before each contact, down after it; `bob` (6)
    is the whole travel (rises 4, sinks 2). The walk starts and ends standing."""
    # three steps: up before contact 1 | down, up between contacts | down after contact 2
    assert _body_y(3) == [-4.0, 0.0, 2.0, -4.0, 0.0, 2.0, 0.0, 0.0]
    # one step: its contact is mid-step
    assert _body_y(1) == [-4.0, 0.0, 2.0, 0.0, 0.0]
    assert _body_y(2) == [-4.0, 0.0, 2.0, 0.0, 0.0]


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
    from cutan.characters.checks import _preset_context_of, _stage_of
    from cutan.characters.play import play_extent_for

    for ref, scale, args in (("gale", 2.0, {}), ("gale_shuffle", 1.0, {}), ("legless", 1.0, {"gait": "shuffle"})):
        shot = _gale_shot(PlayAction(target="w", animation="walk", args={"distance": 160, **args}), scale=scale, ref=ref)
        play = shot.actions[0]
        doc = _compile(shot, {"characters": gait_store})
        walked = max(ch.keyframes[-1].time for a in doc.animations.values() for ch in a.channels if ch.target == "w" and ch.property == "x")
        rigs = {e.id: e for e in shot.entities}
        stores = {"characters": gait_store}
        extent = play_extent_for(lambda e: None, context_of=_preset_context_of(rigs, set(), stores, _stage_of(shot, stores)))
        assert extent(play) == pytest.approx(walked, abs=1e-6), (ref, scale, args)
        # and the shot-end warning validate gives reads the same length
        long = _gale_shot(PlayAction(target="w", animation="walk", args={"distance": 160, **args}), scale=scale, ref=ref).model_copy(update={"duration": walked - 0.1})
        report = validate_semantic(SceneIR(meta=Meta(title="t", duration=4.0), timeline=[long]), available_characters=gait_store)
        assert any("past the shot's end" in f.description for f in report.findings), (ref, scale, args)


def test_a_zero_scale_is_refused_as_the_scale():
    """cutan#13: a zero (or unusable) drawn scale is said as the scale, never
    as `step_length`, and never a silent flat walk."""
    for kwargs in ({"steps": 2}, {"distance": 160}, {"distance": 160, "step_length": 80.0}):
        with pytest.raises(ValueError, match="drawn scale is 0.0"):
            walk("k", gait="hop", legs=(), arms=(), rest={"scale_y": 0.0}, **kwargs)
    for bad in (float("nan"), float("inf"), -1.0):
        with pytest.raises(ValueError, match="drawn scale"):
            walk("k", steps=2, legs=(), scale=bad)
    with pytest.raises(ValueError, match="step_length must be positive"):
        walk("k", steps=2, legs=(), step_length=0.0)


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
    assert "stage scale" in problem and "not an argument" in problem


PROPS = FIXTURES.parent / "props"


def test_validate_times_a_prop_walk_as_compile_does(tmp_path):
    """A prop resolves off the registry: the walk picks its gait from the built
    parts (no legs: a requested `shuffle` glides, 0.8 s), and validate's extent
    must see those parts too (review of cutan#12, F1)."""
    from an.stores.props import PropsStore
    from cutan.characters.checks import _preset_context_of, _stage_of
    from cutan.characters.play import play_extent_for

    shutil.copytree(PROPS / "lamp", tmp_path / "lamp")
    props = PropsStore(tmp_path)
    play = PlayAction(target="p", animation="walk", args={"distance": 160, "gait": "shuffle"})
    shot = Shot(
        id="s",
        duration=1.0,
        entities=[AssetRef(kind="prop", id="p", store="props", ref="lamp")],
        actions=[play],
    )
    doc = _compile(shot, {"props": props})
    walked = max(ch.keyframes[-1].time for a in doc.animations.values() for ch in a.channels if ch.target == "p" and ch.property == "x")
    rigs = {e.id: e for e in shot.entities}
    stores = {"props": props}
    extent = play_extent_for(lambda e: None, context_of=_preset_context_of(rigs, set(), stores, _stage_of(shot, stores)))
    assert extent(play) == pytest.approx(walked, abs=1e-6) == pytest.approx(0.8)
    report = validate_semantic(SceneIR(meta=Meta(title="t", duration=4.0), timeline=[shot]), available_props=props)
    assert not any("past the shot's end" in f.description for f in report.findings)


def test_the_vocabulary_offers_only_what_play_problems_accepts():
    """`scale` is the compiler's (cutan#13): the genre's vocabulary must not list it."""
    from cutan.characters.play import RESERVED_PRESET_ARGS, play_problems
    from cutan.genre import CUTOUT

    (entry,) = [e for e in CUTOUT.vocabulary if getattr(e, "term", None) == "walk"]
    listed = set(entry.params["properties"])
    assert not listed & RESERVED_PRESET_ARGS
    for name in listed - {"gait", "legs", "arms", "direction", "view"}:  # the typed ones
        assert play_problems(None, "walk", args={name: 2}) == [], name


def test_validate_times_nothing_it_was_not_given_a_store_for(gait_store):
    """No characters store: validate's extent invents no rig (review F5)."""
    from cutan.characters.checks import _preset_context_of, _stage_of

    shot = _gale_shot(PlayAction(target="w", animation="walk", args={"distance": 160, "gait": "shuffle"}), ref="gale_shuffle")
    rigs = {e.id: e for e in shot.entities}
    assert _preset_context_of(rigs, {"w"}, {}, _stage_of(shot, {}))("w", shot.actions[0]) is None


def test_a_figure_resized_by_an_authored_move_strides_as_drawn(store):
    """cutan#13 / walk v3: the stage scale, not the pose at the play's start."""
    acts = sequence(set_("w", "scale_y", 2.0), set_("w", "scale_x", 2.0),
                    PlayAction(target="w", animation="walk", args={"distance": 160}))
    doc = _compile(_gale_shot(acts), {"characters": store})
    walked = max(ch.keyframes[-1].time for a in doc.animations.values() for ch in a.channels if ch.target == "w" and ch.property == "x")
    assert walked == pytest.approx(0.8)  # two 80 px steps: the figure is drawn at scale 1


def test_an_unchecked_entity_does_not_cost_the_others_their_context(gait_store, tmp_path):
    """review C: a prop whose store was not supplied is left out of validate's
    stage build, so the character's walk is still timed as compile times it."""
    from cutan.characters.checks import _preset_context_of, _stage_of

    shot = Shot(
        id="s",
        duration=4.0,
        entities=[
            AssetRef(kind="character", id="w", store="characters", ref="gale_shuffle"),
            AssetRef(kind="prop", id="p", store="props", ref="lamp"),
        ],
        actions=[PlayAction(target="w", animation="walk", args={"distance": 160})],
    )
    stores = {"characters": gait_store}  # no props store: `p` is unchecked
    context = _preset_context_of({e.id: e for e in shot.entities}, {"p"}, stores, _stage_of(shot, stores, {"p"}))
    assert context("w", shot.actions[0])["gait"] == "shuffle"


# ------------------------------------------- cutan#14, #15, #16, #18, #20 (walk v3)

PARTS = {n: {"rotation": 0.0, "y": 0.0} for n in ("leg_l", "leg_r", "arm_l", "arm_r")}


def _channel(action, target, prop):
    return sorted(
        (f for f in _tweens(action) if f.action.target == target and f.action.property == prop),
        key=lambda f: f.start,
    )


@pytest.mark.parametrize(
    "gait,view,legs_moving",
    [
        ("profile", None, {"p/leg_l", "p/leg_r"}),
        ("legs", "side", {"p/leg_l", "p/leg_r"}),
        ("hem", None, {"p/leg_l", "p/leg_r"}),
        ("legs", None, {"p/leg_l"}),  # facing the camera one leg steps, the other stands
    ],
)
def test_a_one_step_walk_moves_its_limbs(gait, view, legs_moving):
    """cutan#16: `distance: 80` is one step by default; the limbs still move."""
    w = walk("p", gait=gait, steps=1, distance=80, parts=PARTS, view=view)
    moved = {
        f.action.target
        for f in _tweens(w)
        if f.action.target != "p" and f.action.from_value != f.action.to_value
    }
    assert moved == legs_moving | {"p/arm_l", "p/arm_r"}
    for name in ("p/arm_l",):  # one extreme mid-step, back to rest
        ends = [f.action.to_value for f in _channel(w, name, "rotation")]
        assert ends[0] != 0.0 and ends[-1] == pytest.approx(0.0)


def test_a_profile_walk_passes_its_legs_between_contacts():
    """cutan#18: a walk of N steps starts and ends standing and makes N-1
    contacts; from three steps on the legs cross their rest between two."""
    w = walk("p", gait="profile", steps=3, distance=240, parts=PARTS)
    values = [v for f in _channel(w, "p/leg_l", "rotation") for v in (f.action.from_value, f.action.to_value)]
    assert min(values) < 0.0 < max(values), values
    two = walk("p", gait="profile", steps=2, distance=160, parts=PARTS)
    assert [f.action.to_value for f in _channel(two, "p/leg_l", "rotation")] == pytest.approx([0.45, 0.0, 0.0])


def test_profile_body_travel_per_step_is_bob():
    w = walk("p", gait="profile", steps=2, bob=6.0, parts=PARTS)
    ys = [v for f in _channel(w, "p", "y") for v in (f.action.from_value, f.action.to_value)]
    assert max(ys) - min(ys) == pytest.approx(6.0)


def test_the_body_sway_mirrors_with_the_figure():
    """cutan#20: the sway leans onto the standing foot whichever way the figure faces."""

    def first_rock(a):
        return next(f.action.to_value for f in _channel(a, "b", "rotation"))

    for gait in ("waddle", "rock", "hem"):
        plain = walk("b", gait=gait, steps=2, arms=())
        mirrored = walk("b", gait=gait, steps=2, arms=(), rest={"scale_x": -1.0})
        assert first_rock(plain) > 0, gait  # over the standing leg_r (viewer's right)
        assert first_rock(mirrored) == pytest.approx(-first_rock(plain)), gait


def test_a_zero_amplitude_writes_no_channel():
    """cutan#14: as `arm_swing: 0` and `lean: 0` already did."""
    w = walk("k", gait="glide", bob=0, lean=0, steps=2, distance=100, legs=(), arms=())
    assert {(f.action.target, f.action.property) for f in _tweens(w)} == {("k", "x")}
    w = walk("k", gait="rock", rock=0, bob=0, steps=2, distance=100, legs=(), arms=())
    assert {(f.action.target, f.action.property) for f in _tweens(w)} == {("k", "x")}
    w = walk("k", gait="legs", lift=0, stride=0, bob=0, arm_swing=0, steps=2, parts=PARTS)
    assert not _tweens(w) and duration_of(w) == pytest.approx(2 * DFLT_WALK_STEP_S)  # on the spot: still takes its time


def test_a_zero_amplitude_walk_leaves_an_authored_tween_alone(store):
    acts = parallel(
        tween("w", "y", to=-100.0, duration=2.0, from_=0.0, easing="linear"),
        PlayAction(target="w", animation="walk", args={"gait": "glide", "bob": 0, "lean": 0, "steps": 2, "distance": 100}),
    )
    doc = _compile(_gale_shot(acts), {"characters": store})
    assert _pose(doc, 0.4)[("w", "y")] == pytest.approx(-20.0)


def test_a_walk_does_not_snap_the_body_back_after_a_longer_authored_tween(store):
    """cutan#15: the body lands with the landing tween, as the limbs do."""
    acts = parallel(
        tween("w", "y", to=-100.0, duration=2.0, from_=0.0, easing="linear"),
        PlayAction(target="w", animation="walk", args={"gait": "hop", "steps": 2, "distance": 100}),
    )
    doc = _compile(_gale_shot(acts), {"characters": store})
    assert _pose(doc, 2.5)[("w", "y")] == pytest.approx(-100.0)
    assert _pose(doc, 1.0)[("w", "x")] == pytest.approx(_pose(doc, 0.8)[("w", "x")])  # and x stays landed
