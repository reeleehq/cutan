"""A style's `policy:` block, read at compile (cutan#9, ADR 0002 decision 4).

Precedence: the author's request (a walk's `gait`, a character's declared one),
then the shot's `policy`, then the style's (the StylePack the scene names,
built from the spec by `cutan.styles.style_pack`), then the aspect's chain.
"""

from __future__ import annotations

import json
import warnings

import pytest

from an.adapters.cutout.compile import compile_shot
from an.ir.compose import sequence
from an.stage.compile import CutoutCompileError
from an.styles import StylePack
from cutan.characters.registration import PlayAction
from cutan.styles import PolicyError, layered_policy, policy_problems, style_pack, style_spec_digest

from tests.test_methods_compile import _speaking, _walk_shot, store  # noqa: F401  (fixture)


def _compile(shot, mall, **kw):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return compile_shot(shot, mall, **kw)


def _methods(scene):
    return [(r.store, r.ref, r.resolved) for r in scene.asset_resolution if r.kind == "method"]


def test_a_style_pack_carries_its_spec_policy_and_where_it_came_from():
    pack = style_pack("south_park")
    assert pack.policy == {"locomotion": ["loco.bounce"]}
    assert pack.metadata["style_spec"] == {"name": "south_park", "sha256": style_spec_digest("south_park")}
    # saved and read back the way a project store does: the policy survives
    again = StylePack.model_validate(json.loads(json.dumps(pack.model_dump(mode="json"))))
    assert again.policy == pack.policy
    assert not hasattr(style_pack("kurzgesagt"), "policy")  # no block, no field


def test_no_policy_leaves_the_walk_as_the_chain_resolves_it(store):
    scene = _compile(_walk_shot("legged"), {"characters": store}, style_pack=style_pack("kurzgesagt"))
    assert _methods(scene) == []


def test_the_style_policy_chooses_against_the_chain_and_says_so(store):
    mall = {"characters": store}
    plain = _compile(_walk_shot("legged"), mall)
    styled = _compile(_walk_shot("legged"), mall, style_pack=style_pack("south_park"))
    assert _methods(styled) == [("locomotion", "loco.legged_cycle", "loco.bounce")]
    (record,) = [r for r in styled.asset_resolution if r.kind == "method"]
    assert not record.fallback and "policy" in record.detail  # information, not a warning
    # the walk itself changed, so the compiled document (and the shot-cache key) did
    assert styled.model_dump(mode="json")["animations"] != plain.model_dump(mode="json")["animations"]


def test_the_shot_policy_wins_over_the_style(store):
    shot = _walk_shot("legged").model_copy(update={"policy": {"locomotion": ["loco.glide"]}})
    scene = _compile(shot, {"characters": store}, style_pack=style_pack("south_park"))
    assert _methods(scene) == [("locomotion", "loco.legged_cycle", "loco.glide")]


def test_the_authors_request_wins_over_both(store):
    mall = {"characters": store}
    shot = _walk_shot("legged", gait="legs").model_copy(
        update={"policy": {"locomotion": ["loco.glide"]}}
    )
    assert _methods(_compile(shot, mall, style_pack=style_pack("south_park"))) == []
    # a character's declared gait is a request too
    declared = _walk_shot("gale_legs")
    assert _methods(_compile(declared, mall, style_pack=style_pack("south_park"))) == []


def test_a_walk_inside_a_composition_follows_the_policy(store):
    walk = PlayAction(target="w", animation="walk", args={"distance": 160})
    shot = _walk_shot("legged").model_copy(update={"actions": [sequence(walk)]})
    scene = _compile(shot, {"characters": store}, style_pack=style_pack("south_park"))
    assert _methods(scene) == [("locomotion", "loco.legged_cycle", "loco.bounce")]


def test_a_policy_that_names_no_such_method_fails_the_compile_and_says_why(store):
    shot = _walk_shot("legged").model_copy(update={"policy": {"locomotion": ["bounce"]}})
    with pytest.raises(CutoutCompileError, match="did you mean 'loco.bounce'"):
        _compile(shot, {"characters": store})
    with pytest.raises(PolicyError, match="not registered"):
        layered_policy(shot={"policy": {"dance": ["loco.glide"]}})
    assert policy_problems({"speech": ["loco.glide"]})  # a method of another aspect


def test_reiniger_mimes_a_silhouette_line_under_its_policy(store):
    """an#273: under a black silhouette the mouth chart is invisible, so the
    style's policy makes speech the head's pulse."""
    mall = {"characters": store}
    plain = _compile(_speaking("gale"), mall)
    assert ("speech", "speech.mouth_chart", "speech.pose_only") not in _methods(plain)
    styled = _compile(_speaking("gale"), mall, style_pack=style_pack("reiniger"))
    assert ("speech", "speech.mouth_chart", "speech.pose_only") in _methods(styled)


