"""The style specs (`cutan.styles`, applied by the `cutan-style` skill) claim that every `live` key maps onto a
shipped feature. This checks each claim against the code, so a spec cannot
drift into asking for something `an` does not do.

`guidance` is free-form on purpose — it is what `an` does NOT do yet — so the
one thing checked about it is that nothing from it has leaked into `live`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from an.adapters.cutout.easing import EASING_FUNCS, apply_easing
from an.audio.effects import normalize_effects
from an.environments import EnvironmentDescriptor
from an.ir.camera import CAMERA_MOVES
from an.ir.schema import Meta, SoundCue, Transition
from cutan.motion import PRESETS
from an.styles import StylePack, SurfaceTreatment
from cutan.styles import style_spec, style_spec_path, style_specs
from cutan.verify.style import StyleLintVerifier

SPECS = style_specs()
SKILL_DIR = Path(__file__).resolve().parents[1] / ".claude" / "skills" / "cutan-style"

#: Every key `live` may carry, and nothing else.
LIVE_KEYS = {
    "meta", "style_pack", "environment", "camera", "easing",
    "tween_duration_s", "shots", "characters", "motion_presets",
    "transitions", "sound", "voice", "glow_template",
}
TOP_KEYS = {
    "style", "title", "cost_class", "cost_note", "live", "targets", "prosody_targets", "guidance"
}
COST_CLASSES = {"low", "low_to_medium", "medium", "high", "very_high"}
GENERATORS = {"offline", "promote"}


def _load(name):
    return style_spec(name)


def test_the_six_researched_styles_have_specs():
    assert set(SPECS) >= {
        "south_park", "oversimplified", "kurzgesagt", "gilliam", "reiniger", "norstein"
    }


@pytest.fixture(params=SPECS)
def spec(request):
    return _load(request.param) | {"_stem": style_spec_path(request.param).stem}


def test_shape(spec):
    assert set(spec) - {"_stem"} <= TOP_KEYS
    assert spec["style"] == spec["_stem"]
    assert spec["cost_class"] in COST_CLASSES
    assert set(spec["live"]) <= LIVE_KEYS, set(spec["live"]) - LIVE_KEYS


def test_meta_is_a_valid_meta(spec):
    meta = spec["live"]["meta"]
    m = Meta(**meta)
    if m.step_hz is not None:
        assert m.step_hz <= m.fps
    if "style_pack" in meta:
        assert spec["live"]["style_pack"]["name"] == meta["style_pack"]


def test_style_pack_only_names_reachable_roles(spec):
    pack = spec["live"].get("style_pack")
    if pack is not None:
        StylePack(**pack)  # refuses an unreachable or unknown role, or a bad treatment


def test_surface_treatments_are_live_where_they_ship():
    """an#163: the outline, the paper-gap shadow and the grain are compiled
    now, so South Park carries them under `live` (and no longer under
    `guidance`), and Kurzgesagt's glow is a per-entity template."""
    sp = _load("south_park")
    pack = StylePack(**sp["live"]["style_pack"])
    assert pack.surface.outline and pack.surface.shadow and pack.grain
    assert not {"outline", "paper_gap_shadow", "paper_grain"} & set(sp["guidance"])
    kz = _load("kurzgesagt")
    assert "glow" not in kz["guidance"]


def test_a_glow_template_is_a_valid_per_entity_treatment(spec):
    template = spec["live"].get("glow_template")
    if template is not None:
        assert SurfaceTreatment(**template).glow
        StylePack(name="x", entity_surfaces={"sun": template})


def test_environment_is_a_preset_or_a_valid_descriptor(spec):
    env = spec["live"].get("environment")
    if env is None:
        return
    assert set(env) in ({"preset"}, {"descriptor"})
    if "preset" in env:
        assert env["preset"] in {"park", "indoor", "night", "sunset", "default"}
    else:
        d = EnvironmentDescriptor(**env["descriptor"])
        names = [p.name for p in d.planes]
        assert d.characters_after is None or d.characters_after in names


def test_camera_moves_exist(spec):
    cam = spec["live"]["camera"]
    assert cam["default"] in CAMERA_MOVES
    assert cam["default"] in cam["allowed"]
    assert set(cam["allowed"]) <= set(CAMERA_MOVES)


