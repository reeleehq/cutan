"""Props that depict part of a character's body: the declaration, the geometry, the placement.

A steering wheel with the driver's hands on it, a sleeve holding a cup, a pair of
forearms on a table: art that shows *somebody's* limbs, drawn as one prop and laid
over a rigged character. Three mistakes reached a viewer in one production, and
no check that existed could see any of them:

1. **The art was drawn from the wrong viewpoint.** The image model drew the wheel
   from the driver's seat (forearms coming from the camera), while the shot looked
   at the driver from in front, through the windscreen.
2. **The art did not meet the body.** Placed by hand, the wheel sat to the right of
   the driver's head and was wider than his body, so the arms in it could not come
   from his shoulders.
3. **The relation drifted between framings.** The two-shot and the close-up each
   placed the wheel by hand, so the driver's size relative to his own hands changed
   at the cut.

All three are now one contract, declared ONCE in the character's own units (its
bones) and derived for every framing. The declaration lives in the prop's
document, under ``metadata.body_attachment`` (the persisted key
:data:`BODY_ATTACHMENT_KEY`), because what a drawing depicts is a property of the
drawing:

.. code-block:: json

    {"kind": "PropDescriptor", "name": "wheel_hands", "...": "...",
     "metadata": {"body_attachment": {
         "schema_version": "0.1.0",
         "character": "paul",
         "view": "front",
         "sockets": [
             {"bone": "arm_l", "at": [0.20, 0.45]},
             {"bone": "arm_r", "at": [0.80, 0.45]}
         ]}}}

- ``character`` (optional): the character whose body the art shows, by scene
  entity id, else store ref. A scene entity binds a reusable prop to another
  character with ``overrides: {body_of: jerry}`` (:data:`BODY_OF_OVERRIDE`).
- ``view``: the character's view the art is drawn in, in the rig's own words
  (``front``, ``three_quarter``, ``side``, ``back``, or any key of the
  character's ``view`` swap set), or :data:`FIRST_PERSON` when the camera IS the
  character (valid only while the character is not on screen).
- ``sockets``: where each depicted limb meets the body, in the character's REST
  view. ``bone`` names the character's bone (``arm_l`` is the bone at the viewer's
  left on the factory rig, unmirrored); ``at`` is where that bone's joint would be,
  in the art's ``(u, v)`` (0..1 of the drawn image, like an attachment
  ``anchor``). It may lie outside the image: forearms that vanish behind a wheel
  still say where their shoulders are.
- ``scale`` (optional): the prop's ``stage.scale`` relative to the character's.
  Two sockets measure it; one socket needs it.
- ``tolerance`` (default :data:`DFLT_TOLERANCE`): how far a socket may land from
  its bone, as a fraction of the span between the sockets' bones on screen.
  ``scale_tolerance`` (default :data:`DFLT_SCALE_TOLERANCE`): how far the prop's
  size relative to the character may differ from the declared relation.

Unknown keys are kept (forward-compatible): a later field is not "malformed" to
an older ``cutan``.

**Placement is derived, not authored.** A body-attached prop with no
``stage.at`` is placed by its body in every shot (the ``body_placement`` compile
pass, :mod:`cutan.compile.body`), so the relation cannot drift between a two-shot
and a close-up. :func:`place_body_prop` is the same derivation as a function.
:mod:`cutan.verify.body` checks a prop that IS placed by hand against it.

>>> ba = BodyAttachment(character="paul", view="front", sockets=[
...     {"bone": "arm_l", "at": [0.2, 0.45]}, {"bone": "arm_r", "at": [0.8, 0.45]}])
>>> [s.bone for s in ba.sockets], ba.tolerance, ba.scale_tolerance
(['arm_l', 'arm_r'], 0.25, 0.05)
"""

from __future__ import annotations

import math
from typing import Any, Callable, Mapping, Optional, Sequence, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = [
    "BODY_ATTACHMENT_KEY",
    "BODY_OF_OVERRIDE",
    "FIRST_PERSON",
    "BodyAttachment",
    "Socket",
    "NotChecked",
    "CrossedLimbs",
    "body_attachment_of",
    "bound_character",
    "start_state",
    "entity_pose",
    "character_view",
    "rig_point_on_stage",
    "socket_rig_point",
    "fit_placement",
    "solve_placement",
    "place_body_prop",
    "derivable_placement",
    "derive_placement",
    "character_model",
    "prop_model",
]

