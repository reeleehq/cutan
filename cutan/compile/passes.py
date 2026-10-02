"""The cut-out passes over the stage compiler, and the helpers only they use.

Moved from ``an.stage.compile`` (an#225). The stage compiler keeps the passes every
genre shares (scene, actions, camera, parallax, checks) and the helpers both sides use;
this module holds what only the cut-out genre reaches: the ``speech``, ``swap_pose``,
``view_spans``, ``visemes`` and ``face`` passes (registered by :data:`cutan.genre.CUTOUT`
as ``"cutan.compile.passes:<name>"``) and the character rig builder.
"""

from __future__ import annotations

from __future__ import annotations

import dataclasses
import math
import warnings
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Callable

from cutan.compile.coarticulate import coarticulate
from cutan.expression.axes import LID_KEY_CLOSED, LID_KEY_OPEN, lid_key
from cutan.expression.binding import (
    LID_SQUASH_GAIN,
    ChannelBinding,
    ExpressionResolutionError,
    SetBinding,
    binding_for,
    expression_problems,
    resolve_mouth_set,
)
from cutan.compile.gaze import gaze_seed, saccade_track
from cutan.expression.presets import mouth_form_of
from cutan.expression.provider import DefaultExpressionProvider, ExpressionProvider
from cutan.characters.play import (
    PRESET_SOURCE,
    BoneTrack,
    PlayResolutionError,
    expand_preset_play,
    play_problems,
    play_source,
    GAIT_ARG,
    PARTS_ARG,
    VIEW_ARG,
    facing_at,
    preset_takes,
    resolve_play,
    resolve_turns,
    sampled_deviations,
    slot_node_path,
)
from an.ir.compose import FlatAction
from cutan.characters.registration import PlayAction
from an.ir.schema import (
    AssetRef,
    SetAction,
    Shot,
    TweenAction,
)

from an.stage.serialize import (
    AnimationClipJSON,
    AssetJSON,
    AssetResolutionJSON,
    ChannelJSON,
    KeyframeJSON,
    NodeJSON,
    PlacedClipJSON,
    TrackJSON,
    TransformJSON,
    VisualJSON,
)
from cutan.characters.schema import (
    CHARACTER_DOCUMENT_KIND,
    VIEW_CHANNEL,
    view_variant_sets,
    EYELID_CHANNEL,
    SLOT_POSE_ANGLES,
    SLOT_POSE_FACTORS,
    SLOT_POSE_OFFSETS,
    MOUTH_SHAPES,
    VISEME_CHANNEL,
    CharacterDescriptor,
)
from an.stage.raster import is_raster
from an.ir.migrate import migrate
from an.stage.text_layout import svg_data_uri
from cutan.characters.colour_roles import recolour_svg, role_recolouring
from an.styles import StylePack, resolve_palette, surface_for
from an.stage.surface import (
    apply_surface,
)

from an.stage.compile import (  # noqa: E402
    CHARACTER_ART_PREFIX,
    CompileState,
    CutoutCompileError,
    CutoutCompileWarning,
    SceneBuild,
    _EntitySwap,
    _PROPERTY_REST_VALUES,
    _StepCurve,
    _SwapVocabulary,
    _apply_stage_placement,
    _build_svg_character_subtree,
    _built_value,
    _note_raster_rig,
    _part_probe,
    _raster_digest,
    _svg_asset_src,
    _track_root_of,
    _value_at,
    _warn_surface,
)


# Default placeholder character: a recognizable stick-figure layout in pixel
# space so the demo is *visible* without art assets. Each entry pins a part to
# a (x, y) offset; colors come from a per-character palette so multiple
# characters look distinct. Used only when the characters store has no rig.
def _provider(state) -> ExpressionProvider:
    """The shot's expression provider: the caller's, else the default."""
    return state.expression_provider or DefaultExpressionProvider()


_PLACEHOLDER_PARTS: tuple[str, ...] = ("head", "torso", "left_arm", "right_arm")


#: Fraction of a limb rect's height, from its top edge, at which the joint sits:
#: ``0.0`` is the shoulder/hip. A part without a ``pivot_y`` rotates about its
#: centre (``0.5``), which is right for a head or a torso and wrong for a limb —
#: a centre-pivoted arm swings its hand up while its top swings down into the
#: torso (an#173). Named so the limb entries below say what they mean.
_LIMB_PIVOT_Y: float = 0.0


_DFLT_PIVOT_Y: float = 0.5


#: ``x``/``y`` are the rect's CENTRE when at rest (the layout); ``pivot_y``, when
#: present, moves the NODE to the joint and hangs the rect from it, so the same
#: pixels are covered at rest and a rotation pivots at the joint.
_PLACEHOLDER_PART_GEOMETRY: dict[str, dict[str, float]] = {
    "head": {"x": 0.0, "y": -55.0, "width": 50.0, "height": 50.0},
    "torso": {"x": 0.0, "y": 0.0, "width": 60.0, "height": 80.0},
    "left_arm": {
        "x": -50.0,
        "y": -10.0,
        "width": 30.0,
        "height": 70.0,
        "pivot_y": _LIMB_PIVOT_Y,
    },
    "right_arm": {
        "x": 50.0,
        "y": -10.0,
        "width": 30.0,
        "height": 70.0,
        "pivot_y": _LIMB_PIVOT_Y,
    },
    "left_leg": {
        "x": -18.0,
        "y": 65.0,
        "width": 30.0,
        "height": 70.0,
        "pivot_y": _LIMB_PIVOT_Y,
    },
    "right_leg": {
        "x": 18.0,
        "y": 65.0,
        "width": 30.0,
        "height": 70.0,
        "pivot_y": _LIMB_PIVOT_Y,
    },
}


# Per-character color palettes. Each entry is (skin, clothing, hair). Picked
# deterministically from the entity.id so re-renders are stable.
_CHARACTER_PALETTES: tuple[tuple[str, str, str], ...] = (
    ("#f4c89a", "#3a6ea5", "#3b2a1a"),  # peach skin, blue clothes, dark hair
    ("#d8a47f", "#a83249", "#1a1a1a"),  # tan skin, red clothes, black hair
    ("#fbe1c1", "#2e7d4f", "#a8743f"),  # pale skin, green clothes, ginger
    ("#a87a5d", "#5b3a8a", "#2a2a2a"),  # darker skin, purple clothes, black
    ("#e8c39e", "#d97706", "#5e3a1f"),  # warm skin, orange clothes, brown
)


#: Roles every character has somewhere (a body is skin, a costume, hair). A
#: TAGGED rig missing one of these that a pack sets is half-reached — a
#: DiceBear head keeps its own skin while the rest follows the pack — and is
#: warned about by role. `leg`, `pupil` and `accessory` are not here: a rig
#: may legitimately have none (no legs, no hat).
_CORE_CHARACTER_ROLES: tuple[str, ...] = ("skin", "hair", "clothing")


def _core_roles_left_untagged(
    entity: AssetRef, desc_data: Mapping[str, Any], pack: "StylePack | None"
) -> list[str]:
    """The core roles ``pack`` sets for ``entity`` that its tagged rig never tags."""
    if pack is None:
        return []
    tagged = {
        role
        for roles in (desc_data.get("colour_roles") or {}).values()
        for role in roles.values()
    }
    return [
        role
        for role in _CORE_CHARACTER_ROLES
        if role not in tagged and pack.colour_for(role, entity=entity.id) is not None
    ]


def _recoloured_texture_srcs(
    entity: AssetRef,
    desc_data: Mapping[str, Any],
    characters_store: Mapping,
    pack: "StylePack | None",
    *,
    art_prefix: str | None = None,
) -> dict[str, str] | None:
    """``{part path: inline src}`` for every role-tagged part ``pack`` recolours.

    ``None`` means the rig is UNREACHABLE — a pack is set and the descriptor
    tags no colours (or its art cannot be read) — and the caller warns. An
    empty dict means reachable but untouched (no pack, or a pack that sets none
    of the rig's roles), which is what keeps a scene without a pack
    byte-identical: nothing is read and nothing is rewritten.

    The recoloured text becomes a ``data:`` texture (the an#155 form), so the
    compiled document is self-contained and its contract hash covers the swap.
    """
    if pack is None:
        return {}
    art_prefix = art_prefix or CHARACTER_ART_PREFIX
    roles_by_part = desc_data.get("colour_roles") or {}
    root = getattr(characters_store, "_root", None)
    if not roles_by_part or root is None:
        return None
    out: dict[str, str] = {}
    for rel_path, roles in roles_by_part.items():
        if is_raster(rel_path):
            # Pixels, not literals: nothing to rewrite (an#211). The caller
            # warns once, by rig, via `_raster_parts`.
            continue
        swaps = role_recolouring(
            roles, lambda role: pack.colour_for(role, entity=entity.id)
        )
        if not swaps:
            continue
        src = _svg_asset_src(entity.ref or entity.id, rel_path, art_prefix=art_prefix)
        path = Path(root) / src[len(art_prefix) :]
        if not path.is_file():
            continue  # a missing part is `_record_missing_parts`' business
        out[rel_path] = svg_data_uri(
            recolour_svg(path.read_text(encoding="utf-8"), swaps)
        )
    return out


#: The procedural rig's leg colour — a literal the palette table never
#: carried, which is why it is a named constant rather than two copies of a
#: string. A `StylePack`'s `leg` role replaces it.
DFLT_LEG_COLOUR: str = "#2c3e50"


#: The procedural rig's pupil colour. `makeEye` reads it from the document —
#: the eye WHITE beside it is a literal and cannot be reached, which is the
#: split `REACHABLE_ROLES` / `UNREACHABLE_ROLES` records.
DFLT_PUPIL_COLOUR: str = "#1a1a1a"


def _palette_for(entity_id: str) -> tuple[str, str, str]:
    """Deterministic (skin, clothing, hair) palette for a given entity id."""
    idx = sum(ord(c) for c in entity_id) % len(_CHARACTER_PALETTES)
    return _CHARACTER_PALETTES[idx]


#: Co-articulation on/off (an#97). ON is the product; OFF reproduces the
#: pre-#97 mouth CHOICE — the raw provider track thinned by the old drop-not-hold
#: condenser — over the new frame-ceiled clip window (so not byte-for-byte the
#: old emission: OFF still closes the mouth after a line) and exists so the `lipsync-coarticulation` demo and a test can
#: render the two side by side. Not a RenderContext knob: nobody should ship
#: the old behaviour, and a module flag rebound for one render is the shape
#: the bench's levers already use.
COARTICULATION_ENABLED: bool = True


#: The pre-#97 minimum gap, kept ONLY for the OFF path above (the ON path's
#: hold is `coarticulate.DEFAULT_MIN_HOLD_S`, the same number until measured).
_LEGACY_MIN_VISEME_GAP_S: float = 0.14


#: The procedural (drawn) mouth's swap vocabulary, DECLARED as data on its
#: visual exactly as the runtime declares it (`g._anDrawSets = {viseme: ...}`)
#: and as an SVG mouth carries its projection. A drawn mouth has no textures,
#: so each key maps to itself — the code the runtime's shape table draws. The
#: compiler never branches on the set's NAME: the drawn mouth is just a node
#: whose visual carries a `viseme` set (an#87).
PROCEDURAL_MOUTH_KEYS: dict[str, str] = {s.upper(): s.upper() for s in MOUTH_SHAPES}


# -- Blinks (an#88): generated by the COMPILER, as ordinary channels ---------
#
# These were a runtime-only pass (`applyProceduralBlinks`) that matched eye
# nodes by regex and forced `scale.y` AFTER the pose every frame — which is why
# an authored eye `scale_y` could never reach the screen. They are channels
# now, on the entity's track ahead of everything authored, so later-wins
# evaluation lets an author override a blink like any other motion.
#
# The schedule keeps the runtime's exact rule — period, duration, depth, and
# the phase as a pure function of the entity NAME (stamped into the compiled
# scene's meta, because renaming a corpus character re-phases every blink and
# moves every pixel metric; that hazard is recorded, not fixed).
_BLINK_PERIOD_S: float = 4.0


_BLINK_DURATION_S: float = 0.14


_BLINK_DEPTH: float = 0.95


#: The nodes that blink, by name: the default rig's eye slots ARE its node
#: names, on both the procedural and the descriptor path.
EYE_NODE_NAMES: frozenset[str] = frozenset({"left_eye", "right_eye"})