def test_easings_exist(spec):
    for e in spec["live"]["easing"]:
        if isinstance(e, str):
            assert e in EASING_FUNCS
        else:
            apply_easing(e, 0.5)  # a 4-point cubic-Bezier the evaluator accepts


def test_the_default_easing_is_live_and_is_the_style_s_house_curve(spec):
    """``meta.default_easing`` (an#166) is a real `Meta` key the compiler reads,
    so every spec sets it — to the FIRST of ``live.easing``, the style's house
    curve; the rest of that list are the curves a move may name instead."""
    meta = Meta(**spec["live"]["meta"])
    assert meta.default_easing is not None
    assert meta.default_easing == spec["live"]["easing"][0]
    apply_easing(meta.default_easing, 0.5)


def test_ranges_and_characters(spec):
    live = spec["live"]
    lo, hi = live["tween_duration_s"]
    assert 0 < lo <= hi
    shots = live["shots"]
    assert shots["range_s"][0] <= shots["mean_s"] <= shots["range_s"][1]
    chars = live["characters"]
    assert chars["generate"] in GENERATORS
    assert set(chars) <= {"generate", "mouth_variants", "tint", "view"} | set(FACTORY_KNOBS)
    if "tint" in chars:
        assert chars["tint"].startswith("#") and len(chars["tint"]) == 7


def test_a_spec_s_default_view_is_one_the_factory_draws(spec, tmp_path):
    """`live.characters.view` (an#197; Reiniger's profile) is a `set` of `view`
    on each character root, so it must be a key of the `view` set an offline
    character is built with — checked on a BUILT character, not a constant."""
    from cutan.characters import new_character
    from cutan.characters.schema import VIEW_CHANNEL, CharacterDescriptor

    view = spec["live"]["characters"].get("view")
    if view is None:
        return
    assert spec["live"]["characters"]["generate"] == "offline", "only the factory draws views"
    path = new_character(tmp_path, name="c", use_dicebear=False)
    desc = CharacterDescriptor.model_validate_json(path.read_text("utf-8"))
    assert view in desc.asset_sets[VIEW_CHANNEL]


def test_the_reiniger_silhouette_defaults_to_the_profile():
    """The evidence run faked Reiniger's profile with a squash: the spec says
    `side`, and its turns stay in profile."""
    live = _load("reiniger")["live"]
    assert live["characters"]["view"] == "side"
    assert "turn" in live["motion_presets"]


@pytest.mark.parametrize("style", ["south_park", "oversimplified"])
def test_the_dialogue_styles_turn_with_the_preset(style):
    assert "turn" in _load(style)["live"]["motion_presets"]


#: `live.characters` keys that are `new_character` keyword arguments, with how a
#: spec may spell each: `hat`, `hair_style` and `hair_length` list the choices a
#: cast picks from, and `palette` is `per_character` (the style's identity is
#: each figure's own costume) or a role -> colour map.
FACTORY_KNOBS = ("build", "head_scale", "hat", "hair_style", "hair_length", "sash", "palette")
#: The knobs a spec spells as a list of choices, with the factory's choices.
CHOICE_KNOBS = ("hat", "hair_style", "hair_length")


def test_character_knobs_are_live_factory_settings(spec, tmp_path):
    """Every factory knob a spec names is a real `new_character` argument with a
    value the factory accepts — checked by BUILDING one character per hat."""
    import inspect

    from cutan.characters import new_character
    from cutan.characters.factory import BUILDS, HAIR_LENGTHS, HAIR_STYLES, HATS

    chars = spec["live"]["characters"]
    knobs = {k: chars[k] for k in FACTORY_KNOBS if k in chars}
    if not knobs:
        return
    params = inspect.signature(new_character).parameters
    assert set(knobs) <= set(params), set(knobs) - set(params)
    if "build" in knobs:
        assert knobs["build"] in BUILDS
    known = {"hat": HATS, "hair_style": HAIR_STYLES, "hair_length": HAIR_LENGTHS}
    choices = {k: knobs.pop(k) for k in CHOICE_KNOBS if k in knobs}
    for k, listed in choices.items():
        assert isinstance(listed, list) and set(listed) <= set(known[k]), (k, listed)
    palette = knobs.pop("palette", None)
    assert palette == "per_character" or isinstance(palette, (dict, type(None)))
    if isinstance(palette, dict):
        knobs["palette"] = palette
    if chars["generate"] != "offline":
        return
    # One character per listed choice (the others at their defaults): each
    # choice the spec offers is one the factory builds with the style's knobs.
    built = 0
    for k, listed in choices.items():
        for value in listed:
            if k == "hair_length" and choices.get("hair_style") == ["bald"]:
                continue  # a cast of bald figures has no hair to grow
            new_character(
                tmp_path, name=f"c{built}", use_dicebear=False, **{k: value}, **knobs
            )
            built += 1
    if not built:
        new_character(tmp_path, name="c0", use_dicebear=False, **knobs)


