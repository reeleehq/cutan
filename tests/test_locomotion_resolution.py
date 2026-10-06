"""How a walk resolves to a locomotion method, through the matcher (an#427).

These tests drive ``an.semantic``'s ``resolve``, ``applicable``, ``why_not`` and
``describe`` over the cut-out genre's own aspects and methods (``loco.*``,
``speech.*``), so they belong to the genre: a new gait or a renamed method fails
THIS repository's CI, never an unrelated ``an`` PR. ``an`` tests the same
mechanics over a demo genre (``tests/test_semantic.py``).
"""

from __future__ import annotations

import pytest

from an.semantic import (
    Policy,
    VocabularyError,
    applicable,
    lookup,
    resolve,
    why_not,
)

LEGS = {"limbs.legs": {"slots": ["leg_l", "leg_r"]}}


def test_a_motion_presets_entry_describes_its_parameters_with_defaults():
    walk = lookup("motion_preset", "walk")
    props = walk.params["properties"]
    assert {"step_s", "step_length", "gait"} <= set(props)
    assert not {"target", "rest", "parts"} & set(props)
    assert walk.aspects == ("locomotion",)
    # Per-gait defaults live on the locomotion methods (an#224).
    legs = lookup("method", "legs", aspect="locomotion")
    assert legs.params["properties"]["step_s"]["default"] == 0.4


def test_the_locomotion_chain_is_legs_then_glide():
    """legs when the character affords a leg pair, a glide when it does not (an#224)."""
    assert resolve("locomotion", LEGS).method.id == "loco.legged_cycle"
    assert resolve("locomotion", {}).method.id == "loco.glide"
    legless = [m.id for m in applicable("locomotion", {})]
    assert legless[0] == "loco.glide"
    assert set(legless) == {"loco.glide", "loco.waddle", "loco.hop", "loco.bounce", "loco.rock"}


def test_a_request_by_its_spelling_applies_or_falls_back_with_a_recorded_substitution():
    r = resolve("locomotion", LEGS, requested="hem", entity="robe")
    assert (r.method.id, r.source, r.substitution) == ("loco.hem_sway", "request", None)
    r = resolve("locomotion", {}, requested="hem", entity="blob")
    s = r.substitution
    assert (r.method.id, s.reason, s.requested, s.missing, s.fatal) == (
        "loco.glide",
        "missing",
        "loco.hem_sway",
        ("limbs.legs",),
        True,
    )
    assert "hem" in s.remedies["limbs.legs"]


def test_why_not_gives_the_methods_own_remedy_before_the_capabilitys():
    (gap,) = why_not("loco.legged_cycle", {})
    assert gap.term == "limbs.legs" and "hip" in gap.remedy
    assert why_not("loco.legged_cycle", LEGS) == ()


def test_a_policy_choice_over_an_applicable_chain_is_information_not_a_warning():
    """South Park: the show rocks even when its characters have legs."""
    r = resolve("locomotion", LEGS, policy={"locomotion": ["loco.rock"]})
    assert r.method.id == "loco.rock" and r.source == "policy"
    assert r.substitution.reason == "policy" and not r.substitution.fatal


def test_a_policy_entry_that_does_not_apply_is_skipped_never_a_fatal_substitution():
    """A policy is an order, not a request (an#334): its first APPLICABLE entry
    wins, and the entries passed over are listed, never a ``missing`` record."""
    r = resolve("locomotion", {}, policy={"locomotion": ["hem", "loco.rock"]})
    assert r.method.id == "loco.rock" and r.source == "policy"
    assert r.substitution.reason == "policy" and not r.substitution.fatal
    assert r.substitution.requested == "loco.glide"  # what the chain would have done
    assert r.skipped == (("loco.hem_sway", ("limbs.legs",)),)
    assert r.to_json()["skipped"] == [{"method": "loco.hem_sway", "missing": ["limbs.legs"]}]


def test_a_multi_entry_policy_whose_later_entry_applies_is_not_fatal():
    """The issue's repro: Reiniger's ``[profile, legs]`` on a front-only legged
    figure, and ``[hem, glide]`` on a legless one, each land on the chain's own
    choice, with the head recorded as skipped and nothing to refuse."""
    front_only = {**LEGS, "swap.view": {"keys": ["front"]}}
    r = resolve("locomotion", front_only, policy={"locomotion": ["profile", "legs"]}, entity="w")
    assert r.method.term == "legs" and r.substitution is None
    assert [m for m, _ in r.skipped] == ["loco.profile_cycle"]
    r = resolve("locomotion", {}, policy={"locomotion": ["hem", "glide"]}, entity="b")
    assert r.method.term == "glide" and r.substitution is None
    assert [m for m, _ in r.skipped] == ["loco.hem_sway"]


def test_a_policy_entirely_inapplicable_leaves_the_chain_and_lists_every_skip():
    r = resolve("locomotion", {}, policy={"locomotion": ["hem", "profile"]})
    assert r.method.id == "loco.glide" and r.source == "chain" and r.substitution is None
    assert [m for m, _ in r.skipped] == ["loco.hem_sway", "loco.profile_cycle"]