#: The pupil nodes of the gaze stack (an#99); a rig without them takes gaze as a no-op.
PUPIL_NODE_NAMES: frozenset[str] = frozenset({"left_pupil", "right_pupil"})


#: The summed gaze (x, y), in axis units, is clamped to a circle of this radius
#: — the declared travel maps the unit circle onto the sclera's inner ellipse,
#: and 0.95 keeps the whole pupil disc inside it at every angle (measured on
#: the synthesized eye: 1.0 pokes out by 2% of the ellipse at the diagonal).
GAZE_ELLIPSE_MARGIN: float = 0.95


#: Within a blink window, the eyelid swap shows CLOSED for the central half —
#: the span where the squash curve sits above 0.7 of full closure.
_EYELID_CLOSED_SPAN: tuple[float, float] = (0.25, 0.75)


def _js_string_hash(s: str) -> int:
    """Port of the runtime's ``_strHash`` — JS int32 ``(h << 5) - h + code``.

    >>> _js_string_hash("charlie") % 1000
    762
    """
    # JS iterates UTF-16 code units (`charCodeAt`), not code points: a
    # non-BMP character is two units. Encode the same way so the port stays
    # bit-identical for every entity id, not only ASCII/BMP ones.
    units = s.encode("utf-16-le")
    h = 0
    for i in range(0, len(units), 2):
        h = ((h << 5) - h) + int.from_bytes(units[i : i + 2], "little")
        h &= 0xFFFFFFFF
        if h >= 0x80000000:
            h -= 0x100000000
    return abs(h)


def blink_phase(entity_id: str) -> float:
    """The entity's blink phase in [0, 1): the runtime's rule, ported exactly.

    >>> blink_phase("charlie")
    0.762
    """
    return (_js_string_hash(entity_id) % 1000) / 1000.0


def _blink_windows(entity_id: str, duration: float) -> list[tuple[float, float]]:
    """``[(start, end), ...]`` of every blink overlapping ``[0, duration]``.

    The runtime blinked when ``(t + phase * P) % P < D``, i.e. at
    ``t = k*P - phase*P + [0, D)``.
    """
    offset = blink_phase(entity_id) * _BLINK_PERIOD_S
    out = []
    k = 0
    while True:
        start = k * _BLINK_PERIOD_S - offset
        end = start + _BLINK_DURATION_S
        if start > duration:
            break
        if end > 0.0:
            out.append((start, end))
        k += 1
    return out


def _speech_pass(state: CompileState) -> None:
    """Cut-out: the speech aspect, resolved once per speaker (an#248) -- the
    pulses it adds for a speaker that does not lip-sync (compiled with the
    authored actions), and those speakers, whose lip-sync the viseme pass skips."""
    speech = _speech_plan(state.shot, state.vocab, state.resolutions)
    state.extra_actions.extend(speech.actions)
    state.no_lip_sync = speech.no_lip_sync


def _swap_pose_pass(state: CompileState) -> None:
    """Cut-out: what each whole-character swap POSES (an#197) -- folded into the
    face solver's channels, so a posed pupil still follows the gaze."""
    state.poses = _swap_pose_layer(state.entity_swaps, state.vocab)


def _view_span_pass(state: CompileState) -> None:
    """Cut-out: which view each character with per-view face sets is in, and
    when (an#220): the mouth and lids draw from `viseme@side` while the profile shows."""
    state.view_spans = _view_spans(
        state.entity_swaps, state.vocab, duration=state.shot.duration
    )


def _viseme_pass(state: CompileState) -> None:
    """Cut-out: a viseme channel per dialogue line that has a viseme track (Phase 4)."""
    _add_viseme_clips(
        state.shot,
        state.animations,
        state.tracks,
        mall=state.mall,
        vocab=state.vocab,
        fps=state.fps,
        provider=_provider(state),
        view_spans=state.view_spans,
        no_lip_sync=state.no_lip_sync,
    )


def _face_pass(state: CompileState) -> None:
    """Cut-out: the face (an#98) -- blinks, expressions, gaze and the silent mouth
    form; one channel per (node, property). An entity nothing expresses on gets
    its blink clips exactly as before (an#88)."""
    state.blink_phases, state.gaze_seeds = _add_face_clips(
        state.shot,
        state.animations,
        state.tracks,
        vocab=state.vocab,
        fps=state.fps,
        mall=state.mall,
        provider=_provider(state),
        poses=state.poses,
        view_spans=state.view_spans,
    )


def _build_character_entity(entity: AssetRef, build: SceneBuild) -> None:
    """Cut-out (the ``rig`` pass): a character, spread along x among the shot's
    characters so they don't overlap (a single one at the centre)."""
    cast = [e for e in build.shot.entities if e.kind == entity.kind]
    x = _layout_character_positions(len(cast))[
        next(i for i, e in enumerate(cast) if e is entity)
    ]
    sub = _build_character_subtree(
        entity,
        build.store("characters"),
        textures=build.textures,
        resolutions=build.resolutions,
        style_pack=build.style_pack,
        reached=build.reached,
        skipped=build.skipped,
        raster=build.raster,
    )
    sub.transform.x = x
    _apply_stage_placement(sub, entity)
    # an#163: outline / paper-gap shadow / glow, when the pack asks.
    _warn_surface(
        apply_surface(
            sub, surface_for(build.style_pack, entity.id), textures=build.textures
        )
    )
    build.children.append(sub)


def _layout_character_positions(n: int, *, spread: float = 220.0) -> list[float]:
    """Return ``n`` x-positions evenly distributed about 0.

    >>> _layout_character_positions(0)
    []
    >>> _layout_character_positions(1)
    [0.0]
    >>> _layout_character_positions(2, spread=200.0)
    [-100.0, 100.0]
    """
    if n <= 0:
        return []
    if n == 1:
        return [0.0]
    step = spread / (n - 1)
    return [-spread / 2 + i * step for i in range(n)]


def _build_character_subtree(
    entity: AssetRef,
    characters_store: Mapping,
    *,
    textures: dict[str, AssetJSON] | None = None,
    resolutions: list[AssetResolutionJSON] | None = None,
    style_pack: "StylePack | None" = None,
    reached: set[str] | None = None,
    skipped: set[str] | None = None,
    raster: set[str] | None = None,
) -> NodeJSON:
    """Build a NodeJSON subtree for one character.

    Phase 11b: if the characters store has a Phase-11a CharacterDescriptor
    for this entity (``kind == "CharacterDescriptor"``), build the SVG
    rig and populate the ``textures`` accumulator. Otherwise fall back to
    the procedural rig so legacy / asset-less characters keep rendering.

    That fallback is deliberate and stays — an asset-less project must render
    — but it is no longer *silent*: what happened is appended to
    ``resolutions`` so the compiled scene carries which rig was actually built
    (an#33).
    """
    char_meta: dict[str, Any] = {}
    in_store = entity.ref in characters_store
    if in_store:
        try:
            value = characters_store[entity.ref]
            if isinstance(value, dict):
                char_meta = value
        except KeyError:
            char_meta = {}
            in_store = False

    def _record(resolved: str, *, fallback: bool = False, detail: str = "") -> None:
        if resolutions is None:
            return
        resolutions.append(
            AssetResolutionJSON(
                id=entity.id,
                kind="character",
                store=entity.store,
                ref=entity.ref,
                resolved=resolved,
                fallback=fallback,
                detail=detail,
            )
        )

    if char_meta.get("kind") == "CharacterDescriptor":
        _record("descriptor")
        _note_raster_rig(entity, char_meta, style_pack, raster)
        # An SVG rig's colours live inside its drawings. A pack reaches the
        # ones the descriptor TAGS (`colour_roles`); an untagged rig is
        # recorded so the compiler can say which it could not reach, by name.
        srcs = _recoloured_texture_srcs(entity, char_meta, characters_store, style_pack)
        if srcs is None:
            if skipped is not None:
                skipped.add(entity.id)
        else:
            if srcs and reached is not None:
                reached.add(entity.id)
            untagged = _core_roles_left_untagged(entity, char_meta, style_pack)
            if untagged and skipped is not None:
                skipped.add(f"{entity.id} ({', '.join(untagged)})")
        return _build_svg_character_subtree(
            entity,
            char_meta,
            textures=textures if textures is not None else {},
            probe=_part_probe(characters_store),
            resolutions=resolutions,
            texture_srcs=srcs or None,
            digest=_raster_digest(characters_store),
            descriptor_model=CharacterDescriptor,
            document_kind=CHARACTER_DOCUMENT_KIND,
        )

    declared_parts = char_meta.get("parts")
    if declared_parts:
        _record("parts")
    elif in_store:
        _record(
            "placeholder",
            fallback=True,
            detail=(
                f"character ref {entity.ref!r} IS in the {entity.store!r} store, "
                "but the entry is neither a CharacterDescriptor nor a rig with "
                "'parts', so the built-in placeholder rig was drawn instead"
            ),
        )
    else:
        _record(
            "placeholder",
            fallback=True,
            detail=(
                f"character ref {entity.ref!r} is not in the {entity.store!r} "
                "store, so the built-in placeholder rig was drawn instead of "
                "the character the scene names"
            ),
        )

    parts = declared_parts or _PLACEHOLDER_PARTS
    # A LOOKUP WITH A DEFAULT, not a rewrite: with no pack — every document
    # before an#112 — the literals below come back unchanged and the compiled
    # node is the node this code always produced.
    skin, clothing, hair = resolve_palette(
        style_pack, entity.id, _palette_for(entity.id)
    )
    leg = (
        style_pack.colour_for("leg", entity=entity.id) if style_pack else None
    ) or DFLT_LEG_COLOUR
    if style_pack is not None and reached is not None:
        reached.add(entity.id)
    # Per-part color: head/limbs are skin colour, torso/arm-clothing is the
    # clothing colour.
    part_color: dict[str, str] = {
        "head": skin,
        "torso": clothing,
        "left_arm": clothing,
        "right_arm": clothing,
        "left_leg": leg,
        "right_leg": leg,
    }
    children: list[NodeJSON] = []
    for part in parts:
        geom = _PLACEHOLDER_PART_GEOMETRY.get(
            part, {"x": 0.0, "y": 0.0, "width": 50.0, "height": 50.0}
        )
        # Head renders as a fleshier ellipse; everything else stays a rect.
        kind = "ellipse" if part == "head" else "rect"
        # The node sits at the joint, the rect hangs from it (an#173).
        pivot_y = float(geom.get("pivot_y", _DFLT_PIVOT_Y))
        node_y = float(geom["y"]) - float(geom["height"]) * (_DFLT_PIVOT_Y - pivot_y)
        children.append(
            NodeJSON(
                name=part,
                transform=TransformJSON(x=float(geom["x"]), y=node_y),
                visual=VisualJSON(
                    kind=kind,
                    width=float(geom["width"]),
                    height=float(geom["height"]),
                    anchor_y=pivot_y,
                    color=part_color.get(part, "#cccccc"),
                ),
            )
        )
    char_node = NodeJSON(
        name=entity.id,
        transform=TransformJSON(),
        children=children,
    )
    if "head" in parts:
        # Head children: hair on top, eyebrows above eyes, two eyes (white +
        # pupil drawn together by the runtime when kind="eye"), mouth (viseme
        # target — runtime draws curved lips per viseme code).
        for child in char_node.children:
            if child.name != "head":
                continue
            # Hair: rounded band atop the head.
            child.children.append(
                NodeJSON(
                    name="hair",
                    transform=TransformJSON(x=0.0, y=-20.0),
                    visual=VisualJSON(
                        kind="ellipse", width=46.0, height=18.0, color=hair
                    ),
                )
            )
            # Eyebrows: small dark rects above each eye; rotation = expression.
            for brow_name, bx in (("left_brow", -10.0), ("right_brow", 10.0)):
                child.children.append(
                    NodeJSON(
                        name=brow_name,
                        transform=TransformJSON(x=bx, y=-10.0),
                        visual=VisualJSON(
                            kind="rect",
                            width=10.0,
                            height=2.5,
                            color=hair,
                        ),
                    )
                )
            # Eyes: white sclera + dark pupil drawn together by makeEye, which
            # reads `visualSpec.color` for the PUPIL — so a pack reaches it,
            # while the white is a `runtime.js` literal and cannot be reached
            # (`an.styles.UNREACHABLE_ROLES`).
            pupil = (
                style_pack.colour_for("pupil", entity=entity.id) if style_pack else None
            ) or DFLT_PUPIL_COLOUR
            for eye_name, ex in (("left_eye", -10.0), ("right_eye", 10.0)):
                child.children.append(
                    NodeJSON(
                        name=eye_name,
                        transform=TransformJSON(x=ex, y=-3.0),
                        visual=VisualJSON(
                            kind="eye", width=10.0, height=8.0, color=pupil
                        ),
                    )
                )
            # Mouth (viseme target).
            child.children.append(
                NodeJSON(
                    name="mouth",
                    transform=TransformJSON(x=0.0, y=14.0),
                    visual=VisualJSON(
                        kind="mouth",
                        width=22.0,
                        height=4.0,
                        color="#552222",
                        asset_sets={VISEME_CHANNEL: dict(PROCEDURAL_MOUTH_KEYS)},
                    ),
                )
            )
    return char_node


