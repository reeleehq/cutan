"""The cut-out genre's semantic checks: `play`, `expression`, turns, views and character refs.

Moved from ``an.ir.validate`` (an#225, an#246): the core's validator runs whatever checks a genre registers
(:data:`cutan.genre.CUTOUT`), and these are the cut-out ones.
"""

from __future__ import annotations


from typing import Any, Mapping

from pydantic import ValidationError

from cutan.characters.play import (
    GAIT_ARG,
    PRESET_SOURCE,
    Facing,
    TurnResolution,
    art_exists_for,
    facing_at,
    play_extent_for,
    play_problems,
    play_source,
    preset_moved_nodes,
    preset_play_span,
    preset_takes,
    preset_target_problems,
    resolve_turns,
    slot_node_path,
    swap_art_missing,
    swap_slots,
)
from cutan.characters.schema import DFLT_VIEW, VIEW_CHANNEL, CharacterDescriptor
from cutan.expression.binding import expression_problems
from an.ir.compose import flatten
from an.ir.migrate import migrate
from an.ir.schema import SceneIR

from an.ir.validate import (  # noqa: E402
    ValidationContext,
    ValidationReport,
    _built_node_paths,
    _rig_document,
    _rig_scope,
    _text_ids,
)


def _stage_of(shot, stores: Mapping[str, Any], unchecked: set[str] = frozenset()):
    """``() -> {node path: rest pose}`` of the shot's built stage
    (:func:`an.motion.stage_poses`), built once, lazily, and ``None`` when it
    does not build (reported by the play check). What the compiler reads a
    walk's drawn scale and limbs off (``vocab.node_transforms``), so validate
    reads the same numbers (cutan#12). Entities whose store was not supplied
    (``unchecked``) are left out of the build: they are not checked, and they
    must not take the others' context with them (review C, F1)."""
    cache: dict[str, Any] = {}

    def poses() -> Mapping[str, Mapping[str, float]] | None:
        if "poses" not in cache:
            from an.motion import stage_poses

            staged = shot
            if unchecked:
                staged = shot.model_copy(
                    update={
                        "entities": [e for e in shot.entities if e.id not in unchecked]
                    }
                )
            try:
                cache["poses"] = stage_poses(staged, mall=stores)
            except Exception:  # the stage did not build: `cutout.play` says why
                cache["poses"] = None
        return cache["poses"]

    return poses


def _preset_context_of(
    rigs: Mapping[str, Any],
    unchecked: set[str],
    stores: Mapping[str, Any],
    stage: Any,
):
    """``(entity_id, play) -> PresetContext`` for validate's extent resolver:
    what :func:`cutan.compile.passes.preset_context_of` reads off the compiler's
    vocabulary, read off the same built stage (``stage``: :func:`_stage_of`)
    — the target's built scale and limbs — and the same descriptor and art,
    so validate places a ``sequence``'s later siblings where compile does
    (cutan#12). No context for an entity whose store was not supplied
    (``unchecked``: the check did not run) or a target the stage did not
    build."""
    from cutan.characters.methods import (
        CHARACTER_KIND,
        compile_profile,
        walk_preset_context,
    )

    memo: dict[str, tuple[Any, Any]] = {}

    def descriptor_and_profile(entity_id: str, entity) -> tuple[Any, Any]:
        if entity_id not in memo:
            descriptor = profile = None
            if entity.kind == CHARACTER_KIND:
                doc = _rig_document(entity, stores)
                try:
                    descriptor = (
                        CharacterDescriptor.model_validate(doc) if doc else None
                    )
                except ValidationError:
                    descriptor = None  # reported by the play check
            if descriptor is not None:
                store = stores.get(entity.store) if entity.store else None
                art = art_exists_for(store, entity.ref) if store is not None else None
                profile = compile_profile(descriptor, art_exists=art)
            memo[entity_id] = (descriptor, profile)
        return memo[entity_id]

    def context(entity_id: str, action) -> Mapping[str, Any] | None:
        target = getattr(action, "target", "") or ""
        entity = rigs.get(entity_id)
        if entity_id in unchecked or not preset_takes(action.animation, GAIT_ARG):
            return None
        poses = stage()
        if poses is None or target not in poses:
            return None
        # A character resolves on the registry; a part of one, a prop, or any
        # other built entity walks with the limbs the stage built under the
        # target (as the compiler's does off the registry).
        is_character = entity is not None and entity.kind == CHARACTER_KIND
        descriptor, profile = (
            descriptor_and_profile(entity_id, entity)
            if "/" not in target and is_character
            else (None, None)
        )
        if profile is None and is_character and "/" not in target:
            prefix = f"{target}/"
            profile = compile_profile(
                None,
                built_parts=[p[len(prefix) :] for p in poses if p.startswith(prefix)],
            )
        prefix = f"{target}/"
        return walk_preset_context(
            target,
            dict(action.args or {}),
            descriptor=descriptor,
            profile=profile,
            scale=abs(float(poses[target]["scale_y"])),
            parts=None
            if profile is not None
            else [p[len(prefix) :] for p in poses if p.startswith(prefix)],
        )

    return context


