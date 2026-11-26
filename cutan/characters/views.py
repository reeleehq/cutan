"""The rig view a character shows from where the camera sees it (cutan#173 part 1).

``an`` gives a world member a ``facing`` and asks its kind, per framed shot, what
shows it from the camera's angle (``EntityKind.view_for``, ``an.genres.API_LEVEL``
20, an#734). :func:`character_view_for` answers for a character: the view of its
declared ``view`` swap set whose yaw range holds the camera's angle about the
character, as a ``set`` of that swap at ``t=0``. ``an`` puts it ahead of the shot's
own actions, so an author's explicit ``view`` swap wins.

The angle is the camera's yaw relative to where the character faces: ``0`` the
camera is in front of it, ``±180`` behind, positive when it faces screen-right.
:data:`VIEW_YAW_RANGES` says which view serves which ``|yaw|``. A view the
character does not draw (no ``view`` set, or a set without that key) is not asked
for: it keeps the view it has. A character drawn with only a front and a side view,
say, shows the side from a quarter turn on and the front before it, rather than a
key it has no art for.

**Which way a profile faces.** A directional drawing (``side``, ``three_quarter``)
faces the way its art says (``metadata.faces``, right by default); mirroring it is
a negative ``scale_x``, which a view's actions cannot give yet (it would replace the
world's scale: reeleehq/an#868). So a profile is given only on the side its art
faces; on the other side the character is shown from the front (or the back, past a
quarter turn away). The same gap means a character the author mirrors by hand at
``t=0`` is not looked at: it keeps its mirror.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from cutan.characters.schema import (
    DIRECTIONAL_VIEWS,
    VIEW_CHANNEL,
    VIEWS,
    CharacterDescriptor,
)

#: ``(upper bound of |relative yaw| in degrees, view)``, in order: the first whose
#: bound is not under the yaw serves it; the last bound must be 180. The
#: bounds split each step between two drawn views in half (front 0, three-quarter
#: 45, side 90, back 180: the back from behind-three-quarters on, which the rig
#: does not draw separately).
VIEW_YAW_RANGES: tuple[tuple[float, str], ...] = (
    (22.5, "front"),
    (67.5, "three_quarter"),
    (112.5, "side"),
    (180.0, "back"),
)


def view_for_yaw(
    relative_yaw: float,
    *,
    available: Sequence[str] = VIEWS,
    ranges: Sequence[tuple[float, str]] = VIEW_YAW_RANGES,
) -> str | None:
    """The view for a camera at ``relative_yaw`` degrees about a character, among
    the ``available`` ones; ``None`` when it draws none of them.

    A range whose view is not drawn falls to the nearest drawn view toward the
    front (a character with no three-quarter shows its front until the side).

    >>> view_for_yaw(0.0), view_for_yaw(-40.0), view_for_yaw(90.0), view_for_yaw(180.0)
    ('front', 'three_quarter', 'side', 'back')
    >>> view_for_yaw(40.0, available=("front", "side"))
    'front'
    >>> view_for_yaw(10.0, available=("side",)) is None
    True
    """
    angle = abs(float(relative_yaw))
    order = [view for _, view in ranges]
    for i, (bound, view) in enumerate(ranges):
        if angle <= bound:
            for candidate in reversed(order[: i + 1]):  # toward the front
                if candidate in available:
                    return candidate
            return None
    return None


def _descriptor(
    entity: Any, mall: Mapping[str, Any] | None
) -> CharacterDescriptor | None:
    """``entity``'s descriptor as it plays it (its ``overrides.faces`` applied), or
    ``None`` for a character with none (procedural, placeholder, unknown ref)."""
    if not mall:
        return None
    from cutan.characters.play import with_entity_faces
    from cutan.compile.lowering import character_swap_declaration

    desc = getattr(character_swap_declaration(entity, mall), "descriptor", None)
    if not isinstance(desc, CharacterDescriptor):
        return None
    return with_entity_faces(entity, desc)


def character_view_for(
    entity: Any, mall: Mapping[str, Any] | None, relative_yaw: float
) -> list[Any] | None:
    """``EntityKind.view_for`` for a character (an#734): a ``set`` of its ``view``
    swap at ``t=0`` to the view that shows it from the camera's angle, or ``None``
    when it draws no ``view`` set, or the view in force is already the one.

    A directional view is given only when its art faces the side the camera sees
    the character face (:func:`cutan.characters.play.art_facing`: right for
    ``+yaw``, left for ``-yaw``); otherwise the character is shown from the front
    (or the back, past a quarter turn away), which needs no mirror.

    >>> from an.ir.schema import AssetRef
    >>> ghost = AssetRef(kind="character", id="ned", store="characters", ref="ned")
    >>> character_view_for(ghost, {}, 0.0) is None
    True
    """
    from an.ir.schema import SetAction

    from cutan.characters.play import art_facing, declared_faces

    desc = _descriptor(entity, mall)
    drawn = tuple((desc.asset_sets.get(VIEW_CHANNEL) or ())) if desc else ()
    view = view_for_yaw(relative_yaw, available=drawn) if drawn else None
    if view is None:
        return None
    if view in DIRECTIONAL_VIEWS:
        way = "right" if relative_yaw > 0 else "left"
        if art_facing(declared_faces(desc), {VIEW_CHANNEL: view}) != way:
            # a mirror, which a view's actions cannot give yet (an#868)
            view = view_for_yaw(
                0.0 if abs(relative_yaw) <= 90.0 else 180.0, available=drawn
            )
    if view is None or view == getattr(desc, "rest_view", None):
        return None
    return [SetAction(target=entity.id, property=VIEW_CHANNEL, value=view, at=0.0)]
