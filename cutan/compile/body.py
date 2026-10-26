"""Derive a body-attached prop's placement from its character, in every shot.

A prop that declares ``metadata.body_attachment`` (:mod:`cutan.body_attachment`)
and is placed WITHOUT ``stage.at`` is placed by its body: before the scene is
built (the ``body_placement`` compile pass, order 90), its ``stage.at`` and
``stage.scale`` are derived from where its character stands in this shot, by
:func:`cutan.body_attachment.place_body_prop`. The attachment is then declared
once, in the character's own units (its bones), and every framing (a two-shot,
a close-up) derives the same relation: the prop's size relative to the
character and its anchor on the body cannot drift between shots.

A prop placed WITH ``stage.at`` keeps the author's placement, and
``cutout.body_attachment`` checks it against the same derivation.

**The prop follows the body through the shot** (cutan#104, the constraint
layer): a prop placed by its body whose character moves in the shot (an
authored tween or play on it or its parts, or a joint, a verb or a hold that
makes the shot solve) gets one ``pin`` per socket, from the socket's point on
its art to the character's bone, held for the whole shot. The ``solve`` pass
then keeps the sockets on the bones as the torso nods or the shoulders move,
and ``an validate`` (``cutout.body_attachment``, which reads the compiled
shot's solve report: the pins are added at compile, after the core's joint
checks look) reports a pin the motion pulls off its bone, with the time, and a
prop whose sockets do not fit the bones, which is placed once. A prop with authored motion of its own is
left to that motion. A shot where the character holds still gets none, and
compiles as it always did.

Nothing changes for a stored scene: no prop declared a body attachment before
this existed, and a prop that declares none is never touched.

>>> from an.ir.schema import Shot
>>> derive_body_placements(Shot(id="s"), {}).id
's'
"""

from __future__ import annotations

from typing import Any, Mapping

__all__ = [
    "MOTION_KINDS",
    "MOTION_PROPERTIES",
    "PIN_RESIDUAL_PX",
    "body_attachment_pins",
    "why_not_followed",
    "derive_body_placements",
    "_body_placement_pass",
]

#: How far (px) the derived placement may leave a socket from its bone and still
#: be followed by a pin: a hard pin holds the point exactly, so a mismatch beyond
#: this would drag the prop off its derived place (and, with several sockets,
#: fight the others and be given up). Such a prop is placed once, as before.
PIN_RESIDUAL_PX: float = 0.5
#: The action kinds that move the parts of the entity they name.
MOTION_KINDS: frozenset[str] = frozenset({"tween", "play"})
#: The properties of a ``tween`` that move a part (not its look).
MOTION_PROPERTIES: frozenset[str] = frozenset(
    {"x", "y", "rotation", "scale_x", "scale_y", "rotation_rad"}
)


def derive_body_placements(shot: Any, mall: Mapping[str, Any]) -> Any:
    """``shot`` with every body-attached prop that has no ``stage.at`` placed by
    its body. Returns ``shot`` itself when nothing is derived. A prop whose
    placement cannot be derived (no character in the shot, the character in the
    default layout or mirrored, a socket naming a missing bone, unmeasurable
    art, crossed limbs) is left as it is: ``cutout.body_attachment`` says why.
    """
    from an.ir.schema import StagePlacement

    from cutan.body_attachment import derivable_placement

    props = (mall or {}).get("props")
    if props is None or not any(e.kind == "prop" for e in shot.entities):
        return shot
    entities, pins, changed = [], [], False
    for entity in shot.entities:
        placed = None
        if entity.kind == "prop" and (entity.stage is None or entity.stage.at is None):
            placed = derivable_placement(shot, entity, mall)
        if placed is None:
            entities.append(entity)
            continue
        after = entity.stage.after if entity.stage is not None else None
        stage = StagePlacement(
            at=tuple(placed["at"]), scale=placed["scale"], after=after
        )
        entities.append(entity.model_copy(update={"stage": stage}))
        pins += body_attachment_pins(shot, entity, mall, placed=placed)
        changed = True
    if not changed:
        return shot
    update: dict[str, Any] = {"entities": entities}
    if pins:
        update["actions"] = [*shot.actions, *pins]
    return shot.model_copy(update=update)