def _check_play_actions(
    shot, path: str, report: "ValidationReport", stores: Mapping[str, Any]
) -> None:
    """A `play` must resolve against its target's descriptor animations, or a
    motion preset — checked HERE, before the author pays for TTS or a Chromium
    launch, because compile raises (an#7, an#166). The cut-out genre's check
    (registered by :mod:`cutan.genre`); with no stores it does not run, so
    a bare `validate_semantic(scene)` passes a play the compiler will refuse.
    """
    if not stores:
        return
    rigs, unchecked = _rig_scope(shot, stores)
    # `play` (an#7): resolved against the target entity's MIGRATED descriptor
    # by `cutan.characters.play` — the SAME code the compiler resolves with, so
    # validate's verdict is compile's (an unknown bone property, a bone with
    # no slot of its own, art missing for a frame, a face slot suppressed by
    # `face_overlay=false` all used to pass here and raise there). Art is
    # checked when the store has a filesystem root; a dict store assumes
    # presence, as the compiler's part probe does.
    #
    # A name the descriptor does not declare — or any name on an entity with
    # no descriptor — falls back to a motion preset (an#166), decided by the
    # same `play_problems`. A preset additionally needs the node it moves to
    # be BUILT, which only the compiler's scene builder knows: the stage is
    # built once per shot, lazily, and only when a preset play is present.
    stage_nodes: set[str] | None = None
    stage_tried = False

    def play_descriptor(entity_id: str) -> CharacterDescriptor | None:
        # `play` resolves against a CHARACTER's animations. A prop has an
        # `animations` field so the shared rig builder can read the same
        # attribute on either document, but nothing seeds it and no author
        # tool writes one — so a `play` on a prop resolves presets only,
        # exactly as the compiler (which reads character descriptors
        # alone) resolves it.
        entity = rigs.get(entity_id)
        doc = _rig_document(entity, stores) if entity is not None else None
        is_character = entity is not None and entity.kind == "character"
        return (
            CharacterDescriptor.model_validate(doc)
            if doc is not None and is_character
            else None
        )

    def extent_descriptor(entity_id: str) -> CharacterDescriptor | None:
        # Only to place a `sequence`'s later siblings, exactly as the compiler
        # does; a descriptor that will not even parse is reported by the loop
        # below, so it must not raise from inside `flatten`.
        if entity_id in unchecked:
            return None
        try:
            return play_descriptor(entity_id)
        except ValidationError:
            return None

    preset_context = _preset_context_of(
        rigs, unchecked, stores, _stage_of(shot, stores, unchecked)
    )
    play_extent = play_extent_for(extent_descriptor, context_of=preset_context)
    for k, action in enumerate(shot.actions):
        for flat in flatten(action, play_extent=play_extent):
            leaf = flat.action
            if getattr(leaf, "kind", None) != "play":
                continue
            entity_id = (getattr(leaf, "target", "") or "").split("/", 1)[0]
            if entity_id in unchecked:
                continue
            entity = rigs.get(entity_id)
            is_character = entity is not None and entity.kind == "character"
            desc = play_descriptor(entity_id)
            problems = preset_target_problems(
                leaf.animation, leaf.target
            ) + play_problems(
                desc,
                leaf.animation,
                art_exists=(
                    art_exists_for(stores.get("characters"), entity.ref)
                    if is_character
                    else None
                ),
                args=leaf.args,
                duration=leaf.duration,
                speed=leaf.speed,
                loop=leaf.loop,
            )
            if not problems and play_source(desc, leaf.animation) == PRESET_SOURCE:
                if not stage_tried:
                    stage_tried = True
                    stage_nodes, why = _built_node_paths(shot, stores)
                    if why is not None:
                        # Said out loud, never a silent pass: validate could
                        # not see what compile will look the node up in.
                        report.add(
                            "warning",
                            f"{path}/actions/{k}",
                            "the node a motion-preset `play` moves was NOT "
                            f"checked: the shot's stage did not build ({why}).",
                        )
                end = flat.start + preset_play_span(
                    leaf, preset_context(entity_id, leaf)
                )
                if end > shot.duration + 1e-9:
                    report.add(
                        "warning",
                        f"{path}/actions/{k}",
                        f"`play` of motion preset {leaf.animation!r} on "
                        f"{entity_id!r} runs to t={end:g}s, past the shot's end "
                        f"({shot.duration:g}s): the rest of the move never shows.",
                    )
                if stage_nodes is not None:
                    prefix = f"{leaf.target}/"
                    moved = preset_moved_nodes(
                        leaf.target,
                        leaf.animation,
                        leaf.args,
                        parts=[
                            p[len(prefix) :]
                            for p in stage_nodes
                            if p.startswith(prefix)
                        ],
                    )
                    missing = [n for n in moved if n not in stage_nodes]
                    if missing:
                        built = sorted(
                            p for p in stage_nodes if p.split("/")[0] == entity_id
                        )
                        problems = [
                            f"motion preset {leaf.animation!r} moves node {n!r}, "
                            f"which the built scene does not carry (built: {built})"
                            for n in missing
                        ]
            for problem in problems:
                report.add(
                    "error",
                    f"{path}/actions/{k}",
                    f"`play` of {leaf.animation!r} on {entity_id!r} cannot "
                    f"resolve: {problem} — compiling this shot raises.",
                )


