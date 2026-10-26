"""Where an attachment's anchor is drawn at rest, and placing it somewhere else.

The position is the one the core's rig builder gives the attachment's node
(``an.stage.rig.build_rig_subtree``), read from the same rules it reads
(``bone_positions``, ``rig_origin``, ``slot_parent_chain``, ``nesting_of``,
``drawn_attachment``, ``rest_transform``), in **view_box units from the rig's
origin**: a node's scene position divided by the builder's ``k``.

- :func:`rest_anchor` says where an attachment's anchor is drawn, and how its
  picture is turned and scaled there (its bone's rest pose, composed with the
  parts it nests under).
- :func:`place_attachment` sets the attachment's ``x``/``y`` so its anchor is
  drawn at a given point.

An attachment is named as :func:`cutan.characters.set_part.part_path` names it
(``name``, or ``slot/name``). Both raise :class:`SetPartError` for an unknown or
ambiguous attachment, a slot or bone the rig does not declare, a bone cycle, or
a part nested under one that draws nothing.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cutan.characters.descriptor_io import read_raw, save_raw, validate_raw
from cutan.characters.set_part import SetPartError

__all__ = ["RestAnchor", "find_attachment", "place_attachment", "rest_anchor"]

#: A 2x2 matrix ``(a, b, c, d)``: ``x' = a x + b y``, ``y' = c x + d y``.
Linear = tuple[float, float, float, float]
IDENTITY: Linear = (1.0, 0.0, 0.0, 1.0)
_TOLERANCE = 1e-9


@dataclass(frozen=True)
class RestAnchor:
    """Where an attachment's anchor is drawn at rest.

    slot, name, skin: the attachment found (the skin is the one the builder draws
        when it carries the attachment, else the first that does)
    world: the anchor's position, view_box units from the rig's origin
    frame: how the parts it nests under map an offset of its node (identity
        when none of them is turned or scaled)
    linear: how its picture is drawn there (``frame`` times its bone's rest pose)
    anchor: the anchor, 0..1 of its picture
    """

    slot: str
    name: str
    skin: str
    world: tuple[float, float]
    frame: Linear
    linear: Linear
    anchor: tuple[float, float]

    @property
    def posed(self) -> bool:
        """Whether its picture is drawn turned or scaled (a point of it moves off
        ``world + offset``)."""
        return not _is_identity(self.linear)


def _is_identity(m: Linear) -> bool:
    return all(abs(a - b) <= _TOLERANCE for a, b in zip(m, IDENTITY))


def _mul(m: Linear, n: Linear) -> Linear:
    a, b, c, d = m
    e, f, g, h = n
    return (a * e + b * g, a * f + b * h, c * e + d * g, c * f + d * h)


def _apply(m: Linear, v: tuple[float, float]) -> tuple[float, float]:
    a, b, c, d = m
    return (a * v[0] + b * v[1], c * v[0] + d * v[1])


def _rest_linear(rest: dict[str, float]) -> Linear:
    """A node's rest transform as a matrix: scale, then rotate (the stage's order,
    as ``cutan.body_attachment.rig_point_on_stage`` reads it)."""
    if not rest:
        return IDENTITY
    r, sx, sy = rest["rotation"], rest["scale_x"], rest["scale_y"]
    c, s = math.cos(r), math.sin(r)
    return (c * sx, -s * sy, s * sx, c * sy)


def _applies_rest_pose(raw: dict[str, Any], desc: Any) -> bool:
    """The builder's ``apply_rest_pose``, decided as it decides it."""
    from an.ir.migrate import migrate
    from an.stage.rig import REST_POSE_SINCE, legacy_rest_pose_unknown

    from cutan.characters.schema import CHARACTER_DOCUMENT_KIND as kind

    legacy = legacy_rest_pose_unknown(
        raw, kind, since=REST_POSE_SINCE.get(kind.name)
    ) and "rest_rotation" not in migrate(dict(raw), kind=kind.name)
    return getattr(desc, "rest_rotation", None) is not False and not legacy


def find_attachment(desc: Any, attachment: str) -> tuple[str, str, str, Any]:
    """``(skin, slot, name, Attachment)`` for ``name`` or ``slot/name`` in the
    descriptor ``desc``: from the skin the builder draws when it carries it, else
    from the first skin that does. Raises :class:`SetPartError` when no slot, or
    more than one, carries it."""
    slot_wanted, _, name_wanted = attachment.rpartition("/")
    drawn = "default" if "default" in desc.skins else next(iter(desc.skins), None)
    order = [drawn] + [s for s in desc.skins if s != drawn] if drawn else []
    hits: dict[str, tuple[str, Any]] = {}
    for skin in order:
        for slot, atts in desc.skins[skin].slots.items():
            if name_wanted in atts and slot_wanted in ("", slot) and slot not in hits:
                hits[slot] = (skin, atts[name_wanted])
    if not hits:
        raise SetPartError(f"no attachment {attachment!r} (try slot/name)")
    if len(hits) > 1:
        raise SetPartError(
            f"{attachment!r} is in several slots ({', '.join(sorted(hits))}): "
            "name it as slot/name"
        )
    ((slot, (skin, att)),) = hits.items()
    return skin, slot, name_wanted, att


