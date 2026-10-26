"""Body continuity: a prop that depicts a character's limbs must meet that character's body.

Two checks ``an validate`` runs, over every prop entity whose document declares a
``metadata.body_attachment`` (:mod:`cutan.body_attachment`):

``cutout.body_attachment``, once per shot, at the shot's start:

- **the character is there** when the art shows it from outside: a body part
  whose character is not on stage is a warning. ``first_person`` art (the camera
  IS the character) is the one view that needs the character OFF screen; with
  it on screen it is an error;
- **the view agrees**: the view the art declares is the character's view (a
  ``view`` set at the start, else its ``rest_view``, else ``front``). Art drawn
  from the driver's seat laid over a driver seen through the windscreen is this
  error;
- **the relation holds**, for a prop placed by hand (one placed without
  ``stage.at`` is derived by the ``body_placement`` pass and holds by
  construction): every socket lands within ``tolerance`` × the span between the
  sockets' bones of that bone; the prop's size relative to the character is the
  declared one within ``scale_tolerance``; the limbs are not crossed; a mirrored
  character carries a mirrored prop. The error says where the derivation puts it.

``cutout.body_attachment_consistency``, once per scene: the same prop on the
same character has the same size relative to the character, and the same anchor
on the body in the character's units, in every shot (the framings must not
drift apart at a cut).

Placements are the compiler's: the entity nodes of the shot's built stage
(:func:`an.motion.stage_poses`, built only when a shot holds a declaring prop),
with any ``set`` at the shot's start applied.

**Reported as ``info`` and not checked (v1):** the geometry while the
character is in a view other than its rest view (sockets are declared on the
rest view's bones; a side view moves and hides arms), a rotated prop or
character, a socket on a nested slot or a posed bone, art the store cannot
measure. **Motion during the shot** (cutan#98) is not measured here: when the
character moves, the ``body_placement`` pass lowers the sockets to ``pin``
joints (:func:`cutan.compile.body.body_attachment_pins`) and this check says,
with the time, when the motion pulls one off its bone (:func:`_follow_findings`). A **view change during the shot** (a ``set view`` or a played ``turn``) while a
prop drawn from the former view stays on is a warning with the time
(:func:`view_swap_findings`); the sockets are not followed through the new view.
**Not checked at all:** whether the
declaration is TRUE of the pixels: the sockets are the art author's statement
(a critic over probe frames is cutan#95).

>>> from an.ir.schema import Shot
>>> body_attachment_findings(Shot(id="s"), {})
[]
"""

from __future__ import annotations

import math
from typing import Any, Callable, Mapping

from an.verify.constraints import Constraint

from cutan.body_attachment import (
    BODY_ATTACHMENT_KEY,
    FIRST_PERSON,
    CrossedLimbs,
    NotChecked,
    derive_placement,
    body_attachment_of,
    bound_character,
    character_model,
    character_view,
    crossed_limbs_message,
    entity_pose,
    prop_art_size,
    prop_model,
    rest_view_of,
    solve_placement,
    start_state,
    view_changes,
)

__all__ = [
    "BODY_ATTACHMENT_CONSISTENCY",
    "body_attachment_findings",
    "check_body_attachments",
    "check_body_attachment_consistency",
    "consistency_findings",
    "view_swap_findings",
]

#: Where the per-shot check leaves its measurements for the scene-level one.
RECORDS_KEY: str = "cutout.body_attachment.records"

Finding = tuple[str, str, str]


def _declaring_props(shot: Any, props: Any) -> list[tuple[int, Any, Any]]:
    out = []
    for j, entity in enumerate(shot.entities):
        if entity.kind != "prop":
            continue
        try:
            raw = props[entity.ref] if entity.ref in props else None
        except Exception:  # noqa: BLE001 - an unreadable entry is another check's
            continue
        if not isinstance(raw, Mapping) or raw.get("kind") != "PropDescriptor":
            continue
        meta = raw.get("metadata")
        if isinstance(meta, Mapping) and meta.get(BODY_ATTACHMENT_KEY) is not None:
            out.append((j, entity, raw))
    return out


