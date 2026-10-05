"""The cut-out genre's methods and aspects, and their compile-time resolution (ADR 0002).

The first two aspects of ADR 0002's first slice, as registry data:

=============  ==============================================  =====================  ==========
aspect         method (spelled)                                requires               chain
=============  ==============================================  =====================  ==========
locomotion     ``loco.legged_cycle`` (``legs``)                ``limbs.legs``         1st
locomotion     ``loco.profile_cycle`` (``profile``)            ``limbs.legs``,        by request
                                                               ``swap.view:side``
locomotion     ``loco.shuffle`` (``shuffle``)                  ``limbs.legs``         by request
locomotion     ``loco.hem_sway`` (``hem``)                     ``limbs.legs``         by request
locomotion     ``loco.waddle`` (``waddle``)                    nothing                by request
locomotion     ``loco.hop`` (``hop``)                          nothing                by request
locomotion     ``loco.bounce`` (``bounce``)                    nothing                by request
locomotion     ``loco.rock`` (``rock``)                        nothing                by request
locomotion     ``loco.glide`` (``glide``)                      nothing                last link
speech         ``speech.mouth_chart`` (``mouth_chart``)        ``face.mouth``         1st
speech         ``speech.pose_only`` (``pulse``)                nothing                last link
expression     ``expr.full_face`` (``full_face``)              ``face.brows``         1st
expression     ``expr.without_brows`` (``without_brows``)      nothing                last link
=============  ==============================================  =====================  ==========

**Locomotion: the gaits of an#224** (classified in
``misc/docs/locomotion_gaits.md``). A walk's ``gait`` arg is the author's
request, the descriptor's ``gait`` a declared override (reported as such);
with neither, the chain picks ``legs`` when the character affords a leg pair
and ``glide`` when it does not (the rock, the last link before an#224, read as a
metronome on robe figures and is now a gait an author asks for). A requested
gait the rig cannot honour (``hem`` on a legless blob, ``profile`` on a
character with no side view) is a **recorded substitution**: a warning, fatal
under ``--strict-assets``, and ``why_not`` names what would enable it.

**Speech gains a requirement-free last link.** A character whose face is baked
into its art (``face_overlay: false``) used to speak with a frozen mouth; it now
pulses its head on each syllable (:func:`cutan.motion.speech_pulse`, parametrised:
``strength``, ``part``, ``attack``, ``release``; ``strength: 0`` is a mime).

**Expression names what reads when the brows cannot** (an#252). A hat the
factory could not seat above the brows (recorded in ``occluded``), or brow
slots without art, leave ``face.brows`` unafforded: the face then acts with
the lids, the gaze and the mouth form (``expr.without_brows``), recorded. Both
methods compile to the same face channels — the solver drives whatever the
rig binds — so the aspect is not consulted by the compiler; ``an validate``
reports the fall (:func:`check_brow_acting`) and ``an character
capabilities`` shows it with the remedy.

The asset profile the compiler resolves against is the character analyser's
(``an.capabilities.affordances``), fed what the compiler actually has: the
descriptor and the art its store holds, or — for a rig drawn from ``parts`` or
the placeholder — the parts the builder built. Characters only: other entity
kinds have no analyser yet, and keep the preset's own rig lookup.

Importing this module registers nothing: :data:`cutan.genre.CUTOUT` lists
:data:`CUTOUT_METHODS` and :data:`CUTOUT_ASPECTS`.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from an.semantic.entries import Aspect, Method
from an.semantic.seeds import schema_of_callable

__all__ = [
    "CUTOUT_ASPECTS",
    "CUTOUT_METHODS",
    "EXPRESSION",
    "LOCOMOTION",
    "SPEECH",
    "check_brow_acting",
    "check_declared_speech",
    "check_walk_gaits",
    "gait_problem",
    "locomotion_args",
    "compile_profile",
    "speech_problems",
    "normalise_gait_args",
    "resolve_walk_gait",
    "SpeechPlan",
    "speech_plan",
    "substitution_record",
    "syllable_beats",
    "walk_preset_context",
]

#: The aspect names (persisted in substitution records).
LOCOMOTION: str = "locomotion"
SPEECH: str = "speech"
EXPRESSION: str = "expression"

#: The motion preset whose gait is the locomotion aspect's.
WALK_PRESET: str = "walk"
#: The entity kind whose assets have an analyser, and so resolve on the registry.
CHARACTER_KIND: str = "character"

#: Walk parameters each locomotion method reads (its params; the rest are the
#: walk's own — where to, how many steps).
_LEGGED_PARAMS: tuple[str, ...] = ("stride", "lift", "arm_swing", "bob")
_HEM_PARAMS: tuple[str, ...] = ("hem_tilt", "rock", "bob", "stride", "arm_swing")
_ROCK_PARAMS: tuple[str, ...] = ("rock", "bob", "arm_swing")
_PROFILE_PARAMS: tuple[str, ...] = ("stride", "bob", "arm_swing")
_WADDLE_PARAMS: tuple[str, ...] = ("rock", "lift", "bob", "arm_swing")
_HOP_PARAMS: tuple[str, ...] = ("hop_height", "arm_swing")
_BOUNCE_PARAMS: tuple[str, ...] = ("bob", "lift", "stride", "arm_swing")
_GLIDE_PARAMS: tuple[str, ...] = ("bob", "lean", "arm_swing")
#: Rhubarb's closed shapes: a syllable starts where the mouth opens out of one.
CLOSED_VISEMES: frozenset[str] = frozenset({"A", "X"})
#: Pulses closer than this are one syllable.
DFLT_MIN_BEAT_GAP_S: float = 0.18


def _walk_params(gait: str, names: Iterable[str]) -> dict[str, Any]:
    """A gait's params as JSON Schema: its own defaults (a length's at drawn scale 1)."""
    from cutan.motion import SCALED_GAIT_PARAMS, gait_params

    defaults = gait_params(gait)
    names = ("step_s", "step_length", *names)
    return {
        "type": "object",
        "properties": {
            n: {
                "type": "number",
                "default": defaults[n],
                **(
                    {"description": "scene px at drawn scale 1; scales with the figure"}
                    if n in SCALED_GAIT_PARAMS
                    else {}
                ),
            }
            for n in dict.fromkeys(names)
        },
    }


def _walk_expand(gait: str) -> Callable[[Mapping[str, Any], Any], Any]:
    def expand(params: Mapping[str, Any], context: Any):
        from cutan.motion import walk

        ctx = dict(context or {})
        return walk(ctx.pop("target"), gait=gait, **ctx, **dict(params))

    return expand


def _pulse_expand(params: Mapping[str, Any], context: Any):
    from cutan.motion import speech_pulse

    ctx = dict(context or {})
    return speech_pulse(ctx.pop("target"), **ctx, **dict(params))


def _pulse_params() -> dict[str, Any]:
    from cutan.motion import speech_pulse

    return schema_of_callable(speech_pulse, skip=("target", "rest", "beats"))


#: Every locomotion method's version (ADR 0003 decision 2): bumped together
#: when the walk they expand through changes for the same args. 2: walk v4
#: (cutan#14-#16, #18, #20). A scene pinned to "1" fails validation rather
#: than walking differently.
LOCO_VERSION: str = "2"

_LEGS_REMEDY = (
    "split the legs into two slots named leg_l/leg_r, each with its art, "
    "pivoted at the hip (an-art-package skill; `an character new` builds them)"
)

LOCO_LEGGED = Method(
    "loco.legged_cycle",
    version=LOCO_VERSION,
    aspect=LOCOMOTION,
    name="legs",
    title="legged walk cycle",
    description=(
        "a legged walk cycle: in profile the legs swing about the hip in "
        "opposition, facing the camera the stepping leg lifts; the arms swing "
        "against the legs"
    ),
    params=_walk_params("legs", _LEGGED_PARAMS),
    requires=("limbs.legs",),
    remedies={"limbs.legs": _LEGS_REMEDY},
    examples=(
        {
            "kind": "play",
            "target": "ned",
            "animation": "walk",
            "args": {"gait": "legs"},
        },
    ),
    expand=_walk_expand("legs"),
)
LOCO_HEM = Method(
    "loco.hem_sway",
    version=LOCO_VERSION,
    aspect=LOCOMOTION,
    name="hem",
    title="hem sway",
    description=(
        "a robe figure's walk: the leg slots are the two halves of the hem, which "
        "tilt in turn about the hip while the body sways and bobs"
    ),
    params=_walk_params("hem", _HEM_PARAMS),
    requires=("limbs.legs",),
    remedies={
        "limbs.legs": (
            "carve the robe's hem into two halves on slots leg_l/leg_r, pivoted at "
            "the hip, and declare `gait: hem` in character.json"
        )
    },
    examples=(
        {"kind": "play", "target": "ned", "animation": "walk", "args": {"gait": "hem"}},
    ),
    expand=_walk_expand("hem"),
)
LOCO_ROCK = Method(
    "loco.rock",
    version=LOCO_VERSION,
    aspect=LOCOMOTION,
    name="rock",
    title="rock and bob",
    description=(
        "no leg moves: the body rocks side to side and bobs once per step while "
        "it travels (a blob, a sack, anything drawable)"
    ),
    params=_walk_params("rock", _ROCK_PARAMS),
    examples=(
        {
            "kind": "play",
            "target": "ned",
            "animation": "walk",
            "args": {"gait": "rock"},
        },
    ),
    expand=_walk_expand("rock"),
)
_SIDE_VIEW_REMEDY = (
    "give the character a side view: `an character add-views <name>` (a "
    "factory character), or carve its art in profile and declare `rest_view: "
    "side` in character.json"
)


def _gait_method(
    id_: str, gait: str, title: str, description: str, params: tuple[str, ...], **kw
) -> Method:
    return Method(
        id_,
        version=LOCO_VERSION,
        aspect=LOCOMOTION,
        name=gait,
        title=title,
        description=description,
        params=_walk_params(gait, params),
        examples=(
            {
                "kind": "play",
                "target": "ned",
                "animation": "walk",
                "args": {"gait": gait},
            },
        ),
        expand=_walk_expand(gait),
        **kw,
    )


LOCO_PROFILE = _gait_method(
    "loco.profile_cycle",
    "profile",
    "profile walk cycle",
    "the four poses of a walk seen in profile (contact, down, passing, up): the "
    "legs swing about the hip in opposition whatever the view in force, the "
    "body sinks after each contact and rises before the next (Reiniger's "
    "silhouettes, any figure drawn side-on)",
    _PROFILE_PARAMS,
    requires=("limbs.legs", "swap.view:side"),
    remedies={"limbs.legs": _LEGS_REMEDY, "swap.view:side": _SIDE_VIEW_REMEDY},
)
LOCO_SHUFFLE = _gait_method(
    "loco.shuffle",
    "shuffle",
    "shuffle",
    "the feet barely leave the ground: short, quick steps with little bob and "
    "arms close to the body (the old, the tired, the cautious)",
    _LEGGED_PARAMS,
    requires=("limbs.legs",),
    remedies={"limbs.legs": _LEGS_REMEDY},
)
LOCO_WADDLE = _gait_method(
    "loco.waddle",
    "waddle",
    "waddle",
    "the body rocks from foot to foot and bobs on each step; legs, if any, lift "
    "in turn (a penguin, a toddler, a squat figure)",
    _WADDLE_PARAMS,
)
LOCO_HOP = _gait_method(
    "loco.hop",
    "hop",
    "hop",
    "the whole figure jumps on every step while it travels (a bird, a "
    "kangaroo, a gleeful character, anything drawable)",
    _HOP_PARAMS,
)
LOCO_BOUNCE = _gait_method(
    "loco.bounce",
    "bounce",
    "bounce",
    "the body bobs on every step while it slides; legs, if any, only flick "
    "(the South Park walk)",
    _BOUNCE_PARAMS,
)
LOCO_GLIDE = _gait_method(
    "loco.glide",
    "glide",
    "glide",
    "the figure slides, leaning into the move with a gentle bob; no limb "
    "moves (a robe figure, a ghost, a sack — the default for any figure "
    "without legs)",
    _GLIDE_PARAMS,
)
SPEECH_CHART = Method(
    "speech.mouth_chart",
    aspect=SPEECH,
    name="mouth_chart",
    title="mouth chart lip-sync",
    description=(
        "lip-sync on the character's mouth chart: the line's visemes swap the "
        "mouth drawings (the nine Rhubarb shapes, or the character's own set)"
    ),
    requires=("face.mouth",),
    remedies={
        "face.mouth": (
            "give the character an overlay mouth: a `mouth` slot with the viseme "
            "set's drawings (`an character mouths <dir>`) and face_overlay: true"
        )
    },
)
SPEECH_PULSE = Method(
    "speech.pose_only",
    aspect=SPEECH,
    name="pulse",
    title="speech pulse",
    description=(
        "no lip-sync: the head (or the body) pulses on each syllable, so a "
        "baked face or a mime still reads as speaking"
    ),
    params=_pulse_params(),
    examples=("a character with face_overlay: false speaks",),
    expand=_pulse_expand,
)

EXPR_FULL_FACE = Method(
    "expr.full_face",
    aspect=EXPRESSION,
    name="full_face",
    title="full-face expression",
    description=(
        "the expression acts with the whole face: the brows rise, knit and "
        "tilt, the lids open and close, the pupils move and the mouth takes "
        "the preset's form"
    ),
    requires=("face.brows",),
    remedies={
        "face.brows": (
            "keep the brows clear: `an character new` seats a hat above them at "
            "most head scales — at this one it could not, so use a larger "
            "--head-scale, another --hat or --hat none; for drawn art, redraw "
            "what covers the brows and remove the descriptor's `occluded` "
            "entry, or give the face brow slots (left_brow/right_brow) with art"
        )
    },
    examples=({"kind": "expression", "target": "ned", "preset": "surprised"},),
)
EXPR_WITHOUT_BROWS = Method(
    "expr.without_brows",
    aspect=EXPRESSION,
    name="without_brows",
    title="expression without brows",
    description=(
        "the brows cannot be seen acting (covered, or not drawn): the lids, the "
        "gaze and the mouth form carry the expression"
    ),
    examples=("a character whose hat covers its brows takes [surprised]",),
)

#: The genre's methods, as vocabulary entries (kind ``method``).
CUTOUT_METHODS: tuple[Method, ...] = (
    LOCO_LEGGED,
    LOCO_PROFILE,
    LOCO_SHUFFLE,
    LOCO_HEM,
    LOCO_WADDLE,
    LOCO_HOP,
    LOCO_BOUNCE,
    LOCO_ROCK,
    LOCO_GLIDE,
    SPEECH_CHART,
    SPEECH_PULSE,
    EXPR_FULL_FACE,
    EXPR_WITHOUT_BROWS,
)
#: The genre's aspects: each chain ends in a method that requires nothing.
CUTOUT_ASPECTS: tuple[Aspect, ...] = (
    Aspect(
        LOCOMOTION,
        chain=(LOCO_LEGGED.id, LOCO_GLIDE.id),
        description="how a character travels when it walks.",
        declared_by="gait",
    ),
    Aspect(
        SPEECH,
        chain=(SPEECH_CHART.id, SPEECH_PULSE.id),
        description="how a character shows that it is speaking.",
        declared_by="speech",
        # The pulse is new behaviour for a face that used to stay still: a
        # character that falls to it without declaring it is recorded, so
        # `--strict-assets` sees it (review-256 S1). Declare `speech: pulse`
        # to make it the request.
        records_fallback=True,
    ),
    Aspect(
        EXPRESSION,
        chain=(EXPR_FULL_FACE.id, EXPR_WITHOUT_BROWS.id),
        description="how a character's face shows an emotion.",
        applies_to=frozenset({CHARACTER_KIND}),
        # Brows that cannot act are a loss the author did not choose: said,
        # every time (an#252).
        records_fallback=True,
    ),
)


# -----------------------------------------------------------------------------
# Compile-time resolution
# -----------------------------------------------------------------------------


def compile_profile(
    descriptor: Any | None,
    *,
    built_parts: Iterable[str] = (),
    art_exists: Callable[[str], bool] | None = None,
) -> dict[str, dict[str, Any]]:
    """The character's profile, from what the compiler has: the analyser, fed honestly.

    ``descriptor`` is the migrated ``CharacterDescriptor`` (or ``None`` for a
    rig drawn from ``parts`` / the placeholder); ``art_exists(rel_path)`` the
    store's probe (``None``: the store cannot say, so every declared drawing
    counts — the rig builder's own rule); ``built_parts`` the part names the
    builder built under the entity (for a non-descriptor rig, they ARE its
    parts document).
    """
    from an.capabilities import affordances

    if descriptor is None:
        parts = sorted({p.split("/", 1)[0] for p in built_parts})
        return affordances({"parts": parts}, {}, kind=CHARACTER_KIND)
    art = {
        att.path: True
        for skin in descriptor.skins.values()
        for attachments in skin.slots.values()
        for att in attachments.values()
        if art_exists is None or art_exists(att.path)
    }
    return affordances(descriptor, art, kind=CHARACTER_KIND)


def resolve_walk_gait(
    entity: str,
    *,
    args: Mapping[str, Any],
    descriptor: Any | None,
    profile: Mapping[str, Mapping[str, Any]],
    policy: Any = None,
):
    """``(gait, resolution)`` of a walk on ``entity``: the locomotion method's spelling.

    The request is the walk's ``gait`` arg, else the descriptor's declared
    ``gait`` (an override of the derivation, and reported as one). An explicit
    ``legs`` arg names the limbs itself: a non-empty pair affords legs whatever
    the derivation says, ``()`` affords none.

    >>> gait, r = resolve_walk_gait("blob", args={"gait": "hem"}, descriptor=None, profile={})
    >>> gait, r.substitution.reason, r.substitution.missing
    ('glide', 'missing', ('limbs.legs',))
    """
    from an.semantic import resolve

    profile = dict(profile)
    legs = args.get("legs")
    if legs is not None:
        if legs:
            profile["limbs.legs"] = {"slots": list(legs), "overrides": ["legs arg"]}
        else:
            profile.pop("limbs.legs", None)
    requested = args.get("gait") or getattr(descriptor, "gait", None)
    r = resolve(LOCOMOTION, profile, requested=requested, policy=policy, entity=entity)
    return r.method.term, r


def locomotion_args(
    entity: str,
    args: Mapping[str, Any],
    *,
    descriptor: Any | None,
    profile: Mapping[str, Mapping[str, Any]],
    policy: Any = None,
) -> tuple[dict[str, Any], Any]:
    """``(args with its gait resolved, resolution)`` of a walk on ``entity``:
    the locomotion method the registry resolves (an#248) — the author's
    ``gait`` (a spelling, a method id or a pinned choice, spelled out first,
    its args joining the walk's), else the descriptor's, else the chain.

    ONE function for the compiler's expansion and for the walk's EXTENT (what a
    ``sequence`` waits for, :func:`walk_preset_context`), so the two cannot
    disagree about which gait runs (cutan#12).

    >>> args, r = locomotion_args("blob", {"gait": "hem", "distance": 80}, descriptor=None, profile={})
    >>> args["gait"], r.substitution.reason
    ('glide', 'missing')
    """
    args = normalise_gait_args(args)
    gait, resolution = resolve_walk_gait(
        entity, args=args, descriptor=descriptor, profile=profile, policy=policy
    )
    return {**args, "gait": gait}, resolution


def walk_preset_context(
    entity: str,
    args: Mapping[str, Any],
    *,
    descriptor: Any | None,
    profile: Mapping[str, Mapping[str, Any]] | None,
    scale: float,
    parts: Iterable[str] | None = None,
) -> dict[str, Any]:
    """What the compiler adds to a ``walk`` play's args before expanding it, as
    far as the walk's LENGTH depends on it: the resolved ``gait`` (when the
    entity resolves on the registry: ``profile`` given), the figure's drawn
    ``scale`` (its stage scale, cutan#13), and — off the registry, where the
    walk picks its own gait from the limbs it finds — the built ``parts``. The
    extent resolver reads this so a ``sequence`` waits exactly as long as the
    walk runs (cutan#12); the expansion itself resolves the same way (and
    records the substitution).

    >>> walk_preset_context("b", {"gait": "shuffle"}, descriptor=None, profile={}, scale=2.0)
    {'scale': 2.0, 'gait': 'glide'}
    >>> walk_preset_context("b", {"gait": "shuffle"}, descriptor=None, profile=None, scale=1.0)
    {'scale': 1.0}
    >>> walk_preset_context("b", {}, descriptor=None, profile=None, scale=1.0, parts=["head"])
    {'scale': 1.0, 'parts': {'head': {}}}
    """
    out: dict[str, Any] = {"scale": float(scale)}
    if profile is None:
        if parts is not None:
            out["parts"] = {p: {} for p in parts}
        return out
    from an.semantic import VocabularyError

    try:
        resolved, _ = locomotion_args(
            entity, args, descriptor=descriptor, profile=profile
        )
    except (VocabularyError, ValueError, TypeError):
        return out  # a bad gait is `cutout.play`'s to report; no extent
    if "gait" in resolved:
        out["gait"] = resolved["gait"]
    return out


def normalise_gait_args(args: Mapping[str, Any]) -> dict[str, Any]:
    """A walk's args with ``gait`` as the walk spells it (one of :data:`cutan.motion.GAITS`).

    ``gait`` may name a locomotion method by id (``loco.rock``) or be a choice
    ``{method, args, version}`` — the level-(a) form, and how a scene pins a
    method's version (ADR 0003 decision 2). The choice's ``args`` join the
    walk's (an explicit arg wins); a pin that no longer holds, or a method of
    another aspect, raises :class:`~an.semantic.VocabularyError`.

    >>> normalise_gait_args({"gait": {"method": "loco.legged_cycle", "args": {"stride": 0.5}, "version": "2"}})
    {'stride': 0.5, 'gait': 'legs'}
    >>> normalise_gait_args({"gait": "hem", "distance": 80})
    {'gait': 'hem', 'distance': 80}
    """
    from cutan.characters.schema import GAITS
    from an.semantic import Choice
    from an.semantic.matcher import _as_choice, _method

    gait = args.get("gait")
    if gait is None or (isinstance(gait, str) and gait in GAITS):
        return dict(args)
    choice = _as_choice(gait, LOCOMOTION)
    method = _method(choice, LOCOMOTION)
    rest = {k: v for k, v in args.items() if k != "gait"}
    extra = dict(choice.args) if isinstance(choice, Choice) else {}
    return {**extra, **rest, "gait": method.term}


def speech_problems(declared: Any) -> list[str]:
    """Why a character's declared ``speech`` cannot be honoured (empty: it can).

    An unknown method, a method of another aspect, or a pin to a version the
    registry no longer has; the message names the speech methods.

    >>> speech_problems("pulse"), speech_problems(None)
    ([], [])
    >>> speech_problems("flap")[0].startswith("speech 'flap'")
    True
    """
    from an.semantic import VocabularyError
    from an.semantic.matcher import _as_choice, _method

    if declared is None:
        return []
    try:
        _method(_as_choice(declared, SPEECH), SPEECH)
    except VocabularyError as e:
        name = declared.get("method") if isinstance(declared, Mapping) else declared
        return [f"speech {name!r} cannot be honoured: {e}"]
    return []


def check_declared_speech(ctx) -> None:
    """The cut-out genre's semantic check: each character's declared ``speech`` resolves."""
    store = ctx.stores.get("characters")
    if store is None:
        return
    for j, entity in enumerate(ctx.shot.entities):
        if entity.kind != CHARACTER_KIND or entity.ref not in store:
            continue
        try:
            doc = store[entity.ref]
        except KeyError:
            continue
        declared = doc.get("speech") if isinstance(doc, Mapping) else None
        for problem in speech_problems(declared):
            ctx.report.add(
                "error", f"{ctx.path}/entities/{j}", f"{entity.ref}: {problem}"
            )


def _brow_moves(preset: str | None, axes: Mapping[str, float] | None = None) -> bool:
    """Whether an expression (a preset, with axis overrides) moves a brow."""
    from cutan.expression.axes import BROW_AXES
    from cutan.expression.presets import preset_axes

    try:
        moved = preset_axes(preset, axes=axes)
    except ValueError:
        return False  # an unknown preset or axis is `cutout.expression`'s error
    return any(moved.get(a) for a in BROW_AXES)


def brow_acting_problem(doc: Any, *, entity: str) -> str | None:
    """Why ``entity``'s brows cannot act (its expression falls to
    ``expr.without_brows``), with the remedy — or ``None`` when they can, or when
    the character has no brow slots at all (nothing it ever had is lost).

    ``doc`` is the character's stored document; a procedural rig (no
    descriptor) has no brows to lose.
    """
    from cutan.characters.brows import brow_slots
    from cutan.characters.schema import CharacterDescriptor
    from an.ir.migrate import migrate
    from an.semantic import resolve

    if not isinstance(doc, Mapping) or doc.get("kind") != "CharacterDescriptor":
        return None
    desc = CharacterDescriptor.model_validate(
        migrate(dict(doc), kind="CharacterDescriptor")
    )
    if not desc.face_overlay or not brow_slots(desc):
        return None  # a face whose binding moves no brow has nothing to lose
    r = resolve(
        EXPRESSION, compile_profile(desc), entity=entity, entity_kind=CHARACTER_KIND
    )
    if r.substitution is None:
        return None
    from cutan.characters.brows import BROWS_FEATURE

    cover = desc.occluded.get(BROWS_FEATURE)
    why = f"{cover} covers its brows" if cover else "its brow slots have no art"
    remedy = EXPR_FULL_FACE.remedies["face.brows"]
    return (
        f"{why}, so the brows cannot be seen acting: the expression reads through "
        f"the lids, the gaze and the mouth only ({r.method.id}). To act with the "
        f"brows: {remedy}"
    )


def check_brow_acting(ctx) -> None:
    """The cut-out genre's semantic check: an expression that moves the brows of
    a character whose brows cannot act is reported (a warning) — the expression
    aspect's recorded fall to ``expr.without_brows`` (an#252)."""
    from an.ir.compose import flatten

    store = ctx.stores.get("characters")
    if store is None:
        return
    refs = {
        e.id: e.ref
        for e in ctx.shot.entities
        if e.kind == CHARACTER_KIND and e.ref in store
    }
    problems: dict[str, str | None] = {}

    def problem(entity: str) -> str | None:
        if entity not in problems:
            try:
                doc = store[refs[entity]]
            except KeyError:
                doc = None
            problems[entity] = brow_acting_problem(doc, entity=entity)
        return problems[entity]

    for k, action in enumerate(ctx.shot.actions or ()):
        for flat in flatten(action):
            leaf = flat.action
            if getattr(leaf, "kind", None) != "expression":
                continue
            entity = (getattr(leaf, "target", "") or "").split("/", 1)[0]
            if entity not in refs or not _brow_moves(leaf.preset, leaf.axes):
                continue
            if (p := problem(entity)) is not None:
                ctx.report.add("warning", f"{ctx.path}/actions/{k}", f"{entity}: {p}")
    for j, line in enumerate(ctx.shot.dialogue or ()):
        emotion = (line.emotion or "").strip().lower()
        if not emotion or line.speaker not in refs or not _brow_moves(emotion):
            continue
        if (p := problem(line.speaker)) is not None:
            ctx.report.add(
                "warning", f"{ctx.path}/dialogue/{j}/emotion", f"{line.speaker}: {p}"
            )


def gait_problem(
    doc: Any, *, entity: str, args: Mapping[str, Any], art_exists: Any = None
) -> str | None:
    """Why a walk on ``entity`` will not use the gait it asks for (its ``gait``
    arg, else the descriptor's), with what would enable it — or ``None``.

    ``doc`` is the character's stored document; ``art_exists`` the store's
    probe. The sentence is the one the compiler records (``asset_resolution``)
    when it substitutes the method, plus each missing capability's remedy.
    """
    from cutan.characters.schema import CharacterDescriptor
    from an.capabilities import remedy_for
    from an.ir.migrate import migrate

    if not isinstance(doc, Mapping) or doc.get("kind") != "CharacterDescriptor":
        return None
    desc = CharacterDescriptor.model_validate(
        migrate(dict(doc), kind="CharacterDescriptor")
    )
    args = normalise_gait_args(args)
    _, r = resolve_walk_gait(
        entity,
        args=args,
        descriptor=desc,
        profile=compile_profile(desc, art_exists=art_exists),
    )
    sub = r.substitution
    if sub is None or sub.reason != "missing":
        return None
    fixes = "; ".join(f"{m}: {remedy_for(m)}" for m in sub.missing)
    return f"{sub.sentence()}. To enable it — {fixes}"


def check_walk_gaits(ctx) -> None:
    """The cut-out genre's semantic check: a ``walk`` whose requested gait the
    character cannot honour is reported (a warning, before any render), with
    the gait it will walk instead and what would make the asked one apply
    (an#224, ADR 0002 decision 6)."""
    from an.ir.compose import flatten
    from an.stores._common import art_exists_for

    store = ctx.stores.get("characters")
    if store is None:
        return
    refs = {
        e.id: e.ref
        for e in ctx.shot.entities
        if e.kind == CHARACTER_KIND and e.ref in store
    }
    for k, action in enumerate(ctx.shot.actions or ()):
        for flat in flatten(action):
            leaf = flat.action
            if (
                getattr(leaf, "kind", None) != "play"
                or getattr(leaf, "animation", None) != WALK_PRESET
                or leaf.target not in refs
            ):
                continue
            try:
                doc = store[refs[leaf.target]]
                problem = gait_problem(
                    doc,
                    entity=leaf.target,
                    args=dict(leaf.args or {}),
                    art_exists=art_exists_for(store, refs[leaf.target]),
                )
            except (
                Exception
            ):  # a malformed gait or descriptor is `cutout.play`'s to report
                continue
            if problem is not None:
                ctx.report.add("warning", f"{ctx.path}/actions/{k}", problem)


def substitution_record(sub, *, entity_ref: str | None = None) -> dict[str, Any]:
    """A :class:`~an.capabilities.Substitution` as an ``asset_resolution`` entry.

    The compiled document's record generalised (ADR 0002 decision 6):
    ``kind: method``, ``store`` the aspect, ``ref`` what was asked for,
    ``resolved`` what was used, ``fallback`` whether ``--strict-assets`` makes
    it fatal.
    """
    return {
        "id": sub.entity,
        "kind": "method",
        "store": sub.aspect,
        "ref": sub.requested or "",
        "resolved": sub.chosen,
        "fallback": sub.fatal,
        "detail": sub.sentence(),
    }


def syllable_beats(line, *, min_gap_s: float = DFLT_MIN_BEAT_GAP_S) -> list[float]:
    """Syllable onsets of a dialogue line, in seconds from its start.

    From the line's viseme track (a syllable starts where the mouth opens out
    of a closed shape), else its word timings (one beat per word), else one
    beat at its start. Beats closer than ``min_gap_s`` merge.
    """
    times: list[float] = []
    track = getattr(line, "viseme_track", None)
    if track is not None and track.keyframes:
        closed = True
        for kf in sorted(track.keyframes, key=lambda k: float(k.time)):
            shape = str(kf.viseme).upper()
            if shape in CLOSED_VISEMES:
                closed = True
            elif closed:
                times.append(float(kf.time))
                closed = False
    elif getattr(line, "word_timings", None):
        times = [float(w.start) for w in line.word_timings]
    else:
        times = [0.0]
    end = float(line.duration) if line.duration is not None else float("inf")
    out: list[float] = []
    for t in sorted(times):
        if t < 0 or t >= end:
            continue
        if out and t - out[-1] < min_gap_s:
            continue
        out.append(round(t, 6))
    return out or [0.0]


@dataclass(frozen=True)
class SpeechPlan:
    """What the speech aspect decided for a shot: the actions it adds, and the
    speakers whose lip-sync it switched off (the viseme pass skips them)."""

    actions: tuple = ()
    no_lip_sync: frozenset = frozenset()


#: The motion preset ``speech.pose_only`` expands to.
PULSE_PRESET: str = "speech_pulse"


def _authored_pulse_speakers(shot) -> set[str]:
    """Speakers the author already pulses with an explicit ``play: speech_pulse``."""
    out: set[str] = set()
    stack = list(shot.actions or ())
    while stack:
        a = stack.pop()
        stack.extend(getattr(a, "children", None) or ())
        if getattr(a, "child", None) is not None:
            stack.append(a.child)
        if (
            getattr(a, "kind", None) == "play"
            and getattr(a, "animation", None) == PULSE_PRESET
        ):
            out.add(str(a.target).split("/", 1)[0])
    return out


def speech_plan(
    shot,
    *,
    is_character: Callable[[str], bool],
    profile_of: Callable[[str], Mapping[str, Mapping[str, Any]]],
    descriptor_of: Callable[[str], Any] = lambda e: None,
    has_part: Callable[[str], bool],
    record: Callable[[Any], None] | None = None,
    policy: Any = None,
) -> SpeechPlan:
    """Resolve the speech aspect ONCE per speaking character, and say what it adds.

    The request is the character's declared ``speech`` (a method spelling or a
    ``{method, args, version}`` choice); ``policy`` is the shot/style policy.
    The one resolution decides both halves: a speaker resolved to anything but
    ``speech.mouth_chart`` gets no viseme channel (:attr:`SpeechPlan.no_lip_sync`),
    and one resolved to ``speech.pose_only`` gets a ``speech_pulse`` play at each
    syllable onset of each timed line — one play per syllable, each built at the
    head's pose at that instant, so it rides an authored head-scale tween rather
    than overwriting it; a syllable that starts while the speaker's previous pulse
    is still running is skipped, so the head always settles back. ``strength: 0``
    is a mime: no pulse at all. An authored ``play: speech_pulse`` on the speaker
    replaces the automatic pulses (nothing is added beside it), but it is not a
    declaration: the fall from the mouth chart is still recorded, and only a
    declared ``speech`` makes it the request. Substitutions (a declared method
    the rig cannot honour; the fall from the mouth chart to the pulse) go to
    ``record``, once per speaker. A declared ``speech`` naming no method of the
    aspect, or pinned to a stale version, raises
    :class:`~an.semantic.VocabularyError` naming the aspect's methods
    (:func:`speech_problems` is ``an validate``'s side of it).
    """
    from an.ir.compose import delay, sequence
    from cutan.characters.registration import play
    from an.semantic import resolve

    from cutan.motion import WALK_LANDING_S

    authored = _authored_pulse_speakers(shot)
    resolved: dict[str, Any] = {}
    busy_until: dict[str, float] = {}
    actions: list = []
    lines = sorted(
        (ln for ln in shot.dialogue or ()),
        key=lambda ln: float("inf") if ln.start is None else float(ln.start),
    )
    for line in lines:
        speaker = line.speaker
        if not is_character(speaker):
            continue
        if speaker not in resolved:
            requested = getattr(descriptor_of(speaker), "speech", None)
            r = resolve(
                SPEECH,
                profile_of(speaker),
                requested=requested,
                policy=policy,
                entity=speaker,
            )
            resolved[speaker] = r
            if r.substitution is not None and record is not None:
                record(r.substitution)
        r = resolved[speaker]
        if (
            r.method.id != SPEECH_PULSE.id
            or speaker in authored
            or line.start is None
            or line.duration is None
            or not float(r.args.get("strength", 0.0))
        ):
            continue
        args = {k: v for k, v in r.args.items() if k not in ("part", "beats")}
        part = r.args.get("part", "head")
        args["part"] = part if part and has_part(f"{speaker}/{part}") else ""
        length = (
            float(args.get("attack", 0.0))
            + float(args.get("release", 0.0))
            + WALK_LANDING_S
        )
        for beat in syllable_beats(line):
            at = float(line.start) + beat
            # A beat inside a pulse still running (long args, overlapping lines)
            # is dropped: a pulse built on a mid-pulse pose would settle above
            # rest and ratchet the head up (review-256 R2-1).
            if at < busy_until.get(speaker, float("-inf")):
                continue
            busy_until[speaker] = at + length
            pulse = play(speaker, PULSE_PRESET, args={**args, "beats": [0.0]})
            actions.append(sequence(delay(at), pulse) if at else pulse)
    return SpeechPlan(
        tuple(actions),
        frozenset(s for s, r in resolved.items() if r.method.id != SPEECH_CHART.id),
    )