def _check_expression_actions(
    shot, path: str, report: "ValidationReport", stores: Mapping[str, Any]
) -> None:
    """An `expression` and a dialogue `[emotion]` must resolve (an#98) — the
    cut-out genre's check (registered by :mod:`cutan.genre`). CHARACTER
    entities only: a prop has no face."""
    if not stores:
        return
    refs_by_entity = {e.id: e.ref for e in shot.entities if e.kind == "character"}
    available_characters = stores.get("characters")
    # `expression` (an#98) and the dialogue `[emotion]` sugar resolve through
    # `cutan.expression.binding.expression_problems` — the SAME function the face
    # solver raises with. An unknown preset used to be silence.
    for k, action in enumerate(shot.actions):
        for flat in flatten(action):
            leaf = flat.action
            if getattr(leaf, "kind", None) != "expression":
                continue
            entity_id = (getattr(leaf, "target", "") or "").split("/", 1)[0]
            if entity_id not in refs_by_entity:
                report.add(
                    "error",
                    f"{path}/actions/{k}",
                    f"`expression` targets {entity_id!r}, which is not a character "
                    f"entity of this shot (entities: {sorted(refs_by_entity) or 'none'}) "
                    "— it would compile to nothing.",
                )
                continue
            desc = _descriptor_for(refs_by_entity.get(entity_id), available_characters)
            for problem in expression_problems(
                desc, preset=leaf.preset, axes=leaf.axes, who=entity_id
            ):
                report.add(
                    "error",
                    f"{path}/actions/{k}",
                    f"`expression` on {entity_id!r} cannot resolve: {problem} — "
                    "compiling this shot raises.",
                )
    for j, line in enumerate(shot.dialogue):
        emotion = (line.emotion or "").strip().lower()
        if not emotion:
            continue
        desc = _descriptor_for(refs_by_entity.get(line.speaker), available_characters)
        for problem in expression_problems(None, preset=emotion, who=line.speaker):
            report.add("error", f"{path}/dialogue/{j}/emotion", problem)
        if desc is not None and not desc.face_overlay:
            report.add(
                "warning",
                f"{path}/dialogue/{j}/emotion",
                f"{line.speaker!r} has its face baked into the head art "
                "(face_overlay: false), so the [emotion] on this line moves "
                "nothing; the audio still plays.",
            )


