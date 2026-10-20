"""Body continuity: a prop that depicts a character's limbs must meet that character's body.

The check ``an validate`` runs on every shot (``cutout.body_attachment``), over
every prop entity whose document declares a ``metadata.body_attachment``
(:mod:`cutan.body_attachment`). For each, at the start of the shot:

- **the character is there** when the art shows it from outside: a
  ``front``/``three_quarter``/``side``/``back`` body part with no body on stage
  is a warning; ``first_person`` art (seen through the character's own eyes) is
  the one view that needs the character OFF screen, and with it on screen it
  is an error;
- **the view agrees**: the view the art declares is the view the character is
  in (its ``rest_view``, else ``front``, as set by any ``view`` swap at the
  shot's start). Art drawn from the driver's seat laid over a driver seen
  through the windscreen is exactly this error;
- **every socket meets its bone**: each socket, mapped to the stage through the
  prop's placement, lands within ``tolerance`` × the span between the sockets'
  bones of that bone, mapped through the character's placement; and the limbs
  are not crossed (the art's left limb meeting the body's right). The error
  says where :func:`cutan.body_attachment.place_body_prop` would put the prop.

Placements are the compiler's own: the entity nodes of the shot's built stage
(:func:`an.motion.stage_poses`, shared with the ``play`` check), with any
``set`` of ``x``/``y``/``scale_x``/``scale_y``/``rotation`` at the shot's start
applied. **Not checked (v1):** motion during the shot (a bob, a turn), a
socket on a nested slot, a character in ``nesting: bones`` whose shoulders sit
under a rotated parent, and whether the declaration is TRUE of the pixels:
that a drawing's sleeves really end where its sockets say is the art's author's
statement (the optional critics in ``misc/docs`` measure it).

>>> from an.ir.schema import Shot
>>> body_attachment_findings(Shot(id="s"), {})
[]
"""

from __future__ import annotations

import math
from typing import Any, Callable, Mapping

from pydantic import ValidationError

from cutan.body_attachment import (
    BODY_ATTACHMENT_KEY,
    FIRST_PERSON,
    body_attachment_of,
    character_model,
    crossed_limbs_message,
    fit_placement,
    prop_model,
    socket_pairs,
)

__all__ = ["body_attachment_findings", "check_body_attachments"]

#: The root-node properties a ``set`` at the shot's start overrides.
_POSE_KEYS: tuple[str, ...] = ("x", "y", "scale_x", "scale_y", "rotation")

#: A ``set`` at or before this time (seconds) counts as the shot's start.
_START_EPS: float = 1e-6


def _start_sets(shot: Any) -> dict[str, dict[str, Any]]:
    """``{entity id: {property: value}}`` from the ``set`` actions at the shot's start."""
    from an.motion import flatten

    out: dict[str, dict[str, Any]] = {}
    for action in getattr(shot, "actions", None) or []:
        try:
            leaves = flatten(action)
        except Exception:  # noqa: BLE001 - an unresolvable action is another check's
            continue
        for leaf in leaves:
            a = leaf.action
            if getattr(a, "kind", None) != "set" or leaf.start > _START_EPS:
                continue
            target = str(a.target)
            if "/" in target:
                continue  # a part, not the entity's own node
            out.setdefault(target, {})[a.property] = a.value
    return out


def _entity_pose(
    entity: Any, poses: Mapping[str, Mapping[str, float]] | None, sets: Mapping[str, Any]
) -> dict[str, float] | None:
    """The entity node's pose at the shot's start, or ``None`` when unknown."""
    if poses is not None and entity.id in poses:
        pose = dict(poses[entity.id])
    elif entity.stage is not None and entity.stage.at is not None:
        s = float(entity.stage.scale)
        pose = {"x": entity.stage.at[0], "y": entity.stage.at[1], "scale_x": s, "scale_y": s}
    else:
        return None
    for key in _POSE_KEYS:
        if key in sets:
            try:
                pose[key] = float(sets[key])
            except (TypeError, ValueError):
                pass
    return pose


def _art_size_of(store: Any, ref: str) -> Callable[[str], Any]:
    from an.stage.rig import PROP_ART_PREFIX, art_src, part_probe

    probe = part_probe(store, art_prefix=PROP_ART_PREFIX)

    def size(path: str):
        if probe is None:
            return None
        return probe(art_src(ref, path, art_prefix=PROP_ART_PREFIX))[1]

    return size


def _find_character(shot: Any, name: str) -> Any:
    chars = [e for e in shot.entities if e.kind == "character"]
    return next((e for e in chars if e.id == name), None) or next(
        (e for e in chars if e.ref == name), None
    )


def _span(points: list[tuple[float, float]]) -> float:
    return max((math.dist(a, b) for a in points for b in points), default=0.0)


def body_attachment_findings(
    shot: Any,
    stores: Mapping[str, Any],
    *,
    poses: Mapping[str, Mapping[str, float]] | None = None,
    path: str = "",
) -> list[tuple[str, str, str]]:
    """``[(severity, ir path, message)]`` for every body-depicting prop in ``shot``.

    ``stores`` are the project's stores by mall name (``props``, ``characters``);
    a prop or character whose store is absent is not checked. ``poses`` are the
    shot's built entity poses (:func:`an.motion.stage_poses`); ``None`` reads the
    placements off the entities' ``stage`` (an entity in the default layout is
    then not checked).
    """
    props, chars = stores.get("props"), stores.get("characters")
    if props is None:
        return []
    out: list[tuple[str, str, str]] = []
    sets = _start_sets(shot)
    for j, entity in enumerate(shot.entities):
        if entity.kind != "prop" or entity.ref not in props:
            continue
        where = f"{path}/entities/{j}" if path else f"entities/{j}"
        try:
            raw = props[entity.ref]
        except KeyError:
            continue
        if not isinstance(raw, Mapping) or raw.get("kind") != "PropDescriptor":
            continue
        try:
            ba = body_attachment_of(raw)
        except ValidationError as e:
            out.append(("error", where, f"prop {entity.ref!r}: its {BODY_ATTACHMENT_KEY} is malformed: {e.errors()[0]['msg']} at {'.'.join(map(str, e.errors()[0]['loc']))}"))
            continue
        if ba is None:
            continue
        out.extend(
            _check_one(shot, entity, raw, ba, props=props, chars=chars, poses=poses, sets=sets, where=where)
        )
    return out