def _pose_step_channels(
    pose: Mapping[tuple[str, str], _StepCurve],
    *,
    skip: set[tuple[str, str]] = frozenset(),
) -> list[ChannelJSON]:
    """The pose's curves as held step channels, keyed where each swap lands."""
    return [
        ChannelJSON(
            target=path,
            property=prop,
            keyframes=[KeyframeJSON(time=t, value=v, easing="step") for t, v in curve],
        )
        for (path, prop), curve in sorted(pose.items())
        if (path, prop) not in skip
    ]


def _step_at(curve: _StepCurve, t: float) -> float:
    """The value a step curve holds at ``t`` (a key applies from its own time,
    within float slack, like the evaluators' time-based snap)."""
    value = curve[0][1]
    for time, v in curve:
        if time <= t + 1e-9:
            value = v
        else:
            break
    return value


#: A per-view face clip ends this long before the next view's span begins, so
#: at the instant of the swap only the NEW view's clip is playing — two swap
#: sets playing at one instant on one sprite resolve by name, not by time.
_VIEW_SPAN_EDGE_S: float = 1e-6


def _speech_plan(
    shot: Shot,
    vocab: _SwapVocabulary,
    resolutions: list[AssetResolutionJSON] | None,
):
    """The speech aspect's plan for the shot (an#248): the pulses a speaker that
    does not lip-sync gets, and who those speakers are. A shot whose speakers
    all lip-sync on their mouth chart gets nothing — its document is unchanged."""
    from cutan.characters.methods import speech_plan
    from an.semantic import VocabularyError

    try:
        return speech_plan(
            shot,
            is_character=lambda e: _on_registry(e, vocab),
            profile_of=lambda e: _character_profile(e, vocab),
            descriptor_of=lambda e: vocab.descriptors.get(e),
            has_part=lambda path: path in vocab.node_transforms,
            record=lambda sub: _record_substitution(sub, resolutions),
        )
    except VocabularyError as e:
        raise CutoutCompileError(
            f"shot {shot.id!r}: a character's declared `speech` cannot be honoured: {e}"
        ) from e


def _baked_face_speakers(shot: Shot, mall: Mapping[str, Mapping] | None) -> set[str]:
    """Return the entity ids whose backing descriptor declares a baked face.

    Used to suppress viseme channels for characters that don't have an
    overlay mouth node (DiceBear / external avatars). See
    ``_build_svg_character_subtree`` for the matching scene-tree branch.

    Reads the **migrated, validated** descriptor's declared ``face_overlay``
    fact — the predecessor read the RAW store dict's ``art_provenance`` with
    no ``kind`` guard, so (a) a migration-seeded field was invisible to it,
    and (b) a legacy ``parts``-rig carrying ``art_provenance="dicebear"`` got
    a full procedural mouth built and its viseme channel suppressed — a drawn
    mouth that never moved, silently. Only descriptor-backed entities can
    declare a baked face now; the two consumer sites read one model.
    """
    if not mall:
        return set()
    chars_store = mall.get("characters") or {}
    out: set[str] = set()
    for entity in shot.entities:
        if entity.kind != "character":
            continue
        ref = entity.ref
        if ref is None or ref not in chars_store:
            continue
        try:
            desc_data = chars_store[ref]
        except KeyError:
            continue
        if (
            not isinstance(desc_data, dict)
            or desc_data.get("kind") != "CharacterDescriptor"
        ):
            continue
        desc = CharacterDescriptor.model_validate(
            migrate(dict(desc_data), kind=CHARACTER_DOCUMENT_KIND.name)
        )
        if not desc.face_overlay:
            out.add(entity.id)
    return out


def _add_viseme_clips(
    shot: Shot,
    animations: dict[str, AnimationClipJSON],
    tracks: list[TrackJSON],
    *,
    mall: Mapping[str, Mapping] | None = None,
    vocab: _SwapVocabulary | None = None,
    fps: int = 30,
    provider: ExpressionProvider | None = None,
    view_spans: Mapping[str, list[_ViewSpan]] | None = None,
    no_lip_sync: frozenset[str] = frozenset(),
) -> None:
    """For each dialogue line with a viseme_track, emit a step swap channel on
    every node of the speaker that can apply the line's mouth set.

    ``no_lip_sync`` are the speakers whose speech aspect did not resolve to
    the mouth chart (an#248: one decision, the capability registry's); they
    get no viseme channel.

    **The view picks first** (an#220): a line that starts while the speaker
    is in a view it declares a mouth for (``viseme@side``, per
    ``view_spans``) speaks on that set, whatever the expression — a profile's
    mouth is the profile's. A view set lacking a key the line uses falls back
    to the chain below, with a warning.

    The mouth SET is selected per line (an#98): the expression in force at the
    line's start prefers a ``viseme@<form>`` variant, and
    :func:`cutan.expression.binding.resolve_mouth_set` — shared with ``an
    validate`` — decides whether the character can honour it (declared and
    covering the line's keys), falls back to ``viseme`` with a warning, or
    raises. Whole-line, so at most one mouth swap property is live per instant.

    The provider's raw track goes through the co-articulation passes first
    (`cutan.compile.coarticulate`, an#97): duplicates merged, sub-frame
    tongue shapes dropped, every shape led by two frames, a decay before rest,
    and a minimum hold that HOLDS AND VOTES. The old condenser here dropped
    every key inside its 0.14 s window, so a consonant cluster collapsed to
    whichever shape arrived first (epic #9 defect 5b). ``fps`` is what "one
    frame" means to the symbolic pass.

    Side-effects ``animations`` (adds named clips) and ``tracks`` (appends to
    or creates the speaker's track).

    The target is discovered from the BUILT scene, not a path literal (an#87):
    a node applies ``viseme`` when its visual carries the set's projection (an
    SVG mouth) or is the procedural drawn mouth. The old
    ``f"{speaker}/head/mouth"`` literal was the last place the compiler
    hardcoded where a mouth lives.

    Two kinds of speaker get no viseme channel, for the same reason: there is no
    mouth node for it to target.

    - Speakers whose descriptor declares ``face_overlay=False`` (DiceBear /
      external avatars) — the face is drawn into the head SVG, so there is no
      overlay mouth.
    - **Speakers with no viseme-capable node in the built scene.** One
      condition, two cases that are indistinguishable from here: the
      off-screen-narrator idiom (a speaker deliberately not an entity — the
      standing workaround while ``Shot.narration`` is unimplemented), and a
      character who IS on screen but whose rig has no mouth, which an
      entity-membership check misses and sends to a hard render failure.

    The second kind WARNS rather than passing in silence, because it cannot be
    told apart from a typo: ``speaker="charlei"`` against an on-screen
    ``charlie`` otherwise loses its lip-sync quietly while the audio still
    plays. Naming the scene's actual mouths makes the typo obvious.

    Codes are upper-cased at EMISSION (the Rhubarb convention) — case used to
    be normalised in the runtime's sprite path only, so a lowercase ``'a'``
    swapped correctly on an SVG rig and silently drew rest on a procedural
    one. And a code the target cannot show is DROPPED here with a warning,
    never carried into the scene: the runtime now throws on an unknown swap
    key (the loud half of an#87), so compiled scenes must be total.
    """
    face_baked = _baked_face_speakers(shot, mall)
    track_lookup: dict[str, TrackJSON] = {t.target_root: t for t in tracks}
    # Emit in TIME order, keeping each line's authored index for its ids: the
    # frame-ceiled window of one line can overlap the next line's first frame
    # on the same track, and the runtime resolves that by clip order (later
    # wins) — so a dialogue list authored out of order would show line 1's
    # rest over line 2's opening shape for one frame (an#97 review). In-order
    # lists are emitted exactly as before.
    ordered = sorted(
        enumerate(shot.dialogue),
        key=lambda p: (p[1].start if p[1].start is not None else math.inf, p[0]),
    )
    for i, line in ordered:
        if line.viseme_track is None or not line.viseme_track.keyframes:
            continue
        if line.start is None or line.duration is None:
            # No timing assigned (audio pipeline didn't run); skip silently.
            continue
        speaker = line.speaker
        if speaker in face_baked or speaker in no_lip_sync:
            continue
        set_name = VISEME_CHANNEL
        desc = vocab.descriptors.get(speaker) if vocab is not None else None
        line_spans = (view_spans or {}).get(speaker)
        view_set = _line_view_set(vocab, speaker, line, spans=line_spans, index=i)
        if (
            desc is not None
            and provider is not None
            and hasattr(provider, "mouth_preset_at")
        ):
            preset = provider.mouth_preset_at(shot, speaker, float(line.start))
            if preset is not None:
                keys_used = {
                    str(kf.viseme).upper() for kf in line.viseme_track.keyframes
                }
                # The terminal rest is a key the line USES (appended below), so
                # a variant without it must not be selected (an#98 review).
                keys_used |= {
                    r
                    for p in vocab.swap_capable_paths(speaker, VISEME_CHANNEL)
                    if (r := _mouth_rest_key(vocab, p, VISEME_CHANNEL)) is not None
                }
                try:
                    set_name = resolve_mouth_set(
                        desc, preset, keys_used=keys_used, who=speaker
                    )
                except ExpressionResolutionError as e:
                    raise CutoutCompileError(str(e)) from e
                if set_name != VISEME_CHANNEL:
                    # Declared is not resolved: a variant key whose art is
                    # missing on disk is dropped from the node's projection,
                    # and a line that then holds its previous shape through
                    # the missing key is worse than the neutral set.
                    for p in vocab.swap_capable_paths(speaker, set_name):
                        resolved = set(vocab.node_sets[p].get(set_name) or {})
                        missing = sorted(keys_used - resolved)
                        if missing:
                            warnings.warn(
                                f"shot {shot.id!r} dialogue line {i}: {set_name!r} on "
                                f"{p!r} resolved without {missing} (art missing on "
                                f"disk); the neutral {VISEME_CHANNEL!r} set is used instead.",
                                CutoutCompileWarning,
                                stacklevel=2,
                            )
                            set_name = VISEME_CHANNEL
                            break
        # The expression's set; a line that starts in a view with its own mouth
        # speaks on that instead (an#220), and returns to this one if the
        # speaker turns to a view without one mid-line.
        plain_set = set_name
        if view_set is not None:
            set_name = view_set
        mouth_paths = (
            vocab.swap_capable_paths(speaker, set_name) if vocab is not None else []
        )
        if not mouth_paths:
            if vocab is None:
                continue
            all_mouths = sorted(
                p for p, sets in vocab.node_sets.items() if VISEME_CHANNEL in sets
            )
            warnings.warn(
                f"shot {shot.id!r} dialogue line {i} is spoken by {speaker!r}, "
                "which has no viseme-capable mouth node in the scene: it gets "
                "audio but no lip-sync. Expected for an off-screen narrator. "
                f"If it was not, the scene's mouths are: {all_mouths or 'none'}.",
                CutoutCompileWarning,
                stacklevel=2,
            )
            continue

        raw = [
            (float(kf.time), str(kf.viseme).upper())
            for kf in line.viseme_track.keyframes
        ]
        condensed: list[tuple[float, str]]
        if COARTICULATION_ENABLED:
            # Where the last word ends, when the line knows its words: the
            # mouth rests there, not at the clip's end (an#213) — a TTS clip
            # can carry a second of silence after the last word.
            speech_end = (
                max(float(w.end) for w in line.word_timings)
                if line.word_timings
                else None
            )
            # A word-timed track ends on ITS rest code (`word_timings_to_visemes`
            # always does), which need not be Rhubarb's 'X' (an#213 review).
            rest_kw = {"rest": raw[-1][1]} if speech_end is not None else {}
            condensed = [
                (c.time, c.code)
                for c in coarticulate(
                    raw,
                    fps=fps,
                    end=float(line.duration),
                    speech_end=speech_end,
                    **rest_kw,
                )
            ]
        else:
            # The pre-#97 condenser, verbatim: a key inside the window is
            # DROPPED, so the shape that arrived first owns the window.
            condensed = []
            for t, v in raw:
                if condensed and (t - condensed[-1][0]) < _LEGACY_MIN_VISEME_GAP_S:
                    continue
                condensed.append((t, v))

        for target in mouth_paths:
            mapped = set(vocab.node_sets[target][set_name])
            rest = _mouth_rest_key(vocab, target, set_name)
            usable = [(t, v) for t, v in condensed if v in mapped]
            dropped = sorted({v for _, v in condensed} - mapped)
            if dropped:
                warnings.warn(
                    f"shot {shot.id!r} dialogue line {i}: viseme code(s) "
                    f"{dropped} have no resolved art on {target!r} (it has: "
                    f"{sorted(mapped)}); those keyframes were dropped, so the "
                    "mouth holds its previous shape through them.",
                    CutoutCompileWarning,
                    stacklevel=2,
                )
            if rest is None:
                warnings.warn(
                    f"shot {shot.id!r} dialogue line {i}: {target!r} has no "
                    "rest key in its viseme set (no key maps to the node's "
                    "default attachment, and there is no 'X'), so no viseme "
                    "channel was emitted for it — a mouth that cannot close "
                    "should not start talking.",
                    CutoutCompileWarning,
                    stacklevel=2,
                )
                continue
            kfs: list[KeyframeJSON] = [
                KeyframeJSON(time=max(0.0, t), value=v, easing="step")
                for t, v in usable
                if t < line.duration
            ]
            # The rest key is an INVARIANT, not a conditionally-appended
            # keyframe: a raw keyframe landing at (or clamping to) exactly
            # line.duration used to suppress the append, freezing the mouth
            # in its last viseme forever after the line. And it is DERIVED
            # (the key whose art is the node's default attachment), not the
            # literal 'X' — a set keyed by MPEG-4 numbers or Azure names
            # closes its mouth too.
            kfs.append(KeyframeJSON(time=line.duration, value=rest, easing="step"))

            # The clip WINDOW ends on the first frame at or after the line's
            # end, not at the line's end itself: a terminal rest at 0.71 s is
            # never sampled when frame 17 is 0.708 s and frame 18 (0.75 s) lies
            # outside a 0.71 s window — the runtime then keeps whatever shape
            # frame 17 showed, and the mouth stays open after the line. Seen on
            # `single_character`'s f0024 golden (an#97); blink clips already
            # frame-ceil their windows for the same reason.
            window = math.ceil(float(line.duration) * fps - 1e-9) / fps
            anim_id = f"__viseme__{shot.id}_{i}_{target.replace('/', '.')}"
            track = track_lookup.get(speaker)
            if track is None:
                track = TrackJSON(target_root=speaker, clips=[])
                tracks.append(track)
                track_lookup[speaker] = track
            segments = _line_view_segments(
                vocab,
                speaker,
                target,
                line_spans,
                start=float(line.start),
                end=float(line.start) + max(window, float(line.duration)),
                first=set_name,
                plain=plain_set,
                keys={kf.value for kf in kfs},
            )
            if len(segments) > 1:
                for j, (a, b, seg_set) in enumerate(segments):
                    seg_keys = set(vocab.node_sets[target].get(seg_set) or {})
                    before = [kf for kf in kfs if kf.time <= a + 1e-9]
                    opening = before[-1].value if before else kfs[0].value
                    seg_kfs = [KeyframeJSON(time=0.0, value=opening, easing="step")] + [
                        KeyframeJSON(time=kf.time - a, value=kf.value, easing="step")
                        for kf in kfs
                        if a + 1e-9 < kf.time <= b + 1e-9 and kf.value in seg_keys
                    ]
                    seg_id = f"{anim_id}_{j}"
                    animations[seg_id] = AnimationClipJSON(
                        name=seg_id,
                        duration=max(0.001, b - a),
                        channels=[
                            ChannelJSON(
                                target=target, property=seg_set, keyframes=seg_kfs
                            )
                        ],
                    )
                    track.clips.append(
                        PlacedClipJSON(
                            animation_id=seg_id,
                            start_time=float(line.start) + a,
                            duration=max(0.001, b - a),
                        )
                    )
                continue
            animations[anim_id] = AnimationClipJSON(
                name=anim_id,
                duration=max(window, float(line.duration)),
                channels=[
                    ChannelJSON(target=target, property=set_name, keyframes=kfs),
                ],
            )
            track.clips.append(
                PlacedClipJSON(
                    animation_id=anim_id,
                    start_time=float(line.start),
                    duration=max(window, float(line.duration)),
                )
            )


