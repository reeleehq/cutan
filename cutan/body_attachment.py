"""Props that depict part of a character's body: the declaration, the geometry, the placement.

A steering wheel with the driver's hands on it, a sleeve holding a cup, a pair of
forearms on a table: art that shows *somebody's* limbs, drawn as one prop and laid
over a rigged character. Two mistakes reached a viewer in one production, and
neither was visible to any check that existed:

1. **The art was drawn from the wrong viewpoint.** The image model drew the wheel
   from the driver's seat (forearms coming from the camera), while the shot looked
   at the driver from in front, through the windscreen.
2. **The art did not meet the body.** Placed by hand, the wheel sat to the right of
   the driver's head and was wider than his body, so the arms in it could not come
   from his shoulders.

Both are now facts the prop *declares* and the genre *checks*. The declaration
lives in the prop's own document, under ``metadata.body_attachment`` (the
persisted key :data:`BODY_ATTACHMENT_KEY`), because what a drawing depicts is a
property of the drawing:

.. code-block:: json

    {"kind": "PropDescriptor", "name": "wheel_hands", "...": "...",
     "metadata": {"body_attachment": {
         "character": "paul",
         "view": "front",
         "sockets": [
             {"bone": "arm_l", "at": [0.20, -0.35]},
             {"bone": "arm_r", "at": [0.80, -0.35]}
         ]}}}

- ``character``: the entity (scene id, else store ref) whose body the art shows.
- ``view``: the view of that body the art is drawn in, in the rig's own words
  (:data:`cutan.characters.schema.VIEWS`: ``front``, ``three_quarter``, ``side``,
  ``back``), or :data:`FIRST_PERSON` for art seen through the character's own eyes
  (valid only while the character is NOT on screen).
- ``sockets``: where each depicted limb meets the body. ``bone`` names the
  character's bone (``arm_l`` is the bone at the viewer's LEFT on the factory rig,
  whatever side of the person it is); ``at`` is the point, in the art's own
  ``(u, v)`` units (0..1 of the drawn image, like an attachment ``anchor``), where
  that bone's joint would be. It may lie outside the image: forearms that vanish
  behind a wheel still say where their shoulders are.
- ``tolerance`` (optional, default :data:`DFLT_TOLERANCE`): how far a socket may
  land from its bone, as a fraction of the distance between the sockets' bones on
  screen (the shoulder span, for two arms).

:func:`place_body_prop` turns the declaration into a placement (the prop's
``stage.at`` and ``stage.scale``) from where the character stands, so nobody
places such a prop by eye; :mod:`cutan.verify.body` is the check ``an validate``
runs on every shot.

>>> ba = BodyAttachment(character="paul", view="front", sockets=[
...     {"bone": "arm_l", "at": [0.2, -0.35]}, {"bone": "arm_r", "at": [0.8, -0.35]}])
>>> [s.bone for s in ba.sockets], ba.tolerance
(['arm_l', 'arm_r'], 0.25)
"""

from __future__ import annotations

import math
from typing import Any, Callable, Literal, Mapping, Optional, Sequence, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = [
    "BODY_ATTACHMENT_KEY",
    "BodyAttachment",
    "Socket",
    "body_attachment_of",
    "rig_point_on_stage",
    "socket_rig_point",
    "fit_placement",
    "place_body_prop",
    "socket_pairs",
    "character_model",
    "prop_model",
]

#: The persisted key under a prop document's ``metadata``. Never renamed.
BODY_ATTACHMENT_KEY: str = "body_attachment"

#: The view of art seen through the character's own eyes (a first-person shot).
FIRST_PERSON: str = "first_person"

#: The views a declaration may name: the rig's views, plus the first person.
BODY_VIEWS: tuple[str, ...] = ("front", "three_quarter", "side", "back", FIRST_PERSON)

#: How far a socket may land from its bone, as a fraction of the span between the
#: sockets' bones on screen. A quarter of the shoulder span is about a hand's width
#: on the factory rig: generous enough for a drawn sleeve, far tighter than the
#: production mistake (a wheel centred a head's width to one side).
DFLT_TOLERANCE: float = 0.25

#: The size a slot's art rasterises at, or a function of the art's path giving it.
ArtSize = Union[tuple[float, float], None, Callable[[str], Optional[tuple[float, float]]]]