#: The persisted key under a prop document's ``metadata``. Never renamed.
BODY_ATTACHMENT_KEY: str = "body_attachment"

#: The scene entity's ``overrides`` key that binds a prop to a character.
BODY_OF_OVERRIDE: str = "body_of"

#: The declaration's version, written when a tool writes one.
BODY_ATTACHMENT_SCHEMA_VERSION: str = "0.1.0"

#: The view of art seen through the character's own eyes (the camera is the character).
FIRST_PERSON: str = "first_person"

#: How far a socket may land from its bone, as a fraction of the span between the
#: sockets' bones on screen. A quarter of the shoulder span is about a hand's width
#: on the factory rig: generous enough for a drawn sleeve, far tighter than the
#: production mistake (a wheel centred a head's width to one side).
DFLT_TOLERANCE: float = 0.25

#: How far the prop's size relative to its character may differ from the
#: declared relation (a fraction). 5% is below what an eye notices across a cut;
#: the production's drift was 20%.
DFLT_SCALE_TOLERANCE: float = 0.05

#: The root-node properties a ``set`` at the shot's start overrides.
POSE_KEYS: tuple[str, ...] = ("x", "y", "scale_x", "scale_y", "rotation")

#: A ``set`` at or before this time (seconds) counts as the shot's start.
_START_EPS: float = 1e-6

#: The size a slot's art rasterises at, or a function of the art's path giving it.
ArtSize = Union[
    tuple[float, float], None, Callable[[str], Optional[tuple[float, float]]]
]


class NotChecked(ValueError):
    """The geometry cannot be computed for a reason that is a limit of this
    check, not a fault of the art (a nested slot, a posed bone, unmeasurable art,
    a mirrored or rotated character): reported as ``info``."""


class CrossedLimbs(ValueError):
    """The art's left limb would meet the body's right: drawn from the other side."""


class Socket(BaseModel):
    """Where one depicted limb meets the character's body.

    >>> Socket(bone="arm_l", at=(0.2, -0.4)).at
    (0.2, -0.4)
    """

    model_config = ConfigDict(extra="allow")

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

    >>> BodyAttachment(view="")
    Traceback (most recent call last):
    ...
    pydantic_core._pydantic_core.ValidationError: 1 validation error for BodyAttachment
    ...
    >>> BodyAttachment(view="front", grip="later field").model_dump()["grip"]
    'later field'
    """

    model_config = ConfigDict(extra="allow")

    schema_version: str = BODY_ATTACHMENT_SCHEMA_VERSION
    character: Optional[str] = None
    view: str = Field(min_length=1)
    sockets: list[Socket] = Field(default_factory=list)
    scale: Optional[float] = Field(default=None, gt=0, allow_inf_nan=False)
    tolerance: float = Field(default=DFLT_TOLERANCE, gt=0, allow_inf_nan=False)
    scale_tolerance: float = Field(
        default=DFLT_SCALE_TOLERANCE, gt=0, allow_inf_nan=False
    )


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
    >>> body_attachment_of({"metadata": ["not a mapping"]}) is None
    True
    >>> body_attachment_of({"metadata": {"body_attachment": {"view": "front"}}}).view
    'front'
    """
    meta = _field(prop_doc, "metadata")
    if not isinstance(meta, Mapping):
        return None
    raw = meta.get(BODY_ATTACHMENT_KEY)
    if raw is None:
        return None
    return BodyAttachment.model_validate(raw)


# --- the shot's start --------------------------------------------------------


def start_state(shot: Any) -> dict[str, dict[str, Any]]:
    """``{entity id: {property: value}}`` from the ``set`` actions at the shot's
    start, on the entities' own nodes (a part's are ignored).

    >>> from an.ir.schema import SetAction, Shot
    >>> start_state(Shot(id="s", actions=[SetAction(target="p", property="view", value="side")]))
    {'p': {'view': 'side'}}
    """
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
            if "/" not in target:
                out.setdefault(target, {})[a.property] = a.value
    return out