def _line_view_segments(
    vocab: _SwapVocabulary,
    speaker: str,
    target: str,
    spans: list[_ViewSpan] | None,
    *,
    start: float,
    end: float,
    first: str,
    plain: str,
    keys: set[str],
) -> list[tuple[float, float, str]]:
    """``[(start, end, set)]`` relative to the line's start: the mouth set the
    line speaks on over each view it passes through (an#220). The first is the
    set chosen at the line's start; a later view speaks on its own mouth when
    it has one covering every key the line uses, else on ``plain`` (the
    expression's set). One segment when the line never changes view — the
    line's single clip, exactly as before. Every segment but the last ends
    :data:`_VIEW_SPAN_EDGE_S` before the next, so two mouth sets never play
    at one instant."""
    out: list[tuple[float, float, str]] = []
    for a, b, view in spans or ():
        lo, hi = max(a, start), min(b, end)
        if hi <= lo + 1e-9:
            continue  # the span ends before the line starts, or starts after it
        if out:
            set_name = _face_set_for(vocab, speaker, target, VISEME_CHANNEL, view)
            covered = keys <= set(vocab.node_sets.get(target, {}).get(set_name) or {})
            if set_name == VISEME_CHANNEL or not covered:
                set_name = plain
        else:
            set_name = first
        if out and out[-1][2] == set_name:
            out[-1] = (out[-1][0], hi - start, set_name)
        else:
            out.append((lo - start, hi - start, set_name))
    if not out:
        return [(0.0, end - start, first)]
    out[-1] = (out[-1][0], end - start, out[-1][2])
    return [
        (a, b if j == len(out) - 1 else b - _VIEW_SPAN_EDGE_S, set_name)
        for j, (a, b, set_name) in enumerate(out)
    ]


def _line_view_set(
    vocab: _SwapVocabulary | None,
    speaker: str,
    line: Any,
    *,
    spans: list[_ViewSpan] | None,
    index: int,
) -> str | None:
    """The per-view mouth set a line speaks on (``viseme@side``, an#220), or
    ``None`` when the speaker's view at the line's start has none — or the
    view's set lacks a key the line uses (then with a warning: the front
    mouth in a profile is visible, and should be said)."""
    if vocab is None or not spans:
        return None
    view = _view_at(spans, float(line.start))
    paths = vocab.swap_capable_paths(speaker, VISEME_CHANNEL)
    chosen = {_face_set_for(vocab, speaker, p, VISEME_CHANNEL, view) for p in paths}
    chosen.discard(VISEME_CHANNEL)
    if len(chosen) != 1:
        return None
    (set_name,) = chosen
    keys_used = {str(kf.viseme).upper() for kf in line.viseme_track.keyframes}
    for p in vocab.swap_capable_paths(speaker, set_name):
        missing = sorted(keys_used - set(vocab.node_sets[p][set_name]))
        if missing:
            warnings.warn(
                f"dialogue line {index} of {speaker!r} starts in the {view!r} view, "
                f"but {set_name!r} on {p!r} lacks {missing}; the line speaks on the "
                f"{VISEME_CHANNEL!r} set instead (draw the missing {view} shapes).",
                CutoutCompileWarning,
                stacklevel=3,
            )
            return None
    return set_name


def _mouth_rest_key(
    vocab: _SwapVocabulary, target: str, set_name: str, *, base: str = VISEME_CHANNEL
) -> str | None:
    """The rest key of a mouth set on ``target``: derived from the node's default
    attachment for the neutral set; a variant (``viseme@<form>``, an#98;
    ``viseme@side`` or ``eyelid@side``, an#220 — ``base`` names the set it
    varies) rests on the same KEY the neutral set rests on (its art is the
    variant's), or on ``X``.
    """
    rest = vocab.rest_key(target, set_name)
    if rest is not None:
        return rest
    if set_name != base:
        neutral_rest = vocab.rest_key(target, base)
        keys = vocab.node_sets.get(target, {}).get(set_name) or {}
        if neutral_rest in keys:
            return neutral_rest
        if "X" in keys:
            return "X"
    return None


def _eye_paths(vocab: _SwapVocabulary, entity_id: str) -> list[str]:
    return sorted(
        p
        for p in vocab.paths
        if p.split("/", 1)[0] == entity_id and p.rsplit("/", 1)[-1] in EYE_NODE_NAMES
    )


def _blink_placements(
    shot: Shot,
    entity_id: str,
    animations: dict[str, AnimationClipJSON],
    *,
    vocab: _SwapVocabulary,
    fps: int,
) -> list[PlacedClipJSON] | None:
    """The an#88 blink clips of one entity, VERBATIM — ``None`` when it has no
    eye node (nothing blinks), else the placements (possibly empty). The body of
    the an#88 emitter (`_add_blink_clips`, retired in an#98), so the face solver
    can hand an entity nothing expresses on exactly the clips it always had: same ids, same exact-time
    keyframes, so every corpus scene's contract hash is unchanged (an#98)."""
    eyes = _eye_paths(vocab, entity_id)
    if not eyes:
        return None
    windows = _blink_windows(entity_id, shot.duration)
    placed: list[PlacedClipJSON] = []
    if True:  # indentation kept for a byte-for-byte move of the body below
        for path in eyes:
            eyelid = vocab.node_sets.get(path, {}).get(EYELID_CHANNEL) or {}
            has_art = "OPEN" in eyelid and "CLOSED" in eyelid
            rest = vocab.rest_key(path, EYELID_CHANNEL) if has_art else None
            if has_art and rest not in (None, "OPEN"):
                continue  # rests closed: the author's call, not a blink's
            use_swap = has_art and rest == "OPEN"
            for start, end in windows:
                clip_start = max(0.0, start)
                # Extend to the first rendered frame at/after the window end
                # (capped at the shot), so the rest keyframe is APPLIED.
                clip_end = min(shot.duration, math.ceil(end * fps - 1e-9) / fps)
                if clip_end <= clip_start:
                    continue
                span = end - start
                if use_swap:
                    lo, hi = _EYELID_CLOSED_SPAN
                    t_closed, t_open = start + lo * span, start + hi * span
                    initial = "CLOSED" if t_closed <= clip_start < t_open else "OPEN"
                    kfs = [KeyframeJSON(time=0.0, value=initial, easing="step")]
                    for time, key in ((t_closed, "CLOSED"), (t_open, "OPEN")):
                        if clip_start < time <= clip_end:
                            kfs.append(
                                KeyframeJSON(
                                    time=time - clip_start, value=key, easing="step"
                                )
                            )
                    prop = EYELID_CHANNEL
                else:

                    def squash(time: float) -> float:
                        u = (time - start) / span
                        if u <= 0.0 or u >= 1.0:
                            return 1.0
                        return 1.0 - _BLINK_DEPTH * math.sin(u * math.pi)

                    first_f = math.ceil(clip_start * fps - 1e-9)
                    last_f = math.floor(clip_end * fps + 1e-9)
                    times = sorted(
                        {clip_start, clip_end}
                        | {f / fps for f in range(first_f, last_f + 1)}
                    )
                    kfs = [
                        KeyframeJSON(
                            time=time - clip_start, value=squash(time), easing="linear"
                        )
                        for time in times
                        if clip_start <= time <= clip_end
                    ]
                    prop = "scale_y"
                anim_id = f"__blink__{shot.id}_{path.replace('/', '.')}_{len(placed)}"
                duration = max(0.001, clip_end - clip_start)
                animations[anim_id] = AnimationClipJSON(
                    name=anim_id,
                    duration=duration,
                    channels=[ChannelJSON(target=path, property=prop, keyframes=kfs)],
                )
                placed.append(
                    PlacedClipJSON(
                        animation_id=anim_id, start_time=clip_start, duration=duration
                    )
                )
    return placed