def test_targets_are_measurable(spec):
    v = StyleLintVerifier(spec)  # refuses an unknown target or a bad range
    assert v.targets and v.style == spec["style"]


def test_motion_presets_exist(spec):
    assert set(spec["live"].get("motion_presets", [])) <= set(PRESETS)


def test_transitions_are_valid_transitions(spec):
    """`live.transitions` maps a name to a `Transition`; `default` is required."""
    transitions = spec["live"].get("transitions")
    if transitions is None:
        return
    assert "default" in transitions
    for name, t in transitions.items():
        Transition(**t)  # refuses an unknown kind or a bad colour


def test_sound_bed_is_a_valid_cue(spec):
    """`live.sound.bed` is a `SoundCue` minus the asset key the user supplies."""
    sound = spec["live"].get("sound")
    if sound is None:
        return
    assert set(sound) <= {"bed"}
    cue = SoundCue(sound="bed", **sound["bed"])
    assert cue.loop  # a bed runs under the whole film


def test_voice_effects_are_valid_voice_effects(spec):
    """`live.voice.effects` is the `effects` of a voice document in the voices
    store (an#163): `normalize_effects` refuses an unknown effect or range."""
    voice = spec["live"].get("voice")
    if voice is None:
        return
    assert set(voice) <= {"effects", "roles"} and voice
    if "effects" in voice:
        assert normalize_effects(voice["effects"])  # non-empty: a spec that says nothing omits the key


def test_voice_roles_are_valid_expressive_voice_documents(spec):
    """`live.voice.roles` maps a role to a partial voice document (an#209): only
    the keys `ElevenLabsTTS` reads, valid values, and a model that performs the
    cues the style's lines carry — and a role the prosody targets can check."""
    from an.audio.effects import normalize_effects
    from an.audio.elevenlabs_tts import ElevenLabsTTS, takes_audio_tags
    from an.audio.takes import make_take_scorer, style_voice_role, takes_spec

    roles = spec["live"].get("voice", {}).get("roles")
    if roles is None:
        return
    tts = ElevenLabsTTS(api_key="unused")
    for role, doc in roles.items():
        assert set(doc) <= {"provider", "model_id", "voice_settings", "seed", "effects", "takes"}, role
        assert "voice_id" not in doc  # the cast supplies it, by name
        opts = tts.synthesis_options(doc, direction=["deadpan"])  # raises on a bad setting
        assert takes_audio_tags(opts["model_id"]), role
        assert role in spec.get("prosody_targets", {}), f"role {role!r} has no prosody targets"
        if "effects" in doc:
            assert normalize_effects(doc["effects"]), role  # raises on a bad effect; never a no-op
        # `takes` names its targets; resolved, every cue the role re-rolls builds its scorer
        resolved = style_voice_role(spec, role).get("takes")
        if resolved is not None:
            for cue in [None, *resolved.get("cues", {})]:
                found = takes_spec(resolved, direction=[cue] if cue else None)
                if found is not None:
                    make_take_scorer(found)


def test_prosody_targets_are_measurable(spec):
    """`prosody_targets` maps a role or device to `an.verify.prosody` targets."""
    from an.verify.prosody import validate_targets

    for name, targets in spec.get("prosody_targets", {}).items():
        assert targets, name
        validate_targets(targets)


def test_voice_acting_devices_name_prosody_targets(spec):
    devices = spec.get("guidance", {}).get("voice_acting", {}).get("devices", {})
    known = set(spec.get("prosody_targets", {}))
    for name, device in devices.items():
        refs = device["targets"] if isinstance(device["targets"], list) else [device["targets"]]
        assert set(refs) <= known, (name, refs)