def _check_whole_character_swap(
    action,
    desc: Mapping[str, Any],
    prop: str,
    keys: Mapping[str, str],
    entity_id: str,
    *,
    where: str,
    report: "ValidationReport",
    art_exists,
) -> None:
    """A swap-set action on a character's ROOT, judged the way compile judges
    it (an#201). A ``set`` lands on every slot the set projects onto
    (:func:`~cutan.characters.play.swap_slots`), so each key's art must be there
    on EVERY one of them (:func:`~cutan.characters.play.swap_art_missing`) —
    "some slot has it" passed a key ``--strict-assets`` then refused. A
    ``tween`` is not fanned out: compile names the nodes that carry the set,
    and so does this.
    """
    try:
        cdesc = CharacterDescriptor.model_validate(desc)
    except ValidationError:
        return  # reported where the descriptor is loaded
    nodes = []
    for slot in swap_slots(cdesc, prop, art_exists=art_exists):
        try:
            nodes.append(f"{entity_id}/{slot_node_path(cdesc, slot)}")
        except KeyError:
            continue  # `an character validate` names the slot
    if getattr(action, "kind", None) == "tween":
        if not nodes:
            return  # no node carries the set: compile drops it, recording why
        report.add(
            "error",
            where,
            f"a `tween` of {prop!r} on the whole character {entity_id!r}: the "
            f"{prop!r} set resolves on {nodes}, not on that node — compiling "
            "this shot raises. A whole-character swap is a `set` (it lands on "
            "all of them at one instant); a `tween` targets one of those nodes.",
        )
        return
    values = [
        v
        for v in (
            getattr(action, "value", None),
            getattr(action, "from_value", None),
            getattr(action, "to_value", None),
        )
        if v is not None
    ]
    for v in values:
        if not isinstance(v, str) or v not in keys:
            report.add(
                "error",
                where,
                f"{v!r} is not a declared key of the {prop!r} set of "
                f"{entity_id!r} (it has: {sorted(keys)}) — compiling this shot "
                "raises.",
            )
            continue
        if art_exists is None:
            continue  # a store with no filesystem root assumes presence
        missing = swap_art_missing(cdesc, prop, v, art_exists)
        if missing:
            report.add(
                "error",
                where,
                f"setting {prop!r} to {v!r} on {entity_id!r} swaps every slot "
                f"that carries it ({nodes}), but its art is not on disk for "
                f"all of them: {missing} — the render draws those slots "
                "unswapped, and `--strict-assets` refuses the shot.",
            )