def _compress_linear(times: list[float], values: list[float]) -> list[KeyframeJSON]:
    """Keyframes for a per-frame sampled curve, dropping the interior of constant
    runs (linear easing between equal endpoints reproduces them exactly)."""
    kfs: list[KeyframeJSON] = []
    n = len(times)
    for i in range(n):
        keep = (
            i == 0
            or i == n - 1
            or values[i] != values[i - 1]
            or values[i] != values[i + 1]
        )
        if keep:
            kfs.append(KeyframeJSON(time=times[i], value=values[i], easing="linear"))
    return kfs


def _lid_blink_at(t: float, windows: list[tuple[float, float]]) -> float:
    """−1 inside a blink's closed span (the central half of its window), else
    +inf — the blink is a contributor that can only CLOSE, so outside a blink
    it must not cap a positive (wide) offset (the first draft returned 0 here
    and the `WIDE` rung of the ladder was unreachable, an#98 review)."""
    lo, hi = _EYELID_CLOSED_SPAN
    for start, end in windows:
        span = end - start
        if start + lo * span <= t < start + hi * span:
            return -1.0
    return math.inf


def _blink_squash_at(t: float, windows: list[tuple[float, float]]) -> float:
    for start, end in windows:
        if start < t < end:
            u = (t - start) / (end - start)
            return 1.0 - _BLINK_DEPTH * math.sin(u * math.pi)
    return 1.0


def _add_face_clips(
    shot: Shot,
    animations: dict[str, AnimationClipJSON],
    tracks: list[TrackJSON],
    *,
    vocab: _SwapVocabulary,
    fps: int,
    mall: Mapping[str, Mapping] | None = None,
    provider: ExpressionProvider | None = None,
    poses: Mapping[str, Mapping[tuple[str, str], _StepCurve]] | None = None,
    view_spans: Mapping[str, list[_ViewSpan]] | None = None,
) -> tuple[dict[str, float], dict[str, int]]:
    """Emit the face of every character: blinks, expressions, the silent mouth
    form — **exactly one channel per (node, property)**, summed at compile
    time, placed at the FRONT of the entity's track like blinks (an#88), so an
    authored channel on a face node still wins by later-wins evaluation.

    Two paths, decided per entity by whether anything expresses on it:

    - **Nothing does** (no `expression` leaf, no `[emotion]` line): the an#88
      blink clips, verbatim, through :func:`_blink_placements` — same ids,
      same exact-time keyframes — so every pre-Wave-6 scene's compiled
      document is byte-identical and the corpus contract hashes hold.
    - **Something does**: the solver samples every frame. Brows: ``rest + Σ
      axis·gain`` on the bound ``(node, property)`` (the descriptor's binding,
      default from its slots). Lids: ``lid(t) = min(lid_expr(t), lid_blink(t))``
      read off the eyelid ladder on rigs with closed art, or a scaled squash on
      rigs without — so a blink always closes and a sleepy `half` never masks
      one. The mouth's silent form: a hold on ``viseme@<form>``'s rest key
      over the expression's span, outside the entity's dialogue lines (lines
      carry their own channel, `_add_viseme_clips`).

    A baked face (``face_overlay: false``) refuses an authored expression with
    the same reasons ``an validate`` reports, and warns on the dialogue sugar.

    A rig with a pupil layer (an#99) always takes the solver path, expressed on
    or not: its ambient saccades are a contributor like blinks. Returns the
    blink phases and the gaze seeds used, per entity, for the scene's meta.

    ``poses`` (an#197, :func:`_swap_pose_layer`) is a contributor too: a posed
    entity always takes the solver path, which folds the pose into every
    channel it drives (a posed pupil keeps its gaze on top of the pose) and
    emits the rest of the pose as step channels in the same clip.

    ``view_spans`` (an#220, :func:`_view_spans`): an entity shown in a view it
    declares per-view face sets for takes the solver path too, whose lids and
    silent mouth then draw from ``eyelid@<view>``/``viseme@<view>`` over that
    view's spans.
    """
    provider = provider or DefaultExpressionProvider()
    phases: dict[str, float] = {}
    seeds: dict[str, int] = {}
    baked = _baked_face_speakers(shot, mall)
    track_lookup: dict[str, TrackJSON] = {t.target_root: t for t in tracks}
    spans_of = getattr(provider, "spans", None)

    def place_first(entity_id: str, placed: list[PlacedClipJSON]) -> None:
        track = track_lookup.get(entity_id)
        if track is None:
            track = TrackJSON(target_root=entity_id, clips=[])
            tracks.append(track)
            track_lookup[entity_id] = track
        track.clips[:0] = placed

    for entity in shot.entities:
        if entity.kind != "character":
            continue
        spans = list(spans_of(shot, entity.id)) if spans_of is not None else []
        if entity.id in baked:
            authored = [sp for sp in spans if sp.source == "action"]
            if authored:
                problems = expression_problems(
                    vocab.descriptors.get(entity.id),
                    preset=authored[0].preset,
                    who=entity.id,
                )
                raise CutoutCompileError(
                    str(ExpressionResolutionError(entity.id, problems))
                )
            if spans:
                warnings.warn(
                    f"shot {shot.id!r}: {entity.id!r} has its face baked into the head "
                    "art (face_overlay: false), so the [emotion] on its dialogue moves "
                    "nothing; the audio still plays.",
                    CutoutCompileWarning,
                    stacklevel=2,
                )
            # No face to solve, but a whole-character swap still poses the
            # body (a baked-face rig's views hide an arm all the same).
            pose = (poses or {}).get(entity.id)
            if pose:
                anim_id = f"__pose__{shot.id}_{entity.id}"
                duration = max(0.001, float(shot.duration))
                animations[anim_id] = AnimationClipJSON(
                    name=anim_id, duration=duration, channels=_pose_step_channels(pose)
                )
                place_first(
                    entity.id,
                    [
                        PlacedClipJSON(
                            animation_id=anim_id, start_time=0.0, duration=duration
                        )
                    ],
                )
            continue
        desc = vocab.descriptors.get(entity.id)
        if desc is not None:
            for sp in spans:
                problems = expression_problems(
                    desc, preset=sp.preset, axes=sp.axes, who=entity.id
                )
                if problems:
                    raise CutoutCompileError(
                        str(ExpressionResolutionError(entity.id, problems))
                    )
        # A span that asks for nothing — `preset: None` with no axes, or
        # `intensity: 0` — is not a contributor: the entity keeps its verbatim
        # blink clips rather than a rest-valued face clip (an#98 review).
        # ...and an axis the rig binds nothing to (gaze on a rig without
        # pupils, an#99) contributes nothing either: the document stays the one
        # the rig had, and `an character validate` says why.
        if desc is None or not spans:
            spans = [
                sp
                for sp in spans
                if sp.intensity > 0 and (sp.offsets() or sp.mouth_form)
            ]
        else:
            try:
                bound = {b.axis for b in binding_for(desc)}
            except ExpressionResolutionError as e:
                raise CutoutCompileError(str(e)) from e
            spans = [
                sp
                for sp in spans
                if sp.intensity > 0
                and (sp.mouth_form or any(a in bound for a in sp.offsets()))
            ]
        has_pupils = desc is not None and bool(_pupil_paths(vocab, entity.id))
        pose = (poses or {}).get(entity.id)
        entity_views = (view_spans or {}).get(entity.id)
        if (
            not spans and not has_pupils and not pose and not entity_views
        ) or desc is None:
            if spans and desc is None:
                warnings.warn(
                    f"shot {shot.id!r}: {entity.id!r} has no descriptor (a procedural "
                    "rig), so its expression has no binding and moves nothing.",
                    CutoutCompileWarning,
                    stacklevel=2,
                )
            placed = _blink_placements(
                shot, entity.id, animations, vocab=vocab, fps=fps
            )
            if placed is None:
                continue
            phases[entity.id] = blink_phase(entity.id)
        else:
            placed = _solve_face(
                shot,
                entity.id,
                desc,
                animations,
                tracks,
                vocab=vocab,
                fps=fps,
                provider=provider,
                spans=spans,
                pose=pose,
                view_spans=entity_views,
            )
            if _eye_paths(vocab, entity.id):
                phases[entity.id] = blink_phase(entity.id)
            if has_pupils:
                seeds[entity.id] = gaze_seed(entity.id)
        if not placed:
            continue
        place_first(entity.id, placed)
    return phases, seeds


def _pupil_paths(vocab: _SwapVocabulary, entity_id: str) -> list[str]:
    return sorted(
        p
        for p in vocab.paths
        if p.split("/", 1)[0] == entity_id and p.rsplit("/", 1)[-1] in PUPIL_NODE_NAMES
    )