def body_attachment_findings(
    shot: Any,
    stores: Mapping[str, Any],
    *,
    poses: Mapping[str, Mapping[str, float]] | Callable[[], Any] | None = None,
    path: str = "",
    records: list | None = None,
    index: int | None = None,
) -> list[Finding]:
    """``[(severity, ir path, message)]`` for every body-depicting prop in ``shot``.

    ``stores`` are the project's stores by mall name (``props``, ``characters``);
    a prop or character whose store is absent is not checked. ``poses`` are the
    shot's built entity poses (:func:`an.motion.stage_poses`), or a function
    returning them (called only when a prop declares an attachment); ``None``
    reads placements off the entities' ``stage``, after deriving the placements
    the compiler derives. ``records``, when given, receives one measurement per
    checked prop for :func:`consistency_findings`. Never raises.
    """
    props = stores.get("props")
    if props is None:
        return []
    declaring = _declaring_props(shot, props)
    if not declaring:
        return []
    if callable(poses):
        try:
            poses = poses()
        except Exception:  # noqa: BLE001 - the stage did not build: another check says why
            poses = None
    unplaced = {
        e.id
        for e in shot.entities
        if e.kind == "prop" and (e.stage is None or e.stage.at is None)
    }
    original = shot
    if poses is None:
        from cutan.compile.body import derive_body_placements

        shot = derive_body_placements(shot, stores)
    sets = start_state(shot)
    out: list[Finding] = []
    for j, entity, raw in declaring:
        where = f"{path}/entities/{j}" if path else f"entities/{j}"
        entity = shot.entities[j]  # the derived placement, when there is one
        try:
            if entity.id in unplaced and _parses(raw):
                placed, why = derive_placement(original, original.entities[j], stores)
                if placed is None:
                    out.append(_not_derived(original, entity, raw, why, where))
                    continue
            out.extend(
                _check_one(
                    shot, entity, raw, stores, poses, sets, where, records, index
                )
            )
        except Exception as e:  # noqa: BLE001 - a crash here must not take `an validate` down
            out.append(
                (
                    "info",
                    where,
                    f"prop {entity.id!r}: body attachment not checked ({type(e).__name__}: {e})",
                )
            )
    return out


def _parses(raw) -> bool:
    try:
        body_attachment_of(raw)
        return True
    except Exception:  # noqa: BLE001 - malformed: `_check_one` reports it
        return False


def _not_derived(shot, entity, raw, why, where) -> Finding:
    """A body-attached prop without `stage.at` that could not be derived: the
    compiler draws it at the stage centre, which is wrong for any body. First-person
    art and an absent character are the per-shot check's findings instead."""
    from pydantic import ValidationError

    try:
        ba = body_attachment_of(raw)
    except ValidationError:
        ba = None
    if (
        ba is not None
        and ba.view != FIRST_PERSON
        and bound_character(shot, entity, ba)[0] is not None
    ):
        return (
            "error",
            where,
            f"prop {entity.id!r} has no `stage.at` and cannot be placed by its body: {why}. It would be drawn at the stage centre; fix that, or place it by hand (`set scale_x` negative for a mirrored character)",
        )
    if ba is not None and ba.view == FIRST_PERSON:
        return (
            "info",
            where,
            f"prop {entity.id!r}: first-person art is placed by hand, not by a body",
        )
    return (
        "warning",
        where,
        f"prop {entity.id!r} has no `stage.at` and cannot be placed by its body: {why}",
    )


