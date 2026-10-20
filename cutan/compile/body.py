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

Nothing changes for a stored scene: no prop declared a body attachment before
this existed, and a prop that declares none is never touched.

>>> from an.ir.schema import Shot
>>> derive_body_placements(Shot(id="s"), {}).id
's'
"""

from __future__ import annotations

from typing import Any, Mapping

__all__ = ["derive_body_placements", "_body_placement_pass"]


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
    entities, changed = [], False
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
        changed = True
    return shot.model_copy(update={"entities": entities}) if changed else shot


def _body_placement_pass(state: Any) -> None:
    """Cut-out: body-attached props placed by their body, before the scene is built."""
    state.shot = derive_body_placements(state.shot, state.mall)