def _solve_face(
    shot: Shot,
    entity_id: str,
    desc: CharacterDescriptor,
    animations: dict[str, AnimationClipJSON],
    tracks: list[TrackJSON],
    *,
    vocab: _SwapVocabulary,
    fps: int,
    provider: ExpressionProvider,
    spans,
    pose: Mapping[tuple[str, str], _StepCurve] | None = None,
    view_spans: list[_ViewSpan] | None = None,
) -> list[PlacedClipJSON]:
    """The solved face of one expressed-on entity: one clip, one channel per key.

    A ``pose`` (an#197) replaces the rest a channel is summed onto, frame by
    frame, for every (node, property) the solver drives; the pose's other
    curves ride the same clip as step channels.

    ``view_spans`` (an#220): over a span whose view the eye declares a lid set
    for (``eyelid@side``), the lid — blinks and expression alike — is keyed
    on that set, one clip per span, each ending just before the next begins
    (two swap sets live at one instant would resolve by NAME, not by time);
    the mouth holds its view set's rest outside the lines the same way.
    """
    curves = {
        c.axis: list(c.samples) for c in provider.curves(shot, entity_id, fps=fps)
    }
    n = int(math.ceil(float(shot.duration) * fps - 1e-9)) + 1
    times = [f / fps for f in range(n)]
    k = vocab.entity_scale.get(entity_id, 1.0)
    windows = _blink_windows(entity_id, shot.duration)
    # Ambient saccades (an#99): one more addend on the gaze axes, seeded by
    # the entity name, sample-and-held at frame times — only where the rig
    # has pupils to move (the binding is what says so).
    if _pupil_paths(vocab, entity_id):
        steps = saccade_track(
            entity_id, duration=float(shot.duration), fps=fps, blink_windows=windows
        )
        sx, sy = [0.0] * n, [0.0] * n
        j = 0
        for i, t in enumerate(times):
            while j + 1 < len(steps) and steps[j + 1].time <= t + 1e-9:
                j += 1
            sx[i], sy[i] = steps[j].x, steps[j].y
        for axis, jitter in (("gaze_x", sx), ("gaze_y", sy)):
            base = curves.get(axis) or [0.0] * n
            base = (base + [base[-1]] * n)[:n]
            curves[axis] = [max(-1.0, min(1.0, base[i] + jitter[i])) for i in range(n)]
    if "gaze_x" in curves or "gaze_y" in curves:
        # The pupil stays inside the WHITE, an ellipse, not inside a box: the
        # summed (x, y) — in axis units, where the declared travel is the unit
        # circle — is clamped to a circle of radius GAZE_ELLIPSE_MARGIN. At
        # the corner of the box the pupil disc pokes past the sclera by ~3
        # canvas units (an#99 review); at 0.95 it stays inside on every angle.
        gx = list(curves.get("gaze_x") or [0.0] * n)
        gy = list(curves.get("gaze_y") or [0.0] * n)
        gx, gy = (gx + [gx[-1]] * n)[:n], (gy + [gy[-1]] * n)[:n]
        for i in range(n):
            m = math.hypot(gx[i], gy[i])
            if m > GAZE_ELLIPSE_MARGIN:
                gx[i] *= GAZE_ELLIPSE_MARGIN / m
                gy[i] *= GAZE_ELLIPSE_MARGIN / m
        curves["gaze_x"], curves["gaze_y"] = gx, gy
    # Authored channels on face nodes win; say so once per (target, property).
    authored: set[tuple[str, str]] = set()
    for track in tracks:
        if track.target_root != entity_id:
            continue
        for clip in track.clips:
            anim = animations.get(clip.animation_id)
            if anim is not None:
                authored.update((ch.target, ch.property) for ch in anim.channels)

    offsets: dict[tuple[str, str], list[float]] = {}
    lid_expr: dict[str, list[float]] = {}
    try:
        bindings = binding_for(desc)
    except ExpressionResolutionError as e:
        raise CutoutCompileError(str(e)) from e
    for b in bindings:
        samples = curves.get(b.axis)
        if samples is None:
            continue
        samples = (samples + [samples[-1]] * n)[:n]
        path = f"{entity_id}/{slot_node_path(desc, b.slot)}"
        if path not in vocab.paths:
            continue  # the rig builder did not build the slot (suppressed / no art)
        if isinstance(b, ChannelBinding):
            gain = b.gain * (k if b.rig_scaled else 1.0)
            acc = offsets.setdefault((path, b.property), [0.0] * n)
            for i in range(n):
                acc[i] += samples[i] * gain
        elif isinstance(b, SetBinding):
            acc = lid_expr.setdefault(path, [0.0] * n)
            for i in range(n):
                acc[i] += samples[i]

    pose = pose or {}

    def base_values(path: str, prop: str) -> list[float]:
        """The value each frame's contributors sum onto: the rest, or the pose."""
        curve = pose.get((path, prop))
        if curve is None:
            return [float(getattr(vocab.node_transforms[path], prop))] * n
        return [_step_at(curve, t) for t in times]

    folded: set[tuple[str, str]] = set()
    channels: list[ChannelJSON] = []
    for (path, prop), acc in sorted(offsets.items()):
        if (path, prop) in authored:
            warnings.warn(
                f"shot {shot.id!r}: an authored channel on {path!r}:{prop!r} "
                f"overrides the expression's {prop} on that node (authored wins).",
                CutoutCompileWarning,
                stacklevel=3,
            )
        base = base_values(path, prop)
        folded.add((path, prop))
        channels.append(
            ChannelJSON(
                target=path,
                property=prop,
                keyframes=_compress_linear(times, [b + v for b, v in zip(base, acc)]),
            )
        )
    # Lids: every eye node, expression or not — a blink is a lid contributor.
    placed_lids: list[PlacedClipJSON] = []
    for path in _eye_paths(vocab, entity_id):
        expr = lid_expr.get(path, [0.0] * n)
        eyelid = vocab.node_sets.get(path, {}).get(EYELID_CHANNEL) or {}
        has_art = LID_KEY_OPEN in eyelid and LID_KEY_CLOSED in eyelid
        rest_key = vocab.rest_key(path, EYELID_CHANNEL) if has_art else None
        if has_art and rest_key not in (None, LID_KEY_OPEN):
            continue  # rests closed: the author's call, not a blink's
        if has_art:
            per_view = _lid_view_spans(vocab, entity_id, path, view_spans)
            lid_sets = {EYELID_CHANNEL} | {v for _, _, v in per_view or ()}
            lid_authored = any((path, lid) in authored for lid in lid_sets)
            if lid_authored and not per_view:
                continue  # an authored eye channel overrides the lid entirely (an#88)
            if per_view:
                # Per-view lids (an#220) are emitted even under an authored lid
                # channel — without them the profile's eye art never shows —
                # but then carry no auto-blink (an#88: authored overrides the
                # blinks), and the authored clips still win where they play.
                blink_windows = [] if lid_authored else windows
                placed_lids.extend(
                    _lid_span_clips(
                        shot,
                        entity_id,
                        path,
                        per_view,
                        animations,
                        vocab=vocab,
                        times=times,
                        lid_at=lambda i, t, bw=blink_windows: min(
                            expr[i], _lid_blink_at(t, bw)
                        ),
                    )
                )
                continue
            keys = [
                lid_key(min(expr[i], _lid_blink_at(t, windows)), available=eyelid)
                for i, t in enumerate(times)
            ]
            kfs = [KeyframeJSON(time=times[0], value=keys[0], easing="step")]
            for i in range(1, n):
                if keys[i] != keys[i - 1]:
                    kfs.append(
                        KeyframeJSON(time=times[i], value=keys[i], easing="step")
                    )
            channels.append(
                ChannelJSON(target=path, property=EYELID_CHANNEL, keyframes=kfs)
            )
        else:
            if (path, "scale_y") in authored:
                continue
            base_sy = base_values(path, "scale_y")
            folded.add((path, "scale_y"))
            values = [
                max(
                    0.05 * base_sy[i],
                    base_sy[i]
                    * _blink_squash_at(t, windows)
                    * (1.0 + LID_SQUASH_GAIN * expr[i]),
                )
                for i, t in enumerate(times)
            ]
            channels.append(
                ChannelJSON(
                    target=path,
                    property="scale_y",
                    keyframes=_compress_linear(times, values),
                )
            )

    # The pose's own curves, where no contributor above drives the property:
    # held steps, keyed where each whole-character swap lands.
    channels.extend(_pose_step_channels(pose, skip=folded))

    placed: list[PlacedClipJSON] = []
    if channels:
        anim_id = f"__face__{shot.id}_{entity_id}"
        duration = max(0.001, times[-1])
        animations[anim_id] = AnimationClipJSON(
            name=anim_id, duration=duration, channels=channels
        )
        placed.append(
            PlacedClipJSON(animation_id=anim_id, start_time=0.0, duration=duration)
        )
    placed.extend(placed_lids)

    # The silent mouth form: hold the variant's rest key over each expression
    # span, outside this entity's dialogue lines — and, whenever any variant is
    # in play, hold the NEUTRAL set's rest over the whole shot at the very
    # front, so the mouth returns to neutral art when a variant span or a
    # variant-set line ends (the runtime keeps the last texture a property set;
    # with nothing re-asserting `viseme` the mouth stayed on `X_happy` for the
    # rest of the shot, an#98 review). Two properties live at one instant
    # resolve by NAME order in the runtime (`viseme@…` sorts after `viseme`),
    # so the variant wins wherever it is live and neutral shows elsewhere.
    # Each hold ends one frame BEFORE a line's first frame and starts one
    # frame AFTER the line clip's last frame, so no frame carries both a hold
    # and the line's own key.
    frame = 1.0 / fps
    line_windows = []
    for l in shot.dialogue:
        if l.speaker == entity_id and l.start is not None and l.duration is not None:
            a = float(l.start)
            end = (
                a + math.ceil(float(l.duration) * fps - 1e-9) / fps
            )  # the clip's inclusive last frame
            line_windows.append((a, end))
    variant_used = any(sp.mouth_form for sp in spans)
    for l in shot.dialogue:
        if (
            l.speaker == entity_id
            and l.start is not None
            and getattr(l, "emotion", None)
        ):
            variant_used = variant_used or bool(
                mouth_form_of((l.emotion or "").strip().lower())
            )

    def hold_clips(
        set_name: str,
        rest: str,
        target: str,
        spans_: list[tuple[float, float]],
        tag: str,
        holes: list[tuple[float, float]] = (),
        exact: bool = False,
    ) -> None:
        # `exact` (per-view mouths, an#220): an edge that is a VIEW change —
        # a span's own end, a hole's — stays where it is rather than snapping
        # to a frame, and a hold ending at one stops just short of it: the two
        # sets meeting there then never play at one instant, where they would
        # resolve by name rather than by which view is in force.
        view_edges = (
            [x for a_, b_ in spans_ for x in (a_, b_)] + [x for h in holes for x in h]
            if exact
            else []
        )

        def at_edge(x: float) -> bool:
            return any(abs(x - e) < 1e-12 for e in view_edges)

        for j, (a, b) in enumerate(spans_):
            pieces = [
                piece
                for gap in _subtract_intervals((a, b), list(holes))
                for piece in _subtract_intervals(gap, line_windows)
            ]
            for k, (ha, hb) in enumerate(pieces):
                # Snap to frames: start on the first frame at/after `ha` (one
                # frame after a line's last frame when `ha` is that frame),
                # end on the last frame strictly before `hb`'s line.
                start = math.ceil(ha * fps - 1e-9) / fps
                if any(abs(start - lw_end) < 1e-9 for _, lw_end in line_windows):
                    start += frame
                end = min(shot.duration, math.ceil(hb * fps - 1e-9) / fps)
                if (
                    any(abs(end - lw_start) < 1e-9 for lw_start, _ in line_windows)
                    or end > hb + 1e-9
                    and any(
                        lw_start - 1e-9 <= end <= lw_end + 1e-9
                        for lw_start, lw_end in line_windows
                    )
                ):
                    end -= frame
                # A view edge that is also a line's edge keeps the frame push
                # away from the line: the line's clip owns its last frame.
                if at_edge(ha) and not any(
                    abs(ha - le) < 1e-9 for _, le in line_windows
                ):
                    start = ha
                if (
                    at_edge(hb)
                    and hb < float(shot.duration) - 1e-9
                    and not any(abs(hb - ls) < 1e-9 for ls, _ in line_windows)
                ):
                    end = hb - _VIEW_SPAN_EDGE_S
                if end - start < -1e-9:
                    continue
                dur = max(0.001, end - start)
                anim_id = f"__face_mouth__{shot.id}_{entity_id}_{tag}_{j}_{k}_{target.replace('/', '.')}"
                animations[anim_id] = AnimationClipJSON(
                    name=anim_id,
                    duration=dur,
                    channels=[
                        ChannelJSON(
                            target=target,
                            property=set_name,
                            keyframes=[
                                KeyframeJSON(time=0.0, value=rest, easing="step")
                            ],
                        )
                    ],
                )
                placed.append(
                    PlacedClipJSON(animation_id=anim_id, start_time=start, duration=dur)
                )

    # Per-view mouths (an#220): over a view the mouth has its own set for,
    # hold THAT set's rest outside the lines (a line there speaks on it,
    # `_add_viseme_clips`); over every other view hold the neutral rest, so
    # the mouth leaves the profile's art when the character turns back. The
    # expression holds above step aside over the view's spans — a profile's
    # mouth is the profile's.
    view_holes: dict[str, list[tuple[float, float]]] = {}
    for target in vocab.swap_capable_paths(entity_id, VISEME_CHANNEL):
        per_view = [
            (a, b, _face_set_for(vocab, entity_id, target, VISEME_CHANNEL, v))
            for a, b, v in view_spans or ()
        ]
        if not any(set_name != VISEME_CHANNEL for _, _, set_name in per_view):
            continue
        holes = view_holes.setdefault(target, [])
        for j, (a, b, set_name) in enumerate(per_view):
            rest = _mouth_rest_key(vocab, target, set_name)
            if set_name != VISEME_CHANNEL:
                holes.append((a, b))
            if rest is not None and b > a:
                hold_clips(set_name, rest, target, [(a, b)], f"view{j}", exact=True)
    if variant_used:
        for target in vocab.swap_capable_paths(entity_id, VISEME_CHANNEL):
            rest = _mouth_rest_key(vocab, target, VISEME_CHANNEL)
            if rest is not None:
                hold_clips(
                    VISEME_CHANNEL,
                    rest,
                    target,
                    [(0.0, float(shot.duration))],
                    "neutral",
                    holes=view_holes.get(target, []),
                    exact=bool(view_holes.get(target)),
                )
    for idx, sp in enumerate(spans):
        if sp.mouth_form is None or sp.source != "action":
            continue
        set_name = f"{VISEME_CHANNEL}@{sp.mouth_form}"
        for target in vocab.swap_capable_paths(entity_id, set_name):
            rest = _mouth_rest_key(vocab, target, set_name)
            if rest is None:
                continue
            hold_clips(
                set_name,
                rest,
                target,
                [(sp.start, sp.end)],
                str(idx),
                holes=view_holes.get(target, []),
                exact=bool(view_holes.get(target)),
            )
    return placed


def _lid_view_spans(
    vocab: _SwapVocabulary,
    entity_id: str,
    path: str,
    view_spans: list[_ViewSpan] | None,
) -> list[tuple[float, float, str]] | None:
    """``[(start, end, eyelid set)]`` over the shot for one eye, or ``None``
    when every span keys on the plain ``eyelid`` set (then the lid is the one
    channel it always was). A per-view set without ``OPEN`` and ``CLOSED`` art
    cannot blink, so that view's lid stays on the plain set (an#220)."""
    out: list[tuple[float, float, str]] = []
    for a, b, view in view_spans or ():
        set_name = _face_set_for(vocab, entity_id, path, EYELID_CHANNEL, view)
        keys = vocab.node_sets.get(path, {}).get(set_name) or {}
        if LID_KEY_OPEN not in keys or LID_KEY_CLOSED not in keys:
            set_name = EYELID_CHANNEL
        out.append((a, b, set_name))
    if not any(set_name != EYELID_CHANNEL for _, _, set_name in out):
        return None
    return out