def _check_one(
    shot, entity, raw, stores, poses, sets, where, records, index
) -> list[Finding]:
    from pydantic import ValidationError

    try:
        ba = body_attachment_of(raw)
    except ValidationError as e:
        err = e.errors()[0]
        return [
            (
                "error",
                where,
                f"prop {entity.ref!r}: its {BODY_ATTACHMENT_KEY} is malformed: {err['msg']} at {'.'.join(map(str, err['loc']))}",
            )
        ]
    who, name = bound_character(shot, entity, ba)
    label = f"prop {entity.id!r} (depicts {name or 'nobody'!r}'s body, seen {ba.view})"
    if not name:
        return [
            (
                "warning",
                where,
                f"{label}: no character is bound (declare `character`, or `overrides: {{body_of: <id>}}` on the entity)",
            )
        ]
    if who is None:
        if ba.view == FIRST_PERSON:
            return []
        return [
            (
                "warning",
                where,
                f"{label}: {name!r} is not on stage in this shot (or names several entities), so the limbs it shows belong to nobody",
            )
        ]
    chars = stores.get("characters")
    char = None
    if chars is not None and who.ref in chars:
        try:
            char = character_model(chars[who.ref])
        except Exception:  # noqa: BLE001 - a broken character is another check's
            char = None
    csets = sets.get(who.id, {})
    view = character_view(who, char, csets)
    if ba.view == FIRST_PERSON:
        return [
            (
                "error",
                where,
                f"{label}: first-person art (the camera is {name!r}) while {name!r} is on screen; draw it from the shot's camera ({view} view of {name!r})",
            )
        ]
    if char is None:
        return []
    found: list[Finding] = []
    if view != ba.view:
        found.append(
            (
                "error",
                where,
                f"{label}: {name!r} is in the {view!r} view in this shot, so the art shows the body from another side than the camera does; draw it in the {view!r} view",
            )
        )
        return found
    if not ba.sockets:
        return found
    if view != rest_view_of(char):
        return found + [
            (
                "info",
                where,
                f"{label}: sockets are checked in {name!r}'s rest view only ({rest_view_of(char)!r}), not {view!r}",
            )
        ]
    cpose = entity_pose(who, poses, csets)
    ppose = entity_pose(entity, poses, sets.get(entity.id, {}))
    if cpose is None or ppose is None:
        return found + [
            (
                "info",
                where,
                f"{label}: not placed with `stage.at` and not built, so its sockets were not checked",
            )
        ]
    if abs(ppose["rotation"]) > 1e-9:
        return found + [
            (
                "info",
                where,
                f"{label}: rotated at the shot's start, so its sockets were not checked",
            )
        ]
    if (cpose["scale_x"] < 0) != (ppose["scale_x"] < 0):
        return found + [
            (
                "error",
                where,
                f"{label}: {'the character is' if cpose['scale_x'] < 0 else 'the prop is'} mirrored and {'the prop is not' if cpose['scale_x'] < 0 else 'the character is not'}: mirror both (a negative `scale_x`) or neither",
            )
        ]
    mirror_x = None  # the character's x when both are mirrored
    if cpose["scale_x"] < 0:  # both mirrored: check the unmirrored configuration
        cx = mirror_x = cpose["x"]
        cpose = {**cpose, "scale_x": -cpose["scale_x"]}
        ppose = {**ppose, "x": 2 * cx - ppose["x"], "scale_x": -ppose["scale_x"]}
    props = stores["props"]
    try:
        got = solve_placement(
            prop_model(raw),
            char,
            ba,
            art_size=prop_art_size(props, entity.ref),
            character_pose=cpose,
        )
    except CrossedLimbs:
        return found + [("error", where, crossed_limbs_message(entity.ref, ba, name))]
    except NotChecked as e:
        return found + [("info", where, f"{label}: sockets not checked: {e}")]
    except ValueError as e:
        return found + [("error", where, f"{label}: {e}")]
    sx, sy = ppose["scale_x"], ppose["scale_y"]
    placed = [(ppose["x"] + sx * q[0], ppose["y"] + sy * q[1]) for q in got["local"]]
    limit = ba.tolerance * got["span_px"]
    off = [
        (s.bone, math.dist(a, b))
        for s, a, b in zip(ba.sockets, placed, got["targets"])
        if math.dist(a, b) > limit
    ]
    ratio = sx / got["scale"] - 1.0
    measured_scale = len(ba.sockets) > 1 or ba.scale is not None
    if mirror_x is not None:
        fix = f"Place it at [{2 * mirror_x - got['at'][0]:g}, {got['at'][1]:g}] with `set scale_x` {-got['scale']:.3g} at the start"
    else:
        fix = f"Leave out `stage.at` to have it placed by its body, or place it at [{got['at'][0]:g}, {got['at'][1]:g}] scale {got['scale']:.3g}"
    flagged = False
    if measured_scale and abs(ratio) > ba.scale_tolerance:
        flagged = True
        found.append(
            (
                "error",
                where,
                f"{label}: drawn {abs(ratio):.0%} {'larger' if ratio > 0 else 'smaller'} relative to {name!r} than its attachment says (at most {ba.scale_tolerance:.0%}). {fix}",
            )
        )
    if off:
        flagged = True
        worst = ", ".join(f"{bone} {d:.0f} px off" for bone, d in off)
        found.append(
            (
                "error",
                where,
                f"{label}: its limbs do not meet {name!r}'s body ({worst}; at most {limit:.0f} px, {ba.tolerance:g} of the {got['span_px']:.0f} px span). {fix}",
            )
        )
    if records is not None:
        cs = cpose["scale_x"]
        records.append(
            {
                "shot": index,
                "where": where,
                "prop": entity.ref,
                "character": who.ref,
                "ratio": sx / cs,
                "anchor": (
                    (ppose["x"] - cpose["x"]) / cs,
                    (ppose["y"] - cpose["y"]) / cpose["scale_y"],
                ),
                "span": got["span_px"] / cs,
                "tolerance": ba.tolerance,
                "scale_tolerance": ba.scale_tolerance,
                "flagged": flagged,
            }
        )
    return found