def test_capabilities_says_what_each_aspect_resolves_to_under_a_style(tmp_path):
    """an#273: `an character capabilities` evaluated under a style's policy."""
    from cutan.characters import new_character
    from cutan.characters.cli import capabilities

    new_character(tmp_path, name="ned", seed="ned", use_dicebear=False, overwrite=True)
    out = json.loads(capabilities("ned", out_dir=str(tmp_path), as_json=True, style="reiniger"))
    assert out["aspects"]["speech"]["under_style"] == {
        "style": "reiniger", "method": "speech.pose_only", "source": "policy"}
    assert out["aspects"]["locomotion"]["default"] == "loco.legged_cycle"  # the chain, unchanged
    text = capabilities("ned", out_dir=str(tmp_path), style="south_park")
    assert "locomotion: under south_park: loco.bounce (policy)" in text


# --- findings of the adversarial reviews (PR #32) -------------------------------


def _tweens(scene):
    """``(start, end)`` of every tween clip in a compiled shot."""
    tracks = scene.model_dump(mode="json")["timeline"]["tracks"]
    return [(c["start_time"], c["start_time"] + c["duration"]) for t in tracks
            for c in t["clips"] if c["animation_id"].startswith("__tween__")]


def test_a_walk_in_a_sequence_keeps_its_length_under_a_policy(store):
    """The internal policy arg never reaches the walk's extent: what follows it waits."""
    from an.ir.compose import duration_of

    from cutan.characters.play import POLICY_ARG, play_extent_for

    walk = PlayAction(target="w", animation="walk", args={"distance": 160})
    tagged = PlayAction(target="w", animation="walk",
                        args={"distance": 160, POLICY_ARG: {"locomotion": ["loco.bounce"]}})
    extent = play_extent_for(lambda e: None)
    assert duration_of(walk, play_extent=extent) == duration_of(tagged, play_extent=extent) > 0
    mall, pack = {"characters": store}, style_pack("south_park")
    alone = _compile(_walk_shot("legged"), mall, style_pack=pack)
    walk_end = max(end for _, end in _tweens(alone))
    hop = PlayAction(target="w", animation="hop")
    shot = _walk_shot("legged").model_copy(update={"actions": [sequence(walk, hop)]})
    styled = _compile(shot, mall, style_pack=pack)
    assert _methods(styled) == [("locomotion", "loco.legged_cycle", "loco.bounce")]
    after = [start for start, _ in _tweens(styled) if start >= walk_end - 1e-6]
    assert after, "the hop started during the walk"


def test_a_walk_on_a_part_fails_the_same_way_under_a_policy(store):
    """The internal policy arg never reaches the preset: a walk on a part is
    refused with the same message as without a policy (#22), not a TypeError."""
    shot = _walk_shot("legged").model_copy(update={
        "actions": [PlayAction(target="w/left_arm", animation="walk", args={"distance": 40})]})
    with pytest.raises(CutoutCompileError) as plain:
        _compile(shot, {"characters": store})
    with pytest.raises(CutoutCompileError) as styled:
        _compile(shot, {"characters": store}, style_pack=style_pack("south_park"))
    assert str(styled.value) == str(plain.value)


def test_a_policy_head_that_does_not_apply_is_skipped_not_fatal(store):
    """an#334's case, now the matcher's own: the first APPLICABLE entry of the order wins."""
    mall = {"characters": store}
    shot = _walk_shot("legless").model_copy(
        update={"policy": {"locomotion": ["loco.hem_sway", "loco.glide"]}})
    scene = compile_shot(shot, mall, strict_assets=True)  # no fatal record
    # the skipped head is recorded (never silent), as a skip, not a substitution
    assert _methods(scene) == []
    (skip,) = [r for r in scene.asset_resolution if r.kind == "policy_skip"]
    assert (skip.store, skip.ref, skip.resolved) == ("locomotion", "loco.hem_sway", "loco.glide")
    assert not skip.fallback and "does not apply" in skip.detail and "limbs.legs" in skip.detail
    shot = _walk_shot("legged").model_copy(
        update={"policy": {"locomotion": ["loco.profile_cycle", "loco.bounce"]}})
    scene = compile_shot(shot, mall, strict_assets=True)
    assert _methods(scene) == [("locomotion", "loco.legged_cycle", "loco.bounce")]
    skips = [(r.ref, r.resolved) for r in scene.asset_resolution if r.kind == "policy_skip"]
    assert skips == [("loco.profile_cycle", "loco.bounce")]
    # an entry AFTER the winner is never reported
    shot = _walk_shot("legless").model_copy(
        update={"policy": {"locomotion": ["loco.bounce", "loco.hem_sway"]}})
    scene = compile_shot(shot, mall, strict_assets=True)
    assert not [r for r in scene.asset_resolution if r.kind == "policy_skip"]


def test_a_policy_entrys_args_are_honoured(store):
    mall = {"characters": store}
    plain = _compile(_walk_shot("legged").model_copy(
        update={"policy": {"locomotion": ["loco.bounce"]}}), mall)
    bigger = _compile(_walk_shot("legged").model_copy(
        update={"policy": {"locomotion": [{"method": "loco.bounce", "args": {"bob": 40}}]}}), mall)
    assert plain.model_dump(mode="json")["animations"] != bigger.model_dump(mode="json")["animations"]