class Socket(BaseModel):
    """Where one depicted limb meets the character's body.

    >>> Socket(bone="arm_l", at=(0.2, -0.4)).at
    (0.2, -0.4)
    """

    model_config = ConfigDict(extra="forbid")

    #: The character's bone the limb belongs to; its joint is the meeting point.
    bone: str
    #: That joint, in the art's ``(u, v)`` (0..1 of the drawn image; outside is allowed).
    at: tuple[float, float]
    #: The prop's slot whose art ``at`` is measured on. ``None``: the prop's first slot.
    slot: Optional[str] = None

    @field_validator("at")
    @classmethod
    def _finite(cls, v: tuple[float, float]) -> tuple[float, float]:
        if not all(math.isfinite(c) for c in v):
            raise ValueError(f"a socket's `at` must be finite, got {v!r}")
        return v


class BodyAttachment(BaseModel):
    """A prop's declaration that it depicts part of a character's body.

    >>> BodyAttachment(character="paul", view="driver", sockets=[])
    Traceback (most recent call last):
    ...
    pydantic_core._pydantic_core.ValidationError: 1 validation error for BodyAttachment
    ...
    """

    model_config = ConfigDict(extra="forbid")

    character: str
    view: Literal["front", "three_quarter", "side", "back", "first_person"]
    sockets: list[Socket] = Field(default_factory=list)
    tolerance: float = Field(default=DFLT_TOLERANCE, gt=0, allow_inf_nan=False)


def _field(doc: Any, name: str, default: Any = None) -> Any:
    if isinstance(doc, Mapping):
        return doc.get(name, default)
    return getattr(doc, name, default)


def body_attachment_of(prop_doc: Any) -> BodyAttachment | None:
    """The prop's :class:`BodyAttachment`, or ``None`` when it declares none.

    ``prop_doc`` is a ``PropDescriptor`` or the stored mapping. A malformed
    declaration raises (pydantic's ``ValidationError``): the check reports it.

    >>> body_attachment_of({"metadata": {}}) is None
    True
    >>> body_attachment_of({"metadata": {"body_attachment": {
    ...     "character": "paul", "view": "front"}}}).view
    'front'
    """
    raw = (_field(prop_doc, "metadata") or {}).get(BODY_ATTACHMENT_KEY)
    if raw is None:
        return None
    return BodyAttachment.model_validate(raw)


# --- geometry -----------------------------------------------------------------
#
# Where a point of a rig lands on the stage, by the compiler's own rules
# (`an.stage.rig.build_rig_subtree`): a rig point ``p`` (view_box units) sits at
# ``(p - rig_origin) * k`` inside the entity, ``k = SCENE_PX_PER_VIEW_BOX /
# view_box height``, and the entity's node maps that by its scale, rotation and
# position. A part is centred on its slot's bone plus the attachment's offset, at
# its anchor, in its box (`attachment_box`). tests/test_body_attachment.py holds
# this to a compiled shot.


def _k(desc: Any) -> float:
    from an.stage.rig import SCENE_PX_PER_VIEW_BOX

    view_box = _field(desc, "view_box")
    return SCENE_PX_PER_VIEW_BOX / float(view_box[3] or 1)


def rig_point_on_stage(
    desc: Any, point: Sequence[float], pose: Mapping[str, float]
) -> tuple[float, float]:
    """Where ``point`` (view_box units of the rig ``desc``) lands on the stage when
    the entity's node has ``pose`` (``x``, ``y``, ``scale_x``, ``scale_y``,
    ``rotation`` in radians, as :func:`an.motion.stage_poses` reports it).

    >>> from types import SimpleNamespace as NS
    >>> rig = NS(view_box=(0, 0, 345, 345), origin=(100, 100), bones=[])
    >>> rig_point_on_stage(rig, (110, 100), {"x": 5, "y": 0, "scale_x": 2, "scale_y": 2})
    (25.0, 0.0)
    """
    from an.stage.rig import rig_origin

    ox, oy = rig_origin(desc)
    k = _k(desc)
    lx, ly = (point[0] - ox) * k, (point[1] - oy) * k
    sx = float(pose.get("scale_x", 1.0))
    sy = float(pose.get("scale_y", 1.0))
    rot = float(pose.get("rotation", 0.0))
    c, s = math.cos(rot), math.sin(rot)
    x, y = lx * sx, ly * sy
    return (
        round(float(pose.get("x", 0.0)) + c * x - s * y, 6),
        round(float(pose.get("y", 0.0)) + s * x + c * y, 6),
    )


def _first_slot(desc: Any) -> Any:
    slots = list(_field(desc, "slots") or [])
    if not slots:
        raise ValueError("the prop has no slot to measure a socket on")
    return sorted(slots, key=lambda s: (s.draw_order, s.name))[0]