def entity_pose(
    entity: Any,
    poses: Mapping[str, Mapping[str, float]] | None = None,
    sets: Mapping[str, Any] | None = None,
) -> dict[str, float] | None:
    """The entity node's pose at the shot's start: the built pose when ``poses``
    has it, else its ``stage`` placement, then any ``set`` at the start.
    ``None`` when neither places it (the default layout, without built poses).

    >>> from an.ir.schema import AssetRef, StagePlacement
    >>> e = AssetRef(kind="prop", id="w", store="props", ref="w", stage=StagePlacement(at=(1, 2), scale=3))
    >>> entity_pose(e, None, {"x": 5})
    {'x': 5.0, 'y': 2.0, 'scale_x': 3.0, 'scale_y': 3.0, 'rotation': 0.0}
    """
    if poses is not None and entity.id in poses:
        pose = {k: float(v) for k, v in poses[entity.id].items() if k in POSE_KEYS}
    elif entity.stage is not None and entity.stage.at is not None:
        s = float(entity.stage.scale)
        pose = {
            "x": float(entity.stage.at[0]),
            "y": float(entity.stage.at[1]),
            "scale_x": s,
            "scale_y": s,
        }
    else:
        return None
    pose.setdefault("rotation", 0.0)
    for key in POSE_KEYS:
        if key in (sets or {}):
            try:
                pose[key] = float(sets[key])
            except (TypeError, ValueError):
                pass
    return pose


def bound_character(shot: Any, prop_entity: Any, ba: BodyAttachment) -> tuple[Any, str]:
    """``(the character entity, its name)`` the prop is bound to in ``shot``:
    the entity's ``overrides.body_of`` first, else the declaration's
    ``character``; by entity id, else by store ref when exactly one entity has
    it. The entity is ``None`` when absent or ambiguous; the name is ``""`` when
    nothing binds the prop.
    """
    name = (prop_entity.overrides or {}).get(BODY_OF_OVERRIDE) or ba.character or ""
    chars = [e for e in shot.entities if e.kind == "character"]
    by_id = [e for e in chars if e.id == name]
    if by_id:
        return by_id[0], name
    by_ref = [e for e in chars if e.ref == name]
    return (by_ref[0] if len(by_ref) == 1 else None), name


def character_view(char_entity: Any, char_desc: Any, sets: Mapping[str, Any]) -> str:
    """The character's view at the shot's start: a ``view`` set at 0, else its
    ``rest_view``, else ``front``."""
    from cutan.characters.schema import DFLT_VIEW, VIEW_CHANNEL

    view = (sets or {}).get(VIEW_CHANNEL)
    if isinstance(view, str) and view:
        return view
    return _field(char_desc, "rest_view") or DFLT_VIEW


