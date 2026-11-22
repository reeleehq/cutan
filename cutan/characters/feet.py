"""A character's feet as named points: ``paul@foot_l`` (an#519, cutan#201).

The core's support check (``{type: support, a: paul, b: ground}``, an#797) needs
the points of a body that touch what it stands on. The core derives them from
the rig's origin or its ink when the genre names none; a cut-out character's rig
contract names them: its legs are the slots ``leg_l`` and ``leg_r``, so the genre
gives the core ``foot_l`` / ``foot_r``
(:attr:`an.genres.EntityKind.contacts`), as :mod:`cutan.characters.hands` gives
it the hands:

- a rig with a ``foot_l`` / ``foot_r`` BONE needs nothing from here (the core
  reads a bone as a point first);
- a rig with a ``foot_l`` / ``foot_r`` SLOT (a drawn shoe) stands on the bottom
  centre of that drawing, its sole;
- otherwise the foot is the far end of the last part of the leg's chain, from
  its pivot: the leg's drawn bottom. A factory rig has no foot bone, so this is
  its foot; for a leg that swings from the hip it sweeps an arc, so a hip-swing
  walk's feet leave the floor at the contact pose by ``L * (1 - cos(stride))``
  (the geometry of a cut-out walk, recorded in cutan#201).

A rig with no leg slots gives nothing and the core falls to the rig's origin.
"""

from __future__ import annotations

from typing import Any

from cutan.characters.hands import _field, _named, far_slot

__all__ = ["FEET", "FOOT_SOLE", "character_contacts"]

#: The feet the genre names, and the leg slot each one ends (the rig contract's
#: leg names, ``cutan.motion.WALK_LEG_NAMES``).
FEET: dict[str, str] = {"foot_l": "leg_l", "foot_r": "leg_r"}
#: Where a drawn foot stands: the bottom centre of its drawing, the sole.
FOOT_SOLE: tuple[float, float] = (0.5, 1.0)


def character_contacts(desc: Any) -> dict[str, tuple[str, tuple[float, float] | None]]:
    """``{foot: (slot, point)}`` for a character descriptor: the slot whose part
    touches the ground for that foot, and the point on it (a fraction of its
    drawing, or ``None``: its far end from its pivot).

    >>> rig = {"bones": [{"name": "root"}, {"name": "leg_l", "parent": "root"}],
    ...        "slots": [{"name": "leg_l", "bone": "leg_l"}]}
    >>> character_contacts(rig)
    {'foot_l': ('leg_l', None)}
    >>> rig["slots"].append({"name": "foot_l", "bone": "leg_l"})
    >>> character_contacts(rig)["foot_l"]
    ('foot_l', (0.5, 1.0))
    >>> character_contacts({"bones": [], "slots": []})
    {}
    """
    bones = _named(_field(desc, "bones"))
    slots = _named(_field(desc, "slots"))
    out: dict[str, tuple[str, tuple[float, float] | None]] = {}
    for foot, leg in FEET.items():
        if foot in bones or leg not in slots:
            continue  # a foot bone is read by the core; no leg, no foot
        if foot in slots:
            out[foot] = (foot, FOOT_SOLE)
            continue
        out[foot] = (far_slot(bones, slots, leg), None)
    return out