def _moves(shot: Any, entity_id: str) -> bool:
    """Whether the shot's authored actions move ``entity_id`` or a part of it."""
    from an.motion import flatten

    for action in shot.actions:
        try:
            leaves = flatten(action)
        except Exception:  # noqa: BLE001 - an unresolvable action is another check's
            continue
        for leaf in leaves:
            a = leaf.action
            kind = getattr(a, "kind", None)
            target = str(getattr(a, "target", "") or "")
            if kind not in MOTION_KINDS or target.split("/", 1)[0] != entity_id:
                continue
            if (
                kind == "tween"
                and getattr(a, "property", None) not in MOTION_PROPERTIES
            ):
                continue
            return True
    return False


def why_not_followed(
    shot: Any,
    prop_entity: Any,
    mall: Mapping[str, Any],
    *,
    placed: Mapping[str, Any] | None = None,
) -> str:
    """Why a body-attached prop that moves with its character is NOT given pins
    ('' when it is followed, or when there is nothing to follow). For ``an
    validate``: the prop would be placed once and left behind by the motion."""
    from an.stage.solve import shot_declares_solve

    from cutan.body_attachment import (
        body_attachment_of,
        bound_character,
        derive_placement,
    )

    ba = body_attachment_of(mall["props"][prop_entity.ref])
    who, _ = bound_character(shot, prop_entity, ba)
    if ba is None or who is None or not ba.sockets:
        return ""
    if not (_moves(shot, who.id) or shot_declares_solve(shot, mall)):
        return ""
    if _moves(shot, prop_entity.id):
        return "the prop has motion of its own, which wins"
    if placed is None:
        placed, why = derive_placement(shot, prop_entity, mall)
        if placed is None:
            return why
    residual = float(placed.get("residual_px", 0.0))
    if residual > PIN_RESIDUAL_PX:
        return (
            f"its sockets sit {residual:.1f} px from the bones they name even at the best "
            "placement (the art's sockets do not match the body's proportions): "
            "fix the declared `at` points"
        )
    return ""


def body_attachment_pins(
    shot: Any,
    prop_entity: Any,
    mall: Mapping[str, Any],
    *,
    placed: Mapping[str, Any] | None = None,
) -> list[Any]:
    """The ``pin`` actions that keep a body-attached prop's sockets on its character's bones.

    One per socket, from the socket's point on the prop's art
    (``<prop>/<slot>@u,v``) to the bone, on the part of the character that sits
    on it (``<character>/<slot>@<bone>``), for the whole shot. Empty unless the
    character moves (:func:`_moves`, or the shot already solves: a joint, a
    verb or a hold), the prop has no motion of its own, and every socket's bone
    carries a part, and the derived placement leaves every socket within
    :data:`PIN_RESIDUAL_PX` of its bone (``placed``: the derivation, else made
    here). Never raises: a prop that cannot be followed is placed once, as it
    always was (:func:`why_not_followed` says why, for ``an validate``).
    """
    try:
        from an.ir.joints import PinAction
        from an.stage.solve import shot_declares_solve

        from cutan.body_attachment import (
            body_attachment_of,
            bound_character,
            character_model,
            prop_model,
        )

        raw = mall["props"][prop_entity.ref]
        ba = body_attachment_of(raw)
        who, _ = bound_character(shot, prop_entity, ba)
        if ba is None or who is None or not ba.sockets:
            return []
        if not (_moves(shot, who.id) or shot_declares_solve(shot, mall)):
            return []  # nothing to follow
        if why_not_followed(shot, prop_entity, mall, placed=placed):
            return []
        prop, char = prop_model(raw), character_model(mall["characters"][who.ref])
        first = sorted(prop.slots, key=lambda s: (s.draw_order, s.name))[0]
        by_draw = sorted(char.slots, key=lambda s: (s.draw_order, s.name))
        pins = []
        for socket in ba.sockets:
            on_bone = [s.name for s in by_draw if s.bone == socket.bone]
            if not on_bone:
                return []
            carrier = socket.bone if socket.bone in on_bone else on_bone[0]
            u, v = socket.at
            pins.append(
                PinAction(
                    point=f"{prop_entity.id}/{socket.slot or first.name}@{float(u)!r},{float(v)!r}",
                    to=f"{who.id}/{carrier}@{socket.bone}",
                )
            )
        return pins
    except Exception:  # noqa: BLE001 - not followable; the placement stands
        return []


def _body_placement_pass(state: Any) -> None:
    """Cut-out: body-attached props placed by their body, before the scene is built."""
    state.shot = derive_body_placements(state.shot, state.mall)