def consistency_findings(records: list[Mapping[str, Any]]) -> list[Finding]:
    """The same prop on the same character across shots: one finding per pair
    whose size relative to the character, or anchor on the body (in the
    character's units), differs between shots beyond the declaration's
    tolerances.

    >>> r = lambda shot, ratio, ax: {"shot": shot, "where": f"timeline/{shot}/entities/1",
    ...     "prop": "wheel", "character": "paul", "ratio": ratio, "anchor": (ax, 0.0),
    ...     "span": 50.0, "tolerance": 0.25, "scale_tolerance": 0.05}
    >>> consistency_findings([r(0, 0.43, 0.0), r(3, 0.43, 1.0)])
    []
    >>> [f[0] for f in consistency_findings([r(0, 0.43, 0.0), r(3, 0.52, 0.0)])]
    ['error']
    """
    groups: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    for rec in records:
        if rec.get("flagged"):
            continue  # already an error in its own shot
        groups.setdefault((rec["prop"], rec["character"]), []).append(rec)
    out: list[Finding] = []
    for (prop, char), recs in groups.items():
        if len(recs) < 2:
            continue
        lo, hi = (
            min(recs, key=lambda r: r["ratio"]),
            max(recs, key=lambda r: r["ratio"]),
        )
        tol = min(r["scale_tolerance"] for r in recs)
        if hi["ratio"] > lo["ratio"] * (1 + tol):
            out.append(
                (
                    "error",
                    hi["where"],
                    f"prop {prop!r} on {char!r}: its size relative to {char!r} is {hi['ratio']:.3g} in shot {hi['shot']} and {lo['ratio']:.3g} in shot {lo['shot']}: the framings drift apart at the cut. Leave out `stage.at` so every shot derives it from the body",
                )
            )
        limit = min(r["tolerance"] * r["span"] for r in recs)
        far = max(
            ((a, b) for a in recs for b in recs),
            key=lambda p: math.dist(p[0]["anchor"], p[1]["anchor"]),
        )
        if math.dist(far[0]["anchor"], far[1]["anchor"]) > limit:
            out.append(
                (
                    "error",
                    far[1]["where"],
                    f"prop {prop!r} on {char!r}: it sits at a different place on {char!r}'s body in shot {far[0]['shot']} and shot {far[1]['shot']} ({math.dist(far[0]['anchor'], far[1]['anchor']):.0f} units of {char!r}'s own size apart, at most {limit:.0f}). Leave out `stage.at` so every shot derives it from the body",
                )
            )
    return out


def check_body_attachments(ctx: Any) -> None:
    """The cut-out genre's per-shot body-continuity check (:func:`body_attachment_findings`)."""
    from cutan.characters.checks import _stage_poses_of

    if "props" not in ctx.stores:
        return
    records = ctx.memo.setdefault(RECORDS_KEY, [])
    for severity, where, message in body_attachment_findings(
        ctx.shot,
        ctx.stores,
        poses=lambda: _stage_poses_of(ctx, ctx.index, ctx.shot),
        path=ctx.path,
        records=records,
        index=ctx.index,
    ):
        ctx.report.add(severity, where, message)
    _follow_findings(ctx)
    for severity, where, message in view_swap_findings(
        ctx.shot, ctx.stores, path=ctx.path
    ):
        ctx.report.add(severity, where, message)


def view_swap_findings(
    shot: Any, stores: Mapping[str, Any], *, path: str = ""
) -> list[Finding]:
    """A character that changes view after the shot's start while a prop drawn
    from its former view stays on (cutan#98): the art no longer shows the body
    from the side the camera sees it, and the sockets are declared on the rest
    view. One warning per change, with the time, read off the timeline the
    compiler resolves (a played ``turn`` swaps at its own midpoint). A prop that
    changes its own look (alpha, a swap set) by then is the author's answer and
    is not warned about. Never raises.

    >>> from an.ir.schema import Shot
    >>> view_swap_findings(Shot(id="s"), {})
    []
    """
    from cutan.characters.checks import _turn_resolution
    from cutan.characters.play import facing_at

    props, chars = stores.get("props"), stores.get("characters")
    if props is None or chars is None or not _declaring_props(shot, props):
        return []
    try:
        resolved = _turn_resolution(shot, stores)
        if resolved is None:
            return []
        events = resolved[0].events
        changes = view_changes(events)
        out: list[Finding] = []
        for j, entity, raw in _declaring_props(shot, props):
            ba = body_attachment_of(raw)
            who, name = bound_character(shot, entity, ba)
            if who is None or ba.view == FIRST_PERSON or who.id not in changes:
                continue
            char = character_model(chars[who.ref]) if who.ref in chars else None
            current = character_view(
                who, char, {"view": facing_at(events, who.id, 0.0).view}
            )
            for time, view in changes[who.id]:
                if (
                    current == ba.view
                    and view != ba.view
                    and not _changes_own_look(events, entity.id, by=time)
                ):
                    where = f"{path}/entities/{j}" if path else f"entities/{j}"
                    out.append(
                        (
                            "warning",
                            where,
                            f"prop {entity.id!r} (depicts {name!r}'s body, seen {ba.view}): {name!r} "
                            f"changes to the {view!r} view at {time:.2f} s while the prop stays on, so "
                            f"from then the art shows the body from another side than the camera does. "
                            f"Swap the prop's drawing, or hide it (alpha), by then.",
                        )
                    )
                current = view
        return out
    except Exception:  # noqa: BLE001 - a broken play or declaration is another check's
        return []