def _turn_resolution(
    shot, stores: Mapping[str, Any]
) -> tuple[TurnResolution, list[int]] | None:
    """The shot's flat timeline with its turns resolved the way the compiler
    resolves them (:func:`cutan.characters.play.resolve_turns`, an#203), and the
    top-level action index each flat came from. ``None`` without a characters
    store — the check did not run, which is not the same as passing.

    The rest pose is the identity: validate builds no stage. A facing is only
    the SIGN of ``scale_x``, so this is exact unless a character is staged
    mirrored and a preset settles it back to its rest — then validate reads
    it facing right where compile has it facing left (a known, narrow gap).
    """
    if stores.get("characters") is None:
        return None
    rigs = {e.id: e for e in shot.entities if e.kind == "character"}

    def descriptor_of(entity_id: str) -> CharacterDescriptor | None:
        entity = rigs.get(entity_id)
        doc = _rig_document(entity, stores) if entity is not None else None
        try:
            return CharacterDescriptor.model_validate(doc) if doc else None
        except ValidationError:
            return None  # reported by the play check

    all_rigs, unchecked = _rig_scope(shot, stores)
    extent = play_extent_for(
        descriptor_of,
        context_of=_preset_context_of(
            all_rigs, unchecked, stores, _stage_of(shot, stores, unchecked)
        ),
    )
    origin: list[int] = []
    flats = []
    for k, action in enumerate(shot.actions):
        for flat in flatten(action, play_extent=extent):
            flats.append(flat)
            origin.append(k)
    resolution = resolve_turns(
        flats,
        descriptor_of=descriptor_of,
        rest_of=lambda _p: {
            "x": 0.0,
            "y": 0.0,
            "rotation": 0.0,
            "scale_x": 1.0,
            "scale_y": 1.0,
            "alpha": 1.0,
        },
    )
    return resolution, origin


def _check_turns(shot, path: str, report: "ValidationReport", resolved) -> None:
    """A ``turn`` whose declared ``from_direction`` contradicts the side the
    timeline before it left the character facing (an#203): the compiler
    keeps what the author wrote, so the character flips to the other side
    before it squashes — a visible jump."""
    if resolved is None:
        return
    resolution, origin = resolved
    for turn in resolution.turns:
        if not turn.contradicted:
            continue
        report.add(
            "warning",
            f"{path}/actions/{origin[turn.index]}",
            f"`turn` on {turn.entity!r} at t={turn.start:g}s declares "
            f"from_direction {turn.declared!r}, but the timeline before it left "
            f"{turn.entity!r} facing {turn.before.direction!r}"
            + (f" in its {turn.before.view!r} view" if turn.before.view else "")
            + ", so it jumps to the other side before it turns. Drop "
            "`from_direction`: a turn infers it from the timeline.",
        )


def _check_hidden_mouth_while_speaking(
    shot, path: str, report: "ValidationReport", resolved, stores: Mapping[str, Any]
) -> None:
    """A line spoken while the speaker's view HIDES its mouth (an#220): the
    view's ``swap_poses`` sets the mouth slot's ``alpha`` to 0 — the back
    view does, and so did every profile carved with the mouth baked in — so
    the audio plays over a face with no lip-sync. A warning, since a line
    delivered over the shoulder can be meant; the fix for a profile is a
    per-view mouth set (``viseme@side``) instead of the hide.
    """
    if resolved is None:
        return
    from an.ir.schema import SetAction

    events = resolved[0].events
    rigs = {e.id: e for e in shot.entities if e.kind == "character"}
    for k, line in enumerate(shot.dialogue or ()):
        entity = rigs.get(line.speaker)
        if entity is None or line.start is None:
            continue
        doc = _rig_document(entity, stores)
        try:
            desc = CharacterDescriptor.model_validate(doc) if doc else None
        except ValidationError:
            continue
        if desc is None or not desc.face_overlay:
            continue
        skin = desc.skins.get("default") or next(iter(desc.skins.values()), None)
        mouth_names = set((desc.asset_sets.get("viseme") or {}).values())
        mouths = {
            slot
            for slot, attachments in (skin.slots.items() if skin else ())
            if mouth_names & set(attachments)
        }
        start = float(line.start)
        end = start + float(line.duration or 0.0)
        views = [facing_at(events, line.speaker, start).view or desc.rest_view]
        views += [
            f.action.value
            for f in events
            if isinstance(f.action, SetAction)
            and f.action.target == line.speaker
            and f.action.property == VIEW_CHANNEL
            and start < f.start <= end
        ]
        poses = desc.swap_poses.get(VIEW_CHANNEL) or {}
        for view in dict.fromkeys(v for v in views if v is not None):
            hidden = sorted(
                m for m in mouths if (p := poses.get(view, {}).get(m)) and p.alpha == 0
            )
            if not hidden:
                continue
            report.add(
                "warning",
                f"{path}/dialogue/{k}",
                f"{line.speaker!r} speaks this line while its {view!r} view hides "
                f"its mouth ({', '.join(hidden)}: swap_poses.{VIEW_CHANNEL}.{view} "
                "alpha 0), so the line plays with no lip-sync on screen. "
                + (
                    "Turn before the line if the face should be seen."
                    if view == "back"
                    else f"Give the view its own mouth (a `viseme@{view}` set) "
                    "instead of hiding it, or turn before the line."
                ),
            )