def socket_rig_point(
    prop_desc: Any,
    socket: Socket,
    *,
    art_size: ArtSize,
) -> tuple[float, float]:
    """The socket's ``at`` as a point of the prop's rig (view_box units).

    ``art_size`` is what the slot's drawn art rasterises at (pixels for a
    raster, the SVG's size), as the compiler's probe measures it, or a function
    of the attachment's ``path`` returning it (``None``: unmeasurable); a declared
    ``width``/``height`` on the attachment wins, keeping the art's aspect.
    Raises ``ValueError`` when the slot, its art or its box cannot be found, or
    when the slot is nested under another (not supported by this v1).

    >>> from an.stage.props import PropDescriptor
    >>> p = PropDescriptor.model_validate({"name": "w", "skins": {"default": {"slots": {
    ...     "body": {"w": {"path": "parts/w.png"}}}}}, "slots": [
    ...     {"name": "body", "bone": "root", "attachment": "w"}]})
    >>> socket_rig_point(p, Socket(bone="arm_l", at=(0.0, 0.5)), art_size=(400, 200))
    (312.0, 512.0)
    """
    from an.stage.rig import attachment_box, bone_positions, drawn_attachment, slot_parent_chain

    slot = (
        _first_slot(prop_desc)
        if socket.slot is None
        else next((s for s in prop_desc.slots if s.name == socket.slot), None)
    )
    if slot is None:
        raise ValueError(f"the prop has no slot {socket.slot!r}")
    if slot_parent_chain(prop_desc).get(slot.name) is not None:
        raise ValueError(
            f"slot {slot.name!r} is nested under another slot; measure sockets on a top-level slot"
        )
    skin = prop_desc.skins.get("default") or next(iter(prop_desc.skins.values()), None)
    drawn = drawn_attachment(prop_desc, skin, slot) if skin is not None else None
    if drawn is None:
        raise ValueError(f"slot {slot.name!r} draws no attachment")
    att = drawn[1]
    size = art_size(att.path) if callable(art_size) else art_size
    box = attachment_box(att.width, att.height, size)
    if box is None:
        raise ValueError(
            f"the art of slot {slot.name!r} ({att.path}) cannot be measured and declares no box"
        )
    bx, by = bone_positions(prop_desc).get(slot.bone, (0.0, 0.0))
    ax, ay = att.anchor
    u, v = socket.at
    return (bx + att.x + (u - ax) * box[0], by + att.y + (v - ay) * box[1])


def fit_placement(
    sockets: Sequence[tuple[float, float]],
    targets: Sequence[tuple[float, float]],
    *,
    scale: float = 1.0,
) -> tuple[tuple[float, float], float]:
    """The ``(offset, scale)`` that best maps ``sockets`` onto ``targets``:
    ``targets ≈ offset + scale * sockets`` (least squares, uniform scale, no
    rotation, since a stage placement has none). With one socket (or sockets that
    coincide) the scale cannot be measured and ``scale`` is kept.

    A non-positive scale means the limbs are crossed: the art's left limb would
    have to meet the body's right. That is not a placement; it is art drawn from
    the other side (a back or first-person view of a front-facing rig), and the
    returned scale is negative so the caller can say so.

    >>> fit_placement([(0, 0), (10, 0)], [(100, 50), (120, 50)])
    ((100.0, 50.0), 2.0)
    >>> fit_placement([(5, 5)], [(100, 50)], scale=3.0)
    ((85.0, 35.0), 3.0)
    >>> fit_placement([(0, 0), (10, 0)], [(120, 50), (100, 50)])[1]
    -2.0
    """
    if not sockets or len(sockets) != len(targets):
        raise ValueError("fit_placement needs as many targets as sockets, at least one")
    n = float(len(sockets))
    qx = sum(p[0] for p in sockets) / n
    qy = sum(p[1] for p in sockets) / n
    px = sum(p[0] for p in targets) / n
    py = sum(p[1] for p in targets) / n
    var = sum((q[0] - qx) ** 2 + (q[1] - qy) ** 2 for q in sockets)
    if var > 1e-9:
        cov = sum(
            (q[0] - qx) * (p[0] - px) + (q[1] - qy) * (p[1] - py)
            for q, p in zip(sockets, targets)
        )
        scale = cov / var
    return ((round(px - scale * qx, 3), round(py - scale * qy, 3)), round(scale, 6))


def _validated(doc: Any, model: type, kind_name: str) -> Any:
    if isinstance(doc, Mapping):
        from an.ir.migrate import migrate

        return model.model_validate(migrate(dict(doc), kind=kind_name))
    return doc


def character_model(doc: Any) -> Any:
    """A ``CharacterDescriptor`` from a stored mapping (migrated), or the model as given."""
    from cutan.characters.schema import CHARACTER_DOCUMENT_KIND, CharacterDescriptor

    return _validated(doc, CharacterDescriptor, CHARACTER_DOCUMENT_KIND.name)