def test_south_park_raises_its_voices():
    fx = _load("south_park")["live"]["voice"]["effects"]
    assert 0 < fx["pitch_semitones"] <= 12


# -----------------------------------------------------------------------------
# The lint's advice agrees with the spec (e2e finding 5)
# -----------------------------------------------------------------------------

#: Advice that would break a spec that SETS step_hz.
_UNSTEP_ADVICE = ("drop `step_hz`", "step_hz: null", "raise `step_hz`", "lower `step_hz`",
                  "higher `step_hz`", "set `step_hz` to")
#: Advice that would break a spec that leaves step_hz UNSET.
_STEP_ADVICE = ("set `step_hz`", "raise `step_hz`", "lower `step_hz`", "higher `step_hz`",
                "`step_hz` to fps")


def test_the_lint_never_advises_against_the_spec(spec):
    """South Park (step_hz 12) was told "drop `step_hz`" for a high held-frame
    share, and OverSimplified (no step_hz) "set `step_hz`" for a low one — both
    break the style they were measuring. Every fix, both directions, every metric."""
    from cutan.verify.style import METRICS, _fix_for

    live = spec["live"]
    stepped = live["meta"].get("step_hz") is not None
    banned = _UNSTEP_ADVICE if stepped else _STEP_ADVICE
    for name in METRICS:
        for low in (True, False):
            fix = _fix_for(name, low, live)
            hits = [b for b in banned if b in fix]
            assert not hits, (spec["style"], name, "low" if low else "high", fix)
            assert "{" not in fix, fix  # every placeholder filled


# -----------------------------------------------------------------------------
# Guidance must not call a shipped feature missing (e2e finding 1)
# -----------------------------------------------------------------------------

#: A phrase that says a feature is absent, and the shipped thing that makes it
#: false. The e2e agent, following an-style literally, would have told its user
#: the date card and the map arrow were unsupported — while the `an` skill
#: documented text props, path props and plane environments.
STALE_ABSENCE_CLAIMS = {
    r"\bno text (node|layer|primitive|prop)": "text props ship (an#155, an.text.TextDescriptor)",
    r"has no text\b": "text props ship (an#155)",
    r"\bno map layer": "plane environments (an#110) + path props (an#160) build a map",
    r"\bno (path|stroke|line|arrow) (node|primitive|prop|layer)": "path props ship (an#160, an.paths.PathDescriptor)",
    r"\bno (plane|parallax|multiplane) (layer|support)": "plane environments ship (an#110)",
    r"\bno (sound|audio) (layer|support|track)": "shot and meta `sounds` ship (an#176)",
    r"\bno transitions?\b": "shot transitions ship (an#176)",
    r"\b(use|needs?) side-view art|\bno (profile|side[- ]view|turnaround)": "views ship (an#197): `live.characters.view`, `play: turn`",
}

SKILL_MD = SKILL_DIR / "SKILL.md"


def _strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _strings(v)


def test_guidance_does_not_call_a_shipped_feature_missing(spec):
    import re

    found = [
        (text, why)
        for text in _strings(spec.get("guidance", {}))
        for pat, why in STALE_ABSENCE_CLAIMS.items()
        if re.search(pat, text.lower())
    ]
    assert not found, found


def test_the_an_style_skill_does_not_call_a_shipped_feature_missing():
    import re

    text = SKILL_MD.read_text(encoding="utf-8").lower()
    found = [why for pat, why in STALE_ABSENCE_CLAIMS.items() if re.search(pat, text)]
    assert not found, found


def test_the_skill_loads_its_specs_from_the_package_not_from_a_copy():
    """The specs are package data (cutan#4): the skill holds no copy to drift, names
    no path into a skill folder, and says how to load a spec by its name."""
    text = SKILL_MD.read_text(encoding="utf-8")
    assert not (SKILL_DIR / "styles").exists()
    assert ".claude/skills/cutan-style/styles" not in text
    assert "<skill>/styles" not in text
    assert "python -m cutan.styles" in text and "cutan.style_spec(" in text
    for name in SPECS:
        assert f"`{name}`" in text, f"the skill does not name the shipped style {name!r}"
