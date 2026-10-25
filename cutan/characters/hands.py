"""A character's hands as named points: ``ned@hand_r`` (an#502, reeleehq/cutan#104).

The core's hold verbs (``grasp``, ``place``, ``release``, ``handover``,
``swap``: ``an.ir.holds``) move a point of a body, and the core knows no part
by name. A cut-out character's rig contract does: its arms are the slots
``arm_l`` and ``arm_r`` (``arm_l`` the viewer's left on the unmirrored rig),
and whatever hangs from them (a forearm under ``nesting: bones``, a ``hand_r``
part) is the rest of the arm. So the genre names the hands for the core
(:attr:`an.genres.EntityKind.landmarks`):

- a rig with a ``hand_l`` / ``hand_r`` BONE needs nothing from here: the core
  reads a bone as a point first (a grip landmark, cutan#104's hand bone);
- a rig with a ``hand_l`` / ``hand_r`` SLOT (a drawn hand) holds at the
  middle of that drawing;
- otherwise the hand is the far end of the last part of the arm's chain (the
  arm itself on a one-piece arm, the forearm on a bent one): its end effector.

So ``{kind: grasp, by: stu@hand_r, item: musket}`` works on a factory
character, a carved one with one-stroke arms, and one with an elbow, and keeps
working when the rig gains hand bones.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

__all__ = ["HANDS", "character_landmarks"]

#: The hands the genre names, and the arm slot each one ends.
HANDS: dict[str, str] = {"hand_l": "arm_l", "hand_r": "arm_r"}
#: Where a drawn hand holds things: the middle of its drawing.
HAND_CENTRE: tuple[float, float] = (0.5, 0.5)


def _field(doc: Any, name: str, default: Any = None) -> Any:
    if isinstance(doc, Mapping):
        return doc.get(name, default)
    return getattr(doc, name, default)


def _named(entries: Any) -> dict[str, Any]:
    return {str(_field(e, "name")): e for e in entries or ()}


def character_landmarks(desc: Any) -> dict[str, tuple[str, tuple[float, float] | None]]:
    """``{hand: (slot, point)}`` for a character descriptor: the slot whose part
    holds things for that hand, and the point on it (a fraction of its drawing,
    or ``None``: its far end).

    >>> rig = {"bones": [{"name": "torso"}, {"name": "arm_r", "parent": "torso"},
    ...                  {"name": "fore_r", "parent": "arm_r"}, {"name": "arm_l", "parent": "torso"}],
    ...        "slots": [{"name": "torso", "bone": "torso"}, {"name": "arm_r", "bone": "arm_r"},
    ...                  {"name": "fore_r", "bone": "fore_r"}, {"name": "arm_l", "bone": "arm_l"}]}
    >>> character_landmarks(rig)
    {'hand_l': ('arm_l', None), 'hand_r': ('fore_r', None)}
    >>> rig["slots"].append({"name": "hand_l", "bone": "arm_l"})
    >>> character_landmarks(rig)["hand_l"]
    ('hand_l', (0.5, 0.5))
    """
    bones = _named(_field(desc, "bones"))
    slots = _named(_field(desc, "slots"))

    def depth_under(bone: str, root: str) -> int | None:
        """How many links ``bone`` is below ``root`` (``None``: not under it)."""
        d, cursor, seen = 0, bone, set()
        while cursor is not None and cursor not in seen:
            if cursor == root:
                return d
            seen.add(cursor)
            d += 1
            cursor = _field(bones.get(cursor), "parent") if cursor in bones else None
        return None

    out: dict[str, tuple[str, tuple[float, float] | None]] = {}
    for hand, arm in HANDS.items():
        if hand in bones or arm not in slots:
            continue  # a hand bone is read by the core; no arm, no hand
        if hand in slots:
            out[hand] = (hand, HAND_CENTRE)
            continue
        arm_bone = str(_field(slots[arm], "bone"))
        best, best_depth = arm, 0
        for name, slot in sorted(slots.items()):
            depth = depth_under(str(_field(slot, "bone")), arm_bone)
            if depth is not None and depth > best_depth:
                best, best_depth = name, depth
        out[hand] = (best, None)
    return out