def _lid_span_clips(
    shot: Shot,
    entity_id: str,
    path: str,
    per_view: list[tuple[float, float, str]],
    animations: dict[str, AnimationClipJSON],
    *,
    vocab: _SwapVocabulary,
    times: list[float],
    lid_at: Callable[[int, float], float],
) -> list[PlacedClipJSON]:
    """One lid clip per view span (an#220): the solver's lid value, read off
    the ladder of THAT span's set, keyed from the span's start. Each clip but
    the last ends :data:`_VIEW_SPAN_EDGE_S` before the next span, so at every
    instant exactly one lid set is playing and the latest-written one shows."""
    placed: list[PlacedClipJSON] = []
    for j, (a, b, set_name) in enumerate(per_view):
        last = j == len(per_view) - 1
        end = b if last else b - _VIEW_SPAN_EDGE_S
        if end <= a:
            continue
        available = vocab.node_sets[path][set_name]
        frames = [
            (t, lid_key(lid_at(i, t), available=available))
            for i, t in enumerate(times)
            if a - 1e-9 <= t <= end + 1e-9
        ]
        if not frames:  # a span shorter than a frame: the nearest frame's lid
            i = min(range(len(times)), key=lambda i: abs(times[i] - a))
            frames = [(a, lid_key(lid_at(i, times[i]), available=available))]
        # Keyed from the span's start with its first frame's lid.
        kfs = [KeyframeJSON(time=0.0, value=frames[0][1], easing="step")]
        for (t, key), (_, prev) in zip(frames[1:], frames):
            if key != prev:
                kfs.append(KeyframeJSON(time=t - a, value=key, easing="step"))
        anim_id = f"__face_lid__{shot.id}_{entity_id}_{j}_{path.replace('/', '.')}"
        duration = max(0.001, end - a)
        animations[anim_id] = AnimationClipJSON(
            name=anim_id,
            duration=duration,
            channels=[ChannelJSON(target=path, property=set_name, keyframes=kfs)],
        )
        placed.append(
            PlacedClipJSON(animation_id=anim_id, start_time=a, duration=duration)
        )
    return placed


def _subtract_intervals(
    span: tuple[float, float], holes: list[tuple[float, float]]
) -> list[tuple[float, float]]:
    """``span`` minus every hole, as sorted disjoint intervals."""
    out: list[tuple[float, float]] = []
    cursor, end = span
    for a, b in sorted((min(h), max(h)) for h in holes):
        if b <= cursor or a >= end:
            continue
        if a > cursor:
            out.append((cursor, a))
        cursor = max(cursor, b)
    if cursor < end:
        out.append((cursor, end))
    return out


def _swap_pose_layer(
    swaps: list[_EntitySwap], vocab: _SwapVocabulary
) -> dict[str, dict[tuple[str, str], _StepCurve]]:
    """``{entity id: {(node path, property): step curve}}`` — the transforms the
    descriptor's ``swap_poses`` put on its slots as each whole-character swap
    lands (an#197). A key poses the slots it lists; every other slot any key
    of that set poses is at rest. Offsets (``x``, ``y``) are view_box units,
    scaled by the rig's k and added to the rest; ``rotation`` is radians,
    added unscaled; factors (``scale_*``,
    ``alpha``) multiply it; several posed sets compose the same way.

    A curve that never leaves the rest is dropped, and an entity nothing
    poses is absent — so a scene without whole-character swaps compiles
    byte-identically. Slots the rig builder did not build are skipped, as the
    face solver skips them.
    """
    by_entity: dict[str, list[_EntitySwap]] = {}
    for swap in swaps:
        by_entity.setdefault(swap.entity_id, []).append(swap)
    layer: dict[str, dict[tuple[str, str], _StepCurve]] = {}
    for entity_id, events in by_entity.items():
        desc = vocab.descriptors[entity_id]
        posed_sets = {e.set_name for e in events if desc.swap_poses.get(e.set_name)}
        if not posed_sets:
            continue
        k = vocab.entity_scale.get(entity_id, 1.0)
        paths: dict[str, str] = {}
        for set_name in sorted(posed_sets):
            for per_key in desc.swap_poses[set_name].values():
                for slot in per_key:
                    try:
                        path = f"{entity_id}/{slot_node_path(desc, slot)}"
                    except KeyError:
                        continue  # `an character validate` names the slot
                    if path in vocab.paths:
                        paths[slot] = path
        state: dict[str, str] = {}
        curves: dict[tuple[str, str], _StepCurve] = {}
        # Stable by time: at one instant the later-authored swap wins.
        for event in sorted(events, key=lambda e: e.time):
            if event.set_name not in posed_sets:
                continue
            state[event.set_name] = event.key
            for slot, path in paths.items():
                rest = vocab.node_transforms[path]
                poses = [
                    desc.swap_poses[s].get(key, {}).get(slot)
                    for s, key in sorted(state.items())
                ]
                poses = [p for p in poses if p is not None]
                for prop in SLOT_POSE_OFFSETS:
                    value = float(getattr(rest, prop)) + k * sum(
                        getattr(p, prop) for p in poses
                    )
                    curves.setdefault((path, prop), []).append((event.time, value))
                for prop in SLOT_POSE_ANGLES:
                    value = float(getattr(rest, prop)) + sum(
                        getattr(p, prop) for p in poses
                    )
                    curves.setdefault((path, prop), []).append((event.time, value))
                for prop in SLOT_POSE_FACTORS:
                    value = float(getattr(rest, prop)) * math.prod(
                        getattr(p, prop) for p in poses
                    )
                    curves.setdefault((path, prop), []).append((event.time, value))
        out: dict[tuple[str, str], _StepCurve] = {}
        for (path, prop), keys in curves.items():
            rest_value = float(getattr(vocab.node_transforms[path], prop))
            if all(abs(v - rest_value) < 1e-9 for _, v in keys):
                continue
            steps: _StepCurve = [] if keys[0][0] <= 0.0 else [(0.0, rest_value)]
            for t, v in keys:
                if steps and abs(steps[-1][0] - t) < 1e-12:
                    steps[-1] = (t, v)  # same instant: the later swap wins
                elif not steps or steps[-1][1] != v:
                    steps.append((max(0.0, t), v))
            out[(path, prop)] = steps
        if out:
            layer[entity_id] = out
    return layer


#: ``(start, end, view)``: a stretch of the shot one view is in force over;
#: ``None`` is the default art's view with no ``rest_view`` declared.
_ViewSpan = tuple[float, float, "str | None"]


def _view_spans(
    swaps: list[_EntitySwap],
    vocab: _SwapVocabulary,
    *,
    duration: float,
    view_set: str = VIEW_CHANNEL,
) -> dict[str, list[_ViewSpan]]:
    """``{entity id: [(start, end, view)]}`` for every character whose
    descriptor declares a per-view face set (``eyelid@side``, an#220), and
    that some stretch of the shot shows in a view one of those sets serves.

    The view is the latest whole-character ``view`` swap at or before each
    instant (a ``turn`` lands its swap at its midpoint), else the
    descriptor's ``rest_view``. An entity with no per-view set, or whose views
    never reach one, is absent — so every other scene compiles exactly as it
    did.
    """
    out: dict[str, list[_ViewSpan]] = {}
    for entity_id, desc in sorted(vocab.descriptors.items()):
        variants = view_variant_sets(desc, view_set=view_set)
        served = {v for per_view in variants.values() for v in per_view}
        if not served:
            continue
        events = sorted(
            (e for e in swaps if e.entity_id == entity_id and e.set_name == view_set),
            key=lambda e: e.time,
        )
        spans: list[_ViewSpan] = []
        current, since = desc.rest_view, 0.0
        for event in events:
            t = min(max(0.0, event.time), float(duration))
            if event.key == current:
                continue
            if t > since:
                spans.append((since, t, current))
            current, since = event.key, t
        spans.append((since, float(duration), current))
        if any(view in served for _, _, view in spans):
            out[entity_id] = spans
    return out


def _view_at(spans: list[_ViewSpan] | None, t: float) -> str | None:
    """The view in force at ``t`` over ``spans`` (``None`` without spans)."""
    view = None
    for start, _, v in spans or ():
        if start <= t + 1e-9:
            view = v
    return view


def _face_set_for(
    vocab: _SwapVocabulary, entity_id: str, path: str, base: str, view: str | None
) -> str:
    """Which set ``path`` draws ``base`` from in ``view``: the per-view variant
    (``eyelid@side``) when the descriptor declares it AND the node carries it
    (its art resolved), else ``base`` (an#220)."""
    desc = vocab.descriptors.get(entity_id)
    if desc is None or view is None:
        return base
    variant = view_variant_sets(desc).get(base, {}).get(view)
    if variant is not None and variant in vocab.node_sets.get(path, {}):
        return variant
    return base


def _expand_preset_plays(
    flat_list: list[FlatAction],
    *,
    vocab: _SwapVocabulary | None,
    fps: int = 30,
    step_hz: float | None = None,
    default_easing: Any = None,
    resolutions: list[AssetResolutionJSON] | None = None,
) -> list[FlatAction]:
    """Replace each ``play`` of a motion preset with the flat tweens and sets
    it expands to (an#166), and give every from-less tween its start (an#212);
    descriptor plays pass through to :func:`_resolve_play`.

    Every ``play`` — both sources — is checked here by
    :func:`cutan.characters.play.play_problems`, the verdict ``an validate``
    reports, so the two cannot disagree about a name, an argument or a
    source.

    **Both read the pose the timeline has AT their start** (an#212): the
    moved node's BUILT transform (``vocab.node_transforms`` — the stage
    placement included; the identity with no vocabulary), overridden by the
    authored ``set``s and tweens before it on the same (target, property), as
    the runtime evaluates them (:func:`_value_at`). So a ``tween`` with no
    ``from`` continues from where the entity stands — its ``stage`` ``at``, the
    end of the tween before it, a ``set`` at the same instant — instead of
    jumping to the property's identity value, and a preset played after a move
    (a ``hop`` after a walk) starts where the move left it. Leaves are
    resolved in time order (authoring order at one instant), each seeing the
    ones before it resolved; the output keeps authoring order, which is what
    the tracks' later-wins reads. Descriptor ``play`` clips and the compiled
    face, blink and lip-sync channels are not part of that pose: they write
    their own nodes, which authored motion does not tween.

    A ``turn`` that does not say which way it faced opens from the side the
    timeline before it left the entity facing (:func:`cutan.characters.play.
    resolve_turns`, an#203) — the resolver ``an validate`` checks with.
    """
    from an.stage.timeline import write_group
    from an.motion import HOME_PRESETS, IDENTITY_POSE, POSE_PROPERTIES

    def built_rest(path: str) -> dict[str, float] | None:
        if vocab is None:
            return dict(IDENTITY_POSE)
        transform = vocab.node_transforms.get(path)
        if transform is None:
            return None
        return {p: float(getattr(transform, p)) for p in POSE_PROPERTIES}

    flat_list = resolve_turns(
        flat_list,
        descriptor_of=lambda e: vocab.descriptors.get(e) if vocab is not None else None,
        rest_of=built_rest,
    ).flats
    presets: set[int] = set()
    for i, flat in enumerate(flat_list):
        action = flat.action
        if not isinstance(action, PlayAction):
            continue
        entity_id = _track_root_of(action.target)
        desc = vocab.descriptors.get(entity_id) if vocab is not None else None
        problems = play_problems(
            desc,
            action.animation,
            art_exists=vocab.art_exists.get(entity_id) if vocab is not None else None,
            args=action.args,
            duration=action.duration,
            speed=action.speed,
            loop=action.loop,
        )
        if problems:
            raise CutoutCompileError(
                f"play of {action.animation!r} on {action.target!r}: "
                + "; ".join(problems)
            )
        if play_source(desc, action.animation) == PRESET_SOURCE:
            presets.add(i)

    history: dict[tuple[str, str], list[tuple[tuple[int, int], FlatAction]]] = {}
    placed: dict[int, list[FlatAction]] = {}

    def value_at(target: str, prop: str, t: float, base: float) -> float:
        return _value_at(
            history.get((target, write_group(prop)), []),
            prop,
            t,
            base,
            vocab=vocab,
            fps=fps,
            step_hz=step_hz,
            default_easing=default_easing,
        )

    def pose_at(path: str, t: float) -> dict[str, float] | None:
        rest = built_rest(path)
        if rest is None:
            return None
        return {p: value_at(path, p, t, v) for p, v in rest.items()}

    for i in sorted(range(len(flat_list)), key=lambda k: (flat_list[k].start, k)):
        flat = flat_list[i]
        action = flat.action
        if i in presets:
            rest_of = (
                built_rest
                if action.animation in HOME_PRESETS
                else lambda path, t=flat.start: pose_at(path, t)
            )
            parts_of = None
            if preset_takes(action.animation, PARTS_ARG) and vocab is not None:
                action, rest_of = _with_view_and_posed_parts(
                    action,
                    flat.start,
                    rest_of,
                    history=history,
                    vocab=vocab,
                    resolutions=resolutions,
                )

                def parts_of(entity: str) -> list[str]:
                    prefix = f"{entity}/"
                    return [
                        p[len(prefix) :]
                        for p in vocab.node_transforms
                        if p.startswith(prefix)
                    ]

            try:
                leaves = expand_preset_play(
                    action, start=flat.start, rest_of=rest_of, parts_of=parts_of
                )
            except PlayResolutionError as e:
                entity_id = _track_root_of(action.target)
                built = sorted(
                    p
                    for p in (vocab.paths if vocab else ())
                    if p.split("/")[0] == entity_id
                )
                raise CutoutCompileError(
                    f"play of {action.animation!r} on {action.target!r}: "
                    + "; ".join(e.problems)
                    + f" (built: {built})"
                ) from e
        elif (
            isinstance(action, TweenAction)
            and action.from_value is None
            and action.property in _PROPERTY_REST_VALUES
        ):
            base = _built_value(action.target, action.property, vocab=vocab)
            start_value = value_at(action.target, action.property, flat.start, base)
            leaves = [
                dataclasses.replace(
                    flat, action=action.model_copy(update={"from_value": start_value})
                )
            ]
        else:
            leaves = [flat]
        placed[i] = leaves
        for sub, leaf in enumerate(leaves):
            if isinstance(leaf.action, (SetAction, TweenAction)):
                # Keyed by what the property WRITES: `rotation_rad` is `rotation`.
                key = (leaf.action.target, write_group(leaf.action.property))
                history.setdefault(key, []).append(((i, sub), leaf))
    return [leaf for i in range(len(flat_list)) for leaf in placed[i]]