def _check_view_continuity(
    scene: SceneIR, report: "ValidationReport", resolved: list
) -> None:
    """A character that ends one shot turned (a view other than the default,
    or facing left) and appears in the very next shot starts that shot at its rest
    — shots are independent by design (each compiles alone; the per-shot
    archive and `render_project` depend on it), so a view does not carry
    across a cut (an#203). Said as a warning, with the one line that carries
    it on; the next shot setting the view (or ``scale_x``) at t=0 is taken as
    the author's decision either way. ``resolved`` is
    :func:`_turn_resolution` per shot.
    """
    previous: dict[str, tuple[str, Facing]] = {}
    for i, (shot, shot_resolved) in enumerate(zip(scene.timeline, resolved)):
        if shot_resolved is None:
            return  # no characters store: the check did not run
        events = shot_resolved[0].events
        ids = [e.id for e in shot.entities if e.kind == "character"]
        for entity_id in ids:
            if entity_id not in previous:
                continue
            prev_shot, ended = previous[entity_id]
            start = facing_at(events, entity_id, 0.0)
            turned_view = ended.view not in (None, DFLT_VIEW) and start.view is None
            turned_left = ended.direction == "left" and start.direction is None
            if not (turned_view or turned_left):
                continue
            state = " ".join(
                bit
                for bit in (
                    f"in its {ended.view!r} view" if turned_view else "",
                    "facing left" if turned_left else "",
                )
                if bit
            )
            fix = " and ".join(
                bit
                for bit in (
                    f"`{{kind: set, target: {entity_id}, property: view, value: "
                    f"{ended.view}, at: 0}}`"
                    if turned_view
                    else "",
                    "a negative `scale_x` set at 0" if turned_left else "",
                )
                if bit
            )
            report.add(
                "warning",
                f"timeline/{i}/entities",
                f"{entity_id!r} ends shot {prev_shot!r} {state}, and shot "
                f"{shot.id!r} starts it at its rest — a view does not carry "
                f"across a cut (each shot compiles alone). To continue the "
                f"turn, open shot {shot.id!r} with {fix}; to reset it on "
                "purpose, set the view there anyway.",
            )
        previous = {
            e: (shot.id, facing_at(events, e, float(shot.duration))) for e in ids
        }


def _descriptor_for(ref, available_characters) -> CharacterDescriptor | None:
    """The MIGRATED descriptor a store holds for ``ref``, or ``None``."""
    if ref is None or available_characters is None:
        return None
    try:
        candidate = available_characters[ref]
    except (KeyError, TypeError):
        return None
    if isinstance(candidate, dict) and candidate.get("kind") == "CharacterDescriptor":
        return CharacterDescriptor.model_validate(
            migrate(dict(candidate), kind="CharacterDescriptor")
        )
    return None