def _rest_anchor(raw: dict[str, Any], desc: Any, attachment: str) -> RestAnchor:
    from an.stage.rig import (
        BONES_NESTING,
        Skin,
        bone_positions,
        drawn_attachment,
        nesting_of,
        rest_transform,
        rig_origin,
        rig_problems,
        slot_parent_chain,
    )

    cycles = [p for p in rig_problems(desc) if "cycle" in p]
    if cycles:
        raise SetPartError("; ".join(cycles))
    skin_name, slot_name, name, att = find_attachment(desc, attachment)
    slot_of = {s.name: s for s in desc.slots}
    bone_of = {b.name: b for b in desc.bones}
    if slot_name not in slot_of:
        raise SetPartError(f"slot {slot_name!r} is in a skin but the rig declares none")
    skin = desc.skins.get("default") or next(iter(desc.skins.values()), Skin())
    bones = bone_positions(desc)
    origin = rig_origin(desc)
    parents = slot_parent_chain(desc)
    bones_mode = nesting_of(desc) == BONES_NESTING
    apply_rest = _applies_rest_pose(raw, desc)

    chain = [slot_name]  # the slot, then each slot it nests under
    while (up := parents.get(chain[-1])) is not None:
        if up in chain:
            raise SetPartError(f"slots nest in a cycle: {' -> '.join(chain + [up])}")
        chain.append(up)

    def node(slot_name: str, drawn: Any) -> tuple[tuple[float, float], Linear]:
        """The builder's node for ``slot_name`` drawing ``drawn``: its offset from
        its parent node (view_box units) and its rest pose."""
        slot = slot_of[slot_name]
        if slot.bone not in bones:
            raise SetPartError(
                f"slot {slot_name!r} is bound to bone {slot.bone!r}, which the rig "
                "does not declare"
            )
        x, y = bones[slot.bone]
        parent = parents.get(slot_name)
        if parent is not None:
            px, py = bones.get(slot_of[parent].bone, (0.0, 0.0))
            x, y = x - px, y - py
            if bones_mode:
                drawn_parent = drawn_attachment(desc, skin, slot_of[parent])
                if drawn_parent is not None:
                    x, y = x - drawn_parent[1].x, y - drawn_parent[1].y
        else:
            x, y = x - origin[0], y - origin[1]
        rest = (
            rest_transform(bone_of[slot.bone])
            if apply_rest
            and not (parent is not None and slot_of[parent].bone == slot.bone)
            else {}
        )
        return (x + drawn.x, y + drawn.y), _rest_linear(rest)

    at, frame = (0.0, 0.0), IDENTITY
    for i, s in enumerate(reversed(chain)):
        if s == slot_name:
            drawn = att
        else:
            found = drawn_attachment(desc, skin, slot_of[s])
            if found is None:
                raise SetPartError(
                    f"{attachment!r} nests under slot {s!r}, which draws nothing"
                )
            drawn = found[1]
        offset, own = node(s, drawn)
        step = _apply(frame, offset)
        at = (at[0] + step[0], at[1] + step[1])
        if s == slot_name:
            return RestAnchor(
                slot_name,
                name,
                skin_name,
                at,
                frame,
                _mul(frame, own),
                tuple(att.anchor),
            )
        frame = _mul(frame, own)
    raise AssertionError("unreachable: the chain starts at the slot")


def rest_anchor(char_dir: str | Path, attachment: str) -> RestAnchor:
    """Where ``attachment``'s anchor is drawn at rest (see :class:`RestAnchor`).

    >>> import tempfile
    >>> from cutan.characters import new_character
    >>> d = new_character(tempfile.mkdtemp(), name="n", seed="n", use_dicebear=False).parent
    >>> rest_anchor(d, "torso").world  # the torso bone, from the rig's origin
    (0.0, -20.0)
    """
    raw = read_raw(char_dir)
    return _rest_anchor(raw, validate_raw(raw), attachment)


def place_attachment(
    char_dir: str | Path, attachment: str, *, world: tuple[float, float]
) -> RestAnchor:
    """Set ``attachment``'s ``x``/``y`` so its anchor is drawn at ``world`` (view_box
    units from the rig's origin, as :func:`rest_anchor` gives it); return where it
    now is. The attachments of the same slot and skin drawn by the same file move
    with it (one picture, one place); other slots, skins and files are left alone.

    >>> import tempfile
    >>> from cutan.characters import new_character
    >>> d = new_character(tempfile.mkdtemp(), name="n", seed="n", use_dicebear=False).parent
    >>> place_attachment(d, "arm_l", world=(-100.0, -240.0)).world
    (-100.0, -240.0)
    """
    raw = read_raw(char_dir)
    now = _rest_anchor(raw, validate_raw(raw), attachment)
    a, b, c, d = now.frame
    det = a * d - b * c
    if abs(det) <= _TOLERANCE:
        raise SetPartError(
            f"{attachment!r} nests under a part scaled to nothing at rest: it "
            "cannot be placed"
        )
    gap = (world[0] - now.world[0], world[1] - now.world[1])
    dx, dy = _apply((d / det, -b / det, -c / det, a / det), gap)
    atts = raw["skins"][now.skin]["slots"][now.slot]
    path = atts[now.name].get("path")
    for key, att in atts.items():
        if key == now.name or (path and att.get("path") == path):
            att["x"] = float(att.get("x") or 0.0) + dx
            att["y"] = float(att.get("y") or 0.0) + dy
    desc = save_raw(char_dir, raw)
    return _rest_anchor(raw, desc, attachment)