def prop_model(doc: Any) -> Any:
    """A ``PropDescriptor`` from a stored mapping (migrated), or the model as given."""
    from an.stage.props import PROP_DOCUMENT_KIND, PropDescriptor

    return _validated(doc, PropDescriptor, PROP_DOCUMENT_KIND.name)


def place_body_prop(
    prop_desc: Any,
    character_desc: Any,
    *,
    character_at: Sequence[float],
    character_scale: float = 1.0,
    art_size: ArtSize,
    scale: float | None = None,
) -> dict[str, Any]:
    """Where to put a body-depicting prop so its sockets meet the character's bones.

    Returns ``{"at": [x, y], "scale": s, "residual_px": r}``: the prop's
    ``stage.at`` and ``stage.scale``, derived from where the character stands
    (``character_at``, ``character_scale``: its ``stage.at`` and ``stage.scale``),
    and the largest distance left between a socket and its bone. ``scale`` is used
    only when one socket cannot measure it (default: the character's scale).

    Refuses (``ValueError``) a prop that declares no body attachment, a socket
    naming a bone the character does not have, and crossed limbs (the fitted
    scale is not positive: the art is drawn from the other side).

    >>> from an.stage.props import PropDescriptor
    >>> from cutan.characters.schema import CharacterDescriptor
    >>> paul = CharacterDescriptor(name="paul")
    >>> wheel = PropDescriptor.model_validate({"name": "w", "slots": [
    ...     {"name": "body", "bone": "root", "attachment": "w"}],
    ...     "skins": {"default": {"slots": {"body": {"w": {"path": "parts/w.png"}}}}},
    ...     "metadata": {"body_attachment": {"character": "paul", "view": "front",
    ...         "sockets": [{"bone": "arm_l", "at": [0.1, 0.0]},
    ...                     {"bone": "arm_r", "at": [0.9, 0.0]}]}}})
    >>> place_body_prop(wheel, paul, character_at=(200, 400), character_scale=2.0,
    ...                 art_size=(500, 300))
    {'at': [200.0, 270.288], 'scale': 0.9, 'residual_px': 0.0}
    """
    char = character_model(character_desc)
    prop = prop_model(prop_desc)
    ba = body_attachment_of(prop)
    if ba is None:
        raise ValueError(f"prop {prop.name!r} declares no {BODY_ATTACHMENT_KEY}")
    if not ba.sockets:
        raise ValueError(f"prop {prop.name!r}'s {BODY_ATTACHMENT_KEY} declares no socket")
    targets, local = socket_pairs(
        prop, char, ba, art_size=art_size,
        character_pose={"x": character_at[0], "y": character_at[1],
                        "scale_x": character_scale, "scale_y": character_scale},
    )
    (x, y), s = fit_placement(
        local, targets, scale=character_scale if scale is None else scale
    )
    if s <= 0:
        raise ValueError(crossed_limbs_message(prop.name, ba))
    placed = [(x + s * q[0], y + s * q[1]) for q in local]
    residual = max(math.dist(a, b) for a, b in zip(placed, targets))
    return {"at": [x, y], "scale": round(s, 4), "residual_px": round(residual, 2)}


def crossed_limbs_message(name: str, ba: BodyAttachment) -> str:
    return (
        f"prop {name!r}: its limbs are crossed relative to {ba.character!r}'s bones "
        f"(the art's {ba.sockets[0].bone} side meets the body's other side), so the art "
        f"is drawn from the other side of the body than its declared view {ba.view!r}: "
        "redraw it seen from the shot's camera, or fix the sockets' bones"
    )


def socket_pairs(
    prop: Any,
    char: Any,
    ba: BodyAttachment,
    *,
    art_size: ArtSize,
    character_pose: Mapping[str, float],
) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    """``(bones on stage, sockets in the prop's local stage units at scale 1)``."""
    from an.stage.rig import bone_positions

    bones = bone_positions(char)
    missing = [s.bone for s in ba.sockets if s.bone not in bones]
    if missing:
        raise ValueError(
            f"{ba.character!r} has no bone {', '.join(map(repr, missing))} "
            f"(its bones: {', '.join(sorted(bones))})"
        )
    targets = [rig_point_on_stage(char, bones[s.bone], character_pose) for s in ba.sockets]
    unit = {"x": 0.0, "y": 0.0, "scale_x": 1.0, "scale_y": 1.0}
    local = [
        rig_point_on_stage(prop, socket_rig_point(prop, s, art_size=art_size), unit)
        for s in ba.sockets
    ]
    return targets, local