def _built_parts(vocab: _SwapVocabulary, entity: str) -> list[str]:
    """The part paths the builder built under ``entity``, relative to it."""
    prefix = f"{entity}/"
    return [p[len(prefix) :] for p in vocab.node_transforms if p.startswith(prefix)]


def _on_registry(entity: str, vocab: _SwapVocabulary) -> bool:
    """Whether ``entity`` resolves its methods on the capability registry: a
    character (the one entity kind with an analyser, an#248)."""
    from cutan.characters.methods import CHARACTER_KIND

    return vocab.entity_kinds.get(entity) == CHARACTER_KIND


def _character_profile(entity: str, vocab: _SwapVocabulary) -> dict[str, dict]:
    """What a character on stage affords: the character analyser, fed what compiled."""
    from cutan.characters.methods import compile_profile

    return compile_profile(
        vocab.descriptors.get(entity),
        built_parts=_built_parts(vocab, entity),
        art_exists=vocab.art_exists.get(entity),
    )


def _record_substitution(sub, resolutions: list[AssetResolutionJSON] | None) -> None:
    """A method substitution, recorded beside the stand-in assets (ADR 0002 decision 6)."""
    from cutan.characters.methods import substitution_record

    if resolutions is not None:
        resolutions.append(AssetResolutionJSON(**substitution_record(sub)))


def _locomotion_args(
    entity: str,
    args: Mapping[str, Any],
    desc: Any,
    vocab: _SwapVocabulary,
    resolutions: list[AssetResolutionJSON] | None,
) -> dict[str, Any]:
    """The walk's args with its gait the locomotion method the registry resolves
    (an#248): a method id or a pinned choice in ``gait`` is spelled out first,
    its args joining the walk's."""
    from cutan.characters.methods import normalise_gait_args, resolve_walk_gait

    args = normalise_gait_args(args)
    gait, resolution = resolve_walk_gait(
        entity,
        args=args,
        descriptor=desc,
        profile=_character_profile(entity, vocab),
    )
    if resolution.substitution is not None:
        _record_substitution(resolution.substitution, resolutions)
    return {**args, GAIT_ARG: gait}


def _with_view_and_posed_parts(
    action: PlayAction,
    t: float,
    rest_of: Callable[[str], dict[str, float] | None],
    *,
    history: Mapping[tuple[str, str], list[tuple[tuple[int, int], FlatAction]]],
    vocab: _SwapVocabulary,
    resolutions: list[AssetResolutionJSON] | None = None,
) -> tuple[PlayAction, Callable[[str], dict[str, float] | None]]:
    """For a preset that moves an entity's parts (``walk``, an#214): fill its
    ``view`` from the timeline when the author did not (else from the
    descriptor's ``rest_view``, an#220), its ``gait`` from the locomotion
    method the capability registry resolves (an#248: the author's ``gait``,
    else the descriptor's, else the default chain; a requested gait the rig
    cannot honour is a recorded substitution in ``resolutions``), and read a
    part the
    view POSES at its posed value — a side view splays the legs (an#203), so a
    walk swings them about the splay, not about the front-view rest, and ends
    where the view's pose takes them back.

    The view is the last ``view`` swap set on the entity at or before ``t``
    (:func:`cutan.characters.play.facing_at`); none leaves ``view`` unset (the
    preset's default). A part the author has animated keeps its timeline pose.
    """
    from an.stage.timeline import SWAP_WRITE_GROUP, write_group
    from an.motion import DFLT_TURN_SET

    entity = action.target
    args = dict(action.args or {})
    view_set = DFLT_TURN_SET
    events = [
        f
        for _, f in sorted(
            history.get((entity, SWAP_WRITE_GROUP), []), key=lambda e: e[0]
        )
    ]
    view = args.get(VIEW_ARG)
    desc = vocab.descriptors.get(entity)
    posed_view = view
    if view is None and preset_takes(action.animation, VIEW_ARG):
        view = posed_view = facing_at(events, entity, t, view_set=view_set).view
        if view is None and desc is not None:
            # No turn before it: the view the art is DRAWN in (an#220) — a
            # character carved in profile walks as a profile, on its unposed
            # rest (no swap has posed it).
            view = desc.rest_view
        if view is not None:
            args[VIEW_ARG] = view
            action = action.model_copy(update={"args": args})
    if preset_takes(action.animation, GAIT_ARG) and _on_registry(entity, vocab):
        resolved = _locomotion_args(entity, args, desc, vocab, resolutions)
        if resolved != args:
            args = resolved
            action = action.model_copy(update={"args": args})
    posed: dict[tuple[str, str], _StepCurve] = {}
    if posed_view is not None and entity in vocab.descriptors:
        posed = _swap_pose_layer(
            [_EntitySwap(entity, view_set, 0.0, str(posed_view))], vocab
        ).get(entity, {})
    if not posed:
        return action, rest_of

    def posed_rest_of(path: str) -> dict[str, float] | None:
        pose = rest_of(path)
        if pose is None:
            return None
        return {
            prop: (
                posed[(path, prop)][-1][1]
                if (path, prop) in posed and (path, write_group(prop)) not in history
                else value
            )
            for prop, value in pose.items()
        }

    return action, posed_rest_of


def _resolve_play(
    action: PlayAction,
    *,
    anim_id: str,
    vocab: _SwapVocabulary | None,
    fps: int,
    view: str | None = None,
) -> AnimationClipJSON:
    """A ``play`` becomes a clip built from the descriptor animation's tracks
    (an#7). Resolution — which node, which set, which key, and every way it
    can fail — is :func:`cutan.characters.play.resolve_play`, shared with
    ``an validate`` so the two cannot disagree; this function only converts
    the resolved tracks into channel values.

    Two conversions a naive copy gets wrong (the research reasoned them out,
    `tests/test_play.py` pins them):

    - **Units and reference.** A ``bone:<b>.<prop>`` track is a DEVIATION in
      view-box units (rotation in degrees) around the bone's rest; a channel
      carries ABSOLUTE scene values (radians). So every value is
      ``rest + deviation * k`` (positions scale by the rig's view_box → pixel
      factor; rotation by pi/180), read off the built node's transform — a
      naive copy would put the torso at y≈±2 instead of bobbing around its
      rest, and `rotation_deg` is not a runtime property at all.
    - **Attachment swaps.** A ``slot:<s>.attachment`` track names
      ATTACHMENTS; a swap channel carries set KEYS. The whole track resolves
      to ONE set (never split per frame across two channels) and rides the
      same runtime swap path an authored ``set`` does.

    Sine tracks are sampled at the frame rate with linear easing, always
    closing the cycle at the clip end; step and linear tracks map 1:1.
    ``loop`` is the action's override or, when the action says nothing, the
    animation's own.

    ``view`` is the view the entity is in when the play starts (an#220): a
    swap track rides the set's per-view variant (``eyelid@side``) when the
    node carries it and it has every key the track uses — a blink played in
    profile closes the profile's eye, not the front one.
    """
    entity_id = _track_root_of(action.target)
    if vocab is None or entity_id not in vocab.descriptors:
        raise CutoutCompileError(
            f"play of {action.animation!r} on {entity_id!r}: named animations "
            "live in a character descriptor's `animations`, and this entity "
            "has no descriptor (a procedural rig has none). Use tween / set."
        )
    desc = vocab.descriptors[entity_id]
    try:
        resolved = resolve_play(
            desc, action.animation, art_exists=vocab.art_exists.get(entity_id)
        )
    except PlayResolutionError as e:
        raise CutoutCompileError(
            f"play of {action.animation!r} on {entity_id!r}: " + "; ".join(e.problems)
        ) from e
    anim = resolved.animation
    k = vocab.entity_scale.get(entity_id, 1.0)
    duration = max(0.001, float(anim.duration))
    channels: list[ChannelJSON] = []
    for rt in resolved.tracks:
        path = (
            entity_id
            if isinstance(rt, BoneTrack) and rt.slot is None
            else f"{entity_id}/{slot_node_path(desc, rt.slot)}"
        )
        if path not in vocab.paths:
            # Resolution mirrors the rig builder, so this is a bug in one of
            # the two rather than an authoring error — say which node.
            raise CutoutCompileError(
                f"play of {action.animation!r}: track {rt.track.target!r} "
                f"resolved to node {path!r}, which the built scene does not "
                f"carry (built: {sorted(p for p in vocab.paths if p.startswith(entity_id))})."
            )
        if isinstance(rt, BoneTrack):
            rest_value = float(getattr(vocab.node_transforms[path], rt.property))
            scale = rt.unit * (k if rt.rig_scaled else 1.0)
            if rt.track.type == "sine":
                kfs = [
                    KeyframeJSON(
                        time=t, value=rest_value + dev * scale, easing="linear"
                    )
                    for t, dev in sampled_deviations(rt.track, duration, fps)
                ]
            else:
                easing = "step" if rt.track.type == "step" else "linear"
                kfs = [
                    KeyframeJSON(
                        time=float(ft),
                        value=rest_value + float(fv) * scale,
                        easing=easing,
                    )
                    for ft, fv in rt.track.frames
                ]
            channels.append(
                ChannelJSON(target=path, property=rt.property, keyframes=kfs)
            )
        else:
            set_name = _face_set_for(vocab, entity_id, path, rt.set_name, view)
            if not {key for _, key in rt.frames} <= set(
                vocab.node_sets.get(path, {}).get(set_name) or {}
            ):
                set_name = rt.set_name  # the variant lacks a key: the base set
            channels.append(
                ChannelJSON(
                    target=path,
                    property=set_name,
                    keyframes=[
                        KeyframeJSON(time=t, value=key, easing="step")
                        for t, key in rt.frames
                    ],
                )
            )
    loop = action.loop if action.loop is not None else bool(anim.loop)
    return AnimationClipJSON(
        name=anim_id,
        duration=duration,
        loop_mode="loop" if loop else "once",
        channels=channels,
    )