def test_an_aspect_the_compiler_does_not_apply_is_refused():
    (problem,) = policy_problems({"expression": ["expr.without_brows"]})
    assert "not applied by the cut-out compiler" in problem


def test_validate_reports_a_bad_shot_policy(store):
    from an.ir.schema import Meta, SceneIR
    from an.ir.validate import validate_semantic

    shot = _walk_shot("legged").model_copy(update={"policy": {"locomotion": ["bounce"]}})
    report = validate_semantic(SceneIR(meta=Meta(), timeline=[shot]), available_characters=store)
    found = [f for f in report.findings if f.ir_path.endswith("/policy")]
    assert found and "did you mean 'loco.bounce'" in found[0].description


def test_a_scale_two_figure_bounces_the_same_by_request_and_by_policy(store):
    """A policy-chosen method keeps its own defaults (scaled to the figure), as a request does."""
    from an.ir.schema import StagePlacement

    mall = {"characters": store}

    def big(shot):
        ents = [e.model_copy(update={"stage": StagePlacement(scale=2.0)}) for e in shot.entities]
        return shot.model_copy(update={"entities": ents})

    asked = _compile(big(_walk_shot("legged", gait="bounce")), mall)
    chosen = _compile(big(_walk_shot("legged")), mall, style_pack=style_pack("south_park"))
    assert asked.model_dump(mode="json")["animations"] == chosen.model_dump(mode="json")["animations"]


def test_a_pack_built_from_a_spec_file_records_its_digest(tmp_path):
    from cutan.styles import style_spec_path

    path = tmp_path / "mine.yaml"
    path.write_bytes(style_spec_path("south_park").read_bytes())
    assert style_pack(str(path)).metadata["style_spec"]["sha256"] == style_spec_digest("south_park")



def test_a_policy_entrys_step_time_lengthens_the_walk_a_sequence_waits_for(store):
    """The extent resolves the walk exactly as the expansion does, policy included (cutan#12)."""
    mall = {"characters": store}
    slow = {"locomotion": [{"method": "loco.bounce", "args": {"step_s": 0.8}}]}
    walk = PlayAction(target="w", animation="walk", args={"distance": 160})
    hop = PlayAction(target="w", animation="hop")
    alone = _compile(_walk_shot("legged").model_copy(update={"policy": slow}), mall)
    walk_end = max(end for _, end in _tweens(alone))
    shot = _walk_shot("legged").model_copy(
        update={"policy": slow, "actions": [sequence(walk, hop)], "duration": walk_end + 2})
    seq = _compile(shot, mall)
    assert any(start >= walk_end - 1e-6 for start, _ in _tweens(seq)), "the hop did not wait"



def test_reiniger_walks_in_profile_only_while_the_side_view_shows(tmp_path):
    """The style's [profile_cycle, legged_cycle]: the profile cycle needs its side
    view in force (#17); in front view the figure steps on its legs, the skip recorded."""
    from an.ir.compose import set_
    from an.ir.schema import AssetRef, Shot
    from an.stores.characters import CharactersStore

    from cutan.characters import new_character

    new_character(tmp_path, name="ned", seed="ned", use_dicebear=False, overwrite=True)
    mall = {"characters": CharactersStore(tmp_path)}

    def shot(*first):
        walk = PlayAction(target="w", animation="walk", args={"distance": 120}, start=0.1)
        return Shot(id="w", duration=3.0, actions=[*first, walk],
                    entities=[AssetRef(kind="character", id="w", store="characters", ref="ned")])

    pack = style_pack("reiniger")
    front = compile_shot(shot(), mall, style_pack=pack, strict_assets=True)
    assert [(r.kind, r.ref, r.resolved) for r in front.asset_resolution if r.kind != "character"] == [
        ("policy_skip", "loco.profile_cycle", "loco.legged_cycle")]
    side = compile_shot(shot(set_("w", "view", "side", at=0.0)), mall, style_pack=pack,
                        strict_assets=True)
    assert _methods(side) == [("locomotion", "loco.legged_cycle", "loco.profile_cycle")]



def test_length_args_on_a_view_dependent_order_are_refused():
    """Which entry of [profile_cycle, legged_cycle] wins depends on the view at the
    walk; the extent cannot see it, so an entry's step_s would mistime a sequence."""
    (problem,) = policy_problems({"locomotion": [
        {"method": "loco.profile_cycle", "args": {"step_s": 0.2}}, "loco.legged_cycle"]})
    assert "step_s" in problem and "view" in problem
    assert policy_problems({"locomotion": [{"method": "loco.bounce", "args": {"step_s": 0.2}}]}) == []


def test_capabilities_says_a_view_bound_method_needs_its_view(tmp_path):
    from cutan.characters import new_character
    from cutan.characters.cli import capabilities

    new_character(tmp_path, name="ned", seed="ned", use_dicebear=False, overwrite=True)
    text = capabilities("ned", out_dir=str(tmp_path), style="reiniger")
    assert "loco.profile_cycle (policy), only while swap.view:side is showing" in text