def rest_view_of(char_desc: Any) -> str:
    """The view a character's bones are drawn in (sockets are declared in it)."""
    from cutan.characters.schema import DFLT_VIEW

    return _field(char_desc, "rest_view") or DFLT_VIEW


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
        raise NotChecked("the prop has no slot to measure a socket on")
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
    of the attachment's ``path`` returning it (``None``: unmeasurable); a
    declared ``width``/``height`` on the attachment wins, keeping the art's
    aspect. Raises :class:`NotChecked` for what this v1 does not compute: a
    missing slot or art, unmeasurable art, a nested slot, a posed bone.

    >>> from an.stage.props import PropDescriptor
    >>> p = PropDescriptor.model_validate({"name": "w", "skins": {"default": {"slots": {
    ...     "body": {"w": {"path": "parts/w.png"}}}}}, "slots": [
    ...     {"name": "body", "bone": "root", "attachment": "w"}]})
    >>> socket_rig_point(p, Socket(bone="arm_l", at=(0.0, 0.5)), art_size=(400, 200))
    (312.0, 512.0)
    """
    from an.stage.rig import (
        bone_positions,
        drawn_attachment,
        rest_transform,
        slot_parent_chain,
    )

    slot = (
        _first_slot(prop_desc)
        if socket.slot is None
        else next((s for s in prop_desc.slots if s.name == socket.slot), None)
    )
    if slot is None:
        raise NotChecked(f"the prop has no slot {socket.slot!r}")
    if slot_parent_chain(prop_desc).get(slot.name) is not None:
        raise NotChecked(
            f"slot {slot.name!r} is nested under another slot (not checked in v1)"
        )
    bone = next((b for b in prop_desc.bones if b.name == slot.bone), None)
    if bone is not None and rest_transform(bone) != {
        "rotation": 0.0,
        "scale_x": 1.0,
        "scale_y": 1.0,
    }:
        raise NotChecked(
            f"bone {bone.name!r} carries a rest rotation or scale (not checked in v1)"
        )
    skin = prop_desc.skins.get("default") or next(iter(prop_desc.skins.values()), None)
    drawn = drawn_attachment(prop_desc, skin, slot) if skin is not None else None
    if drawn is None:
        raise NotChecked(f"slot {slot.name!r} draws no attachment")
    att = drawn[1]
    size = art_size(att.path) if callable(art_size) else art_size
    if not size or not (size[0] > 0 and size[1] > 0):
        # Without the art's own size the runtime contain-fits it inside whatever
        # box is declared, so a (u, v) of the art has no known place.
        raise NotChecked(
            f"the art of slot {slot.name!r} ({att.path}) cannot be measured"
        )
    from an.stage.rig import attachment_box

    box = attachment_box(att.width, att.height, size)
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

    A non-positive scale means the limbs are crossed.

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
    if isinstance(doc, model):
        return doc
    raise TypeError(
        f"expected a {model.__name__} or its document, got {type(doc).__name__}"
    )


def character_model(doc: Any) -> Any:
    """A ``CharacterDescriptor`` from a stored mapping (migrated), or the model as given."""
    from cutan.characters.schema import CHARACTER_DOCUMENT_KIND, CharacterDescriptor

    return _validated(doc, CharacterDescriptor, CHARACTER_DOCUMENT_KIND.name)


def prop_model(doc: Any) -> Any:
    """A ``PropDescriptor`` from a stored mapping (migrated), or the model as given."""
    from an.stage.props import PROP_DOCUMENT_KIND, PropDescriptor

    return _validated(doc, PropDescriptor, PROP_DOCUMENT_KIND.name)


def crossed_limbs_message(name: str, ba: BodyAttachment, character: str) -> str:
    return (
        f"prop {name!r}: its limbs are crossed relative to {character!r}'s bones "
        f"(the art's {ba.sockets[0].bone} side meets the body's other side), so the art "
        f"is drawn from the other side of the body than its declared view {ba.view!r}: "
        "redraw it seen from the shot's camera, or fix the sockets' bones"
    )


def solve_placement(
    prop: Any,
    char: Any,
    ba: BodyAttachment,
    *,
    art_size: ArtSize,
    character_pose: Mapping[str, float],
) -> dict[str, Any]:
    """The placement the declaration gives for a character at ``character_pose``
    (unmirrored, unrotated: :class:`NotChecked` otherwise):
    ``{"at", "scale", "residual_px", "span_px", "targets", "local"}`` where
    ``targets`` are the bones on stage and ``local`` the sockets in the prop's
    own stage units at scale 1. Raises :class:`CrossedLimbs`, :class:`NotChecked`,
    or ``ValueError`` for a bone the character lacks.
    """
    from an.stage.rig import bone_positions

    sx = float(character_pose.get("scale_x", 1.0))
    sy = float(character_pose.get("scale_y", 1.0))
    if sx <= 0 or sy <= 0:
        raise NotChecked("the character is mirrored at the shot's start")
    if abs(float(character_pose.get("rotation", 0.0))) > 1e-9:
        raise NotChecked("the character is rotated at the shot's start")
    if not ba.sockets:
        raise NotChecked("the declaration has no socket")
    bones = bone_positions(char)
    missing = [s.bone for s in ba.sockets if s.bone not in bones]
    if missing:
        raise ValueError(
            f"the character has no bone {', '.join(map(repr, missing))} "
            f"(its bones: {', '.join(sorted(bones))})"
        )
    targets = [
        rig_point_on_stage(char, bones[s.bone], character_pose) for s in ba.sockets
    ]
    unit = {"x": 0.0, "y": 0.0, "scale_x": 1.0, "scale_y": 1.0}
    local = [
        rig_point_on_stage(prop, socket_rig_point(prop, s, art_size=art_size), unit)
        for s in ba.sockets
    ]
    fallback = (ba.scale or 1.0) * sx
    (x, y), s = fit_placement(local, targets, scale=fallback)
    if s <= 0:
        raise CrossedLimbs("crossed")
    placed = [(x + s * q[0], y + s * q[1]) for q in local]
    span = max((math.dist(a, b) for a in targets for b in targets), default=0.0)
    if span <= 0:  # one socket: half the body's bone height stands in for the span
        ys = [p[1] for p in bones.values()]
        span = (max(ys) - min(ys)) * _k(char) * sy / 2.0
    return {
        "at": [x, y],
        "scale": round(s, 4),
        "residual_px": round(max(math.dist(a, b) for a, b in zip(placed, targets)), 2),
        "span_px": span,
        "targets": targets,
        "local": local,
    }


def place_body_prop(
    prop_desc: Any,
    character_desc: Any,
    *,
    character_at: Sequence[float],
    character_scale: float = 1.0,
    art_size: ArtSize,
) -> dict[str, Any]:
    """Where to put a body-depicting prop so its sockets meet the character's bones.

    Returns ``{"at": [x, y], "scale": s, "residual_px": r}``: the prop's
    ``stage.at`` and ``stage.scale`` for a character standing at
    ``character_at`` with ``stage.scale`` ``character_scale`` in its rest view,
    and the largest distance left between a socket and its bone. The compile
    pass does this for every prop placed without ``stage.at``; call it for a
    hand-placed one.

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

    The relation is the character's: at another framing the prop's scale moves
    with the character's, in proportion.

    >>> place_body_prop(wheel, paul, character_at=(0, 0), character_scale=3.0,
    ...                 art_size=(500, 300))["scale"]
    1.35
    """
    char = character_model(character_desc)
    prop = prop_model(prop_desc)
    ba = body_attachment_of(prop)
    if ba is None:
        raise ValueError(f"prop {prop.name!r} declares no {BODY_ATTACHMENT_KEY}")
    pose = {
        "x": character_at[0],
        "y": character_at[1],
        "scale_x": character_scale,
        "scale_y": character_scale,
    }
    try:
        got = solve_placement(prop, char, ba, art_size=art_size, character_pose=pose)
    except CrossedLimbs:
        raise ValueError(
            crossed_limbs_message(prop.name, ba, ba.character or char.name)
        ) from None
    return {k: got[k] for k in ("at", "scale", "residual_px")}


def prop_art_size(props_store: Any, ref: str) -> Callable[[str], Any]:
    """``path -> size`` for a prop's art, by the compiler's own probe."""
    from an.stage.rig import PROP_ART_PREFIX, art_src, part_probe

    probe = part_probe(props_store, art_prefix=PROP_ART_PREFIX)

    def size(path: str):
        if probe is None:
            return None
        return probe(art_src(ref, path, art_prefix=PROP_ART_PREFIX))[1]

    return size


def derive_placement(
    shot: Any, prop_entity: Any, mall: Mapping[str, Any]
) -> tuple[dict | None, str]:
    """``(the derived placement, "")`` of ``prop_entity`` in ``shot``, or
    ``(None, why not)``. Never raises."""
    try:
        props, chars = mall.get("props"), mall.get("characters")
        if props is None or chars is None or prop_entity.ref not in props:
            return None, "the props or characters store is not available"
        raw = props[prop_entity.ref]
        if not isinstance(raw, Mapping) or raw.get("kind") != "PropDescriptor":
            return None, "it is not a PropDescriptor"
        ba = body_attachment_of(raw)
        if ba is None:
            return None, f"it declares no {BODY_ATTACHMENT_KEY}"
        if ba.view == FIRST_PERSON:
            return None, "first-person art has no body on screen to follow"
        if not ba.sockets:
            return None, "its declaration has no socket"
        if len(ba.sockets) == 1 and ba.scale is None:
            return None, "one socket cannot measure the size: declare `scale`"
        who, name = bound_character(shot, prop_entity, ba)
        if who is None or who.ref not in chars:
            return None, f"its character {name!r} is not on stage (or is ambiguous)"
        sets = start_state(shot)
        pose = entity_pose(who, None, sets.get(who.id, {}))
        if pose is None:
            return (
                None,
                f"{name!r} has no `stage.at` (the default layout): place {name!r}",
            )
        char = character_model(chars[who.ref])
        view = character_view(who, char, sets.get(who.id, {}))
        if view != rest_view_of(char):
            return (
                None,
                f"{name!r} starts the shot in the {view!r} view; sockets are declared on its rest view",
            )
        got = solve_placement(
            prop_model(raw),
            char,
            ba,
            art_size=prop_art_size(props, prop_entity.ref),
            character_pose=pose,
        )
        if got["scale"] <= 1e-4:
            return None, "the derived scale is degenerate"
        return {
            "at": got["at"],
            "scale": got["scale"],
            "residual_px": got["residual_px"],
        }, ""
    except CrossedLimbs:
        return None, "its limbs are crossed relative to the character's bones"
    except Exception as e:  # noqa: BLE001 - not derivable; say why
        return None, str(e) or type(e).__name__


def derivable_placement(
    shot: Any, prop_entity: Any, mall: Mapping[str, Any]
) -> dict | None:
    """The derived placement of ``prop_entity`` in ``shot``, or ``None``
    (:func:`derive_placement` says why). Never raises."""
    return derive_placement(shot, prop_entity, mall)[0]