def _check_one(shot, entity, raw, ba, *, props, chars, poses, sets, where):
    from cutan.characters.schema import DFLT_VIEW, VIEW_CHANNEL

    who = _find_character(shot, ba.character)
    name = f"prop {entity.id!r} (depicts {ba.character!r}'s body, seen {ba.view})"
    if who is None:
        if ba.view == FIRST_PERSON:
            return []
        return [("warning", where, f"{name}: {ba.character!r} is not on stage in this shot, so the limbs it shows belong to nobody")]
    if ba.view == FIRST_PERSON:
        return [("error", where, f"{name}: first-person art (seen through {ba.character!r}'s own eyes) while {ba.character!r} is on screen; draw it from the shot's camera ({_view_of(who, chars, sets, DFLT_VIEW, VIEW_CHANNEL)} view)")]
    if chars is None or who.ref not in chars:
        return []
    char = character_model(chars[who.ref])
    found: list[tuple[str, str, str]] = []
    view = _view_of(who, chars, sets, DFLT_VIEW, VIEW_CHANNEL, desc=char)
    if view != ba.view:
        found.append(("error", where, f"{name}: {ba.character!r} is in the {view!r} view in this shot, so the art shows the body from a different side than the camera does; draw it in the {view!r} view, as the camera sees {ba.character!r}"))
    if not ba.sockets:
        return found
    char_pose = _entity_pose(who, poses, sets.get(who.id, {}))
    prop_pose = _entity_pose(entity, poses, sets.get(entity.id, {}))
    if char_pose is None or prop_pose is None:
        found.append(("info", where, f"{name}: not placed with `stage.at`, so its sockets were not checked"))
        return found
    prop = prop_model(raw)
    try:
        targets, local = socket_pairs(prop, char, ba, art_size=_art_size_of(props, entity.ref), character_pose=char_pose)
    except ValueError as e:
        found.append(("error", where, f"{name}: {e}"))
        return found
    sx, sy = float(prop_pose.get("scale_x", 1.0)), float(prop_pose.get("scale_y", 1.0))
    rot = float(prop_pose.get("rotation", 0.0))
    c, s = math.cos(rot), math.sin(rot)
    px, py = float(prop_pose.get("x", 0.0)), float(prop_pose.get("y", 0.0))
    placed = [(px + c * q[0] * sx - s * q[1] * sy, py + s * q[0] * sx + c * q[1] * sy) for q in local]
    (fx, fy), fs = fit_placement(local, targets, scale=float(entity.stage.scale if entity.stage else 1.0))
    if fs <= 0:
        found.append(("error", where, crossed_limbs_message(entity.ref, ba)))
        return found
    span = _span(targets)
    if span <= 0:  # one socket, or bones that coincide: the body's own height sets the scale
        from an.stage.rig import bone_positions

        ys = [p[1] for p in bone_positions(char).values()]
        from an.stage.rig import SCENE_PX_PER_VIEW_BOX

        k = SCENE_PX_PER_VIEW_BOX / float(char.view_box[3] or 1)
        span = (max(ys) - min(ys)) * k * abs(float(char_pose.get("scale_y", 1.0))) / 2.0
    limit = ba.tolerance * span
    off = [
        (sock.bone, math.dist(a, b))
        for sock, a, b in zip(ba.sockets, placed, targets)
        if math.dist(a, b) > limit
    ]
    if off:
        worst = ", ".join(f"{bone} {d:.0f} px off" for bone, d in off)
        found.append(("error", where, f"{name}: its limbs do not meet {ba.character!r}'s body ({worst}; at most {limit:.0f} px, {ba.tolerance:g} of the {span:.0f} px span). Place it at [{fx:g}, {fy:g}] scale {fs:.3g} (cutan.body_attachment.place_body_prop), or redraw it"))
    return found


def _view_of(who, chars, sets, dflt, channel, *, desc=None) -> str:
    view = sets.get(who.id, {}).get(channel)
    if isinstance(view, str) and view:
        return view
    if desc is None and chars is not None and who.ref in chars:
        try:
            desc = character_model(chars[who.ref])
        except Exception:  # noqa: BLE001 - a malformed character is another check's
            desc = None
    return (getattr(desc, "rest_view", None) or dflt) if desc is not None else dflt


def check_body_attachments(ctx: Any) -> None:
    """The cut-out genre's body-continuity check (:func:`body_attachment_findings`)."""
    from cutan.characters.checks import _stage_poses_of

    if "props" not in ctx.stores:
        return
    if not any(e.kind == "prop" for e in ctx.shot.entities):
        return
    poses = _stage_poses_of(ctx, ctx.index, ctx.shot)
    for severity, where, message in body_attachment_findings(
        ctx.shot, ctx.stores, poses=poses, path=ctx.path
    ):
        ctx.report.add(severity, where, message)