def test_a_failed_request_is_still_fatal_when_a_policy_then_chooses():
    """Only the author's request is a request: when IT does not apply, the
    record stays ``missing`` (fatal under ``--strict-assets``)."""
    r = resolve("locomotion", {}, requested="hem", policy={"locomotion": ["rock"]})
    assert r.method.id == "loco.rock"
    assert r.substitution.reason == "missing" and r.substitution.fatal
    assert r.substitution.requested == "loco.hem_sway"


def test_the_authors_request_outranks_the_policy_and_policies_layer_shot_first():
    r = resolve("locomotion", LEGS, requested="legs", policy={"locomotion": ["loco.rock"]})
    assert r.method.id == "loco.legged_cycle" and r.substitution is None
    layered = Policy.layered({"locomotion": ["hem"]}, {"locomotion": ["rock"], "speech": ["pulse"]})
    assert [c.method for c in layered.choices("locomotion")] == ["hem"]
    assert [c.method for c in layered.choices("speech")] == ["pulse"]


def test_policy_args_reach_the_resolution():
    r = resolve("speech", {}, policy={"speech": [{"method": "pulse", "args": {"strength": 0}}]})
    assert r.method.id == "speech.pose_only" and r.args["strength"] == 0


def test_a_version_pin_that_no_longer_holds_is_an_error_not_a_silent_change():
    with pytest.raises(VocabularyError, match="pinned"):
        resolve("locomotion", LEGS, requested={"method": "loco.legged_cycle", "version": "0"})


def test_a_policy_choice_on_an_aspect_that_records_its_fallback_stays_information():
    """Reiniger mimes (``speech: [pulse]``) a figure that has a mouth chart:
    speech records its own chain's fallback as ``missing``, but a policy's
    choice is never that record (an#334)."""
    r = resolve("speech", {"face.mouth": {}}, policy={"speech": ["pulse"]})
    assert r.method.id == "speech.pose_only" and r.source == "policy"
    assert r.substitution.reason == "policy" and not r.substitution.fatal


def test_a_declared_method_is_the_request_unless_the_switch_puts_the_policy_first(monkeypatch):
    """cutan#36 is the maintainer's: ``DECLARED_OUTRANKS_POLICY`` is the one line
    that decides whether a character's declared gait beats a style's order."""
    from an.semantic import matcher

    south_park = {"locomotion": ["loco.rock"]}
    r = resolve("locomotion", LEGS, declared="legs", policy=south_park)
    assert r.method.id == "loco.legged_cycle" and r.source == "request" and r.substitution is None
    r = resolve("locomotion", {}, declared="hem", policy=south_park)
    assert r.substitution.reason == "missing" and r.substitution.fatal  # a declaration is honoured or said
    # the author's explicit request outranks the declaration either way
    r = resolve("locomotion", LEGS, requested="hop", declared="legs", policy=south_park)
    assert r.method.id == "loco.hop"

    monkeypatch.setattr(matcher, "DECLARED_OUTRANKS_POLICY", False)
    r = resolve("locomotion", LEGS, declared="legs", policy=south_park)
    assert r.method.id == "loco.rock" and r.source == "policy"
    # the declaration is now the order's last entry: with no policy it still decides
    r = resolve("locomotion", LEGS, declared="hop")
    assert r.method.id == "loco.hop" and r.source == "policy"
    # and one that cannot be honoured is a skipped entry, not a fatal record
    r = resolve("locomotion", {}, declared="hem")
    assert r.method.id == "loco.glide" and r.substitution is None
    assert [m for m, _ in r.skipped] == ["loco.hem_sway"]
    r = resolve("locomotion", LEGS, requested="hop", declared="legs", policy=south_park)
    assert r.method.id == "loco.hop"
    # the chosen entry, as written: its own args, not the method's defaults
    r = resolve("locomotion", {}, declared={"method": "hop", "args": {"hop_height": 9}})
    assert r.choice.method == "hop" and dict(r.choice.args) == {"hop_height": 9}
    assert resolve("locomotion", {}).choice is None  # a chain link


def test_describe_says_what_each_aspect_resolves_to_under_a_policy():
    from an.semantic.describe import describe_profile, format_description

    d = describe_profile(LEGS, aspects=("locomotion",), policy={"locomotion": ["profile", "bounce"]})
    under = d["aspects"]["locomotion"]["under_policy"]
    assert under["method"] == "loco.bounce" and under["source"] == "policy"
    assert under["substitution"]["reason"] == "policy"
    assert under["skipped"] == [{"method": "loco.profile_cycle", "missing": ["swap.view:side"]}]
    assert d["aspects"]["locomotion"]["default"] == "loco.legged_cycle"  # the policy-free answer stays
    text = format_description(d, policy_label="south_park")
    assert "under south_park: loco.bounce (policy)" in text and "skipped loco.profile_cycle" in text
    d = describe_profile(LEGS, aspects=("locomotion",), policy={"locomotion": ["shuffle"]})
    assert "under the policy: loco.shuffle (policy; needs limbs.legs)" in format_description(d)
    # a declared gait outranks the policy (today's rule), as the compiler does
    d = describe_profile(LEGS, aspects=("locomotion",), declared={"gait": "legs"}, policy={"locomotion": ["bounce"]})
    assert d["aspects"]["locomotion"]["under_policy"]["method"] == "loco.legged_cycle"