def _changes_own_look(events: Any, prop_id: str, *, by: float) -> bool:
    """Whether the prop sets its own ``alpha`` or a swap set at or before ``by``."""
    from an.stage.compile import TRANSFORM_PROPERTIES

    for flat in events:
        a = flat.action
        target = str(getattr(a, "target", ""))
        prop = getattr(a, "property", None)
        if (
            target.split("/", 1)[0] == prop_id
            and flat.start <= by + 1e-6
            and (prop == "alpha" or (getattr(a, "kind", None) == "set" and prop not in TRANSFORM_PROPERTIES))
        ):
            return True
    return False


def _follow_findings(ctx: Any) -> None:
    """Motion during the shot (cutan#98, on the constraint layer): a prop placed by
    its body is followed through the shot by pins (:mod:`cutan.compile.body`); say
    when it cannot be (its sockets do not fit the bones) and when the motion pulls
    a pin off its bone, with the time. The pins are added at compile, so the core's
    joint checks do not see them: this reads the compiled shot's solve report."""
    from cutan.compile.body import why_not_followed

    mall = ctx.stores
    declaring = False
    for i, entity in enumerate(ctx.shot.entities):
        if entity.kind != "prop" or (
            entity.stage is not None and entity.stage.at is not None
        ):
            continue
        try:
            raw = mall["props"][entity.ref]
            if body_attachment_of(raw) is None:
                continue
            declaring = True
            why = why_not_followed(ctx.shot, entity, mall)
        except Exception:  # noqa: BLE001 - the per-shot check reports a broken declaration
            continue
        if why:
            ctx.report.add(
                "info" if "own" in why else "warning",
                f"{ctx.path}/entities/{i}",
                f"prop {entity.id!r} is placed by its body but not followed through the shot: {why}",
            )
    if not declaring:
        return
    from an.verify.constraints import compiled_shot

    doc = compiled_shot(ctx)
    report = ((doc.meta.extensions or {}).get("solve") or {}) if doc is not None else {}
    joints = report.get("joints") or []
    authored = len(ctx.shot.actions)
    for entry in report.get("dropped") or []:
        row = joints[entry["joint"]] if entry["joint"] < len(joints) else {}
        where = str(row.get("where", ""))
        if row.get("source") != "pin" or not where.startswith("actions/"):
            continue
        if int(where.split("/")[1]) < authored:
            continue  # an authored pin: unreachable_pin reports it
        ctx.report.add(
            "warning",
            f"{ctx.path}/{where}",
            f"a body-attached prop's socket ({row.get('bodies')}) cannot stay on its bone from "
            f"{entry['from']:.2f} s to {entry['until']:.2f} s (it stays {entry['gap']:.1f} px off): "
            "the character's motion carries the bone out of the prop's reach. Move less, or "
            "tween the prop yourself (a prop with motion of its own is not followed).",
        )


def check_body_attachment_consistency(ctx: Any) -> None:
    """The cut-out genre's cross-shot body-continuity check (:func:`consistency_findings`).

    It reads the measurements ``cutout.body_attachment`` leaves in the
    validation's memo, so the two must be selected together (``only=``)."""
    for severity, where, message in consistency_findings(
        ctx.memo.get(RECORDS_KEY) or []
    ):
        ctx.report.add(severity, where, message)


#: The cross-shot check as a constraint on the shared interface (cutan#104,
#: an#508): size conservation of a body-attached prop against its character.
#: Lint-only (no solver term): the placement is derived from the character in
#: every shot, so a drift can only come from a hand placement. The persisted
#: name is the check's, unchanged.
BODY_ATTACHMENT_CONSISTENCY = Constraint(
    "cutout.body_attachment_consistency",
    check_body_attachment_consistency,
    stage="finish",
    order=11,
    description=(
        "a body-attached prop keeps its size and place relative to its "
        "character across shots"
    ),
)