#: Entity kinds whose missing ref is NOT an error, because the compiler draws
#: a placeholder rig instead: the cut-out genre's `character`, reported by its
#: own check (:func:`check_character_refs`). P8 moves this with the genre.
_PLACEHOLDER_RIG_KINDS: frozenset[str] = frozenset({"character"})


def check_character_refs(ctx: ValidationContext) -> None:
    """The cut-out genre's missing-character warning. A WARNING: the compiler
    falls back to the built-in placeholder rig and the scene still renders.
    Deliberately not escalated — an asset-less project rendering placeholders
    is a supported way to work."""
    store = ctx.stores.get("characters")
    if store is None:
        return  # store not supplied → this check did not run
    text_ids = _text_ids(ctx)
    for j, entity in enumerate(ctx.shot.entities):
        if entity.kind != "character" or entity.id in text_ids:
            continue
        if entity.ref not in store:
            ctx.report.add(
                "warning",
                f"{ctx.path}/entities/{j}",
                f"character ref {entity.ref!r} not in characters store",
            )


def _turns_of(ctx: ValidationContext, index: int, shot: Any):
    return ctx.cached(("turns", index), lambda: _turn_resolution(shot, ctx.stores))


def _stage_poses_of(ctx: ValidationContext, index: int, shot: Any):
    """The shot's built stage poses (:func:`_stage_of`), once per shot across
    the checks that read them; ``None`` when the stage does not build."""
    _, unchecked = _rig_scope(shot, ctx.stores)
    return ctx.cached(("stage", index), _stage_of(shot, ctx.stores, unchecked))


def check_play_actions(ctx: ValidationContext) -> None:
    """The cut-out genre's `play` check (:func:`_check_play_actions`)."""
    _check_play_actions(ctx.shot, ctx.path, ctx.report, ctx.stores)


def check_expression_actions(ctx: ValidationContext) -> None:
    """The cut-out genre's `expression` / `[emotion]` check."""
    _check_expression_actions(ctx.shot, ctx.path, ctx.report, ctx.stores)


def check_turns(ctx: ValidationContext) -> None:
    """The cut-out genre's contradicted-turn warning (:func:`_check_turns`)."""
    _check_turns(ctx.shot, ctx.path, ctx.report, _turns_of(ctx, ctx.index, ctx.shot))


def check_hidden_mouth_while_speaking(ctx: ValidationContext) -> None:
    """The cut-out genre's mouth-hidden-by-a-view warning."""
    _check_hidden_mouth_while_speaking(
        ctx.shot,
        ctx.path,
        ctx.report,
        _turns_of(ctx, ctx.index, ctx.shot),
        ctx.stores,
    )


def check_view_continuity(ctx: ValidationContext) -> None:
    """The cut-out genre's view-across-a-cut warning (:func:`_check_view_continuity`)."""
    resolved = [_turns_of(ctx, i, shot) for i, shot in enumerate(ctx.scene.timeline)]
    _check_view_continuity(ctx.scene, ctx.report, resolved)


class CharacterSwapChecks:
    """The ``character`` entity kind's swap-reference checks (``EntityKind.swap_checks``)."""

    @staticmethod
    def missing_set_hint(prop: str) -> str:
        """What to add to "names no declared asset set" for a missing ``view`` set."""
        if prop == VIEW_CHANNEL:
            return (
                " A character made before an#197 has no views: "
                "`an character add-views` draws them."
            )
        return ""

    @staticmethod
    def whole_entity(
        action, desc, prop, keys, entity_id, *, where, report, art_exists
    ) -> bool:
        """A swap on the character ITSELF is judged slot by slot (an#197, an#201)."""
        _check_whole_character_swap(
            action,
            desc,
            prop,
            keys,
            entity_id,
            where=where,
            report=report,
            art_exists=art_exists,
        )
        return True
