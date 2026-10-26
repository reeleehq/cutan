"""Hinge limits per part type: how far a cut-out figure's joints may turn (cutan#104).

A rig's bones are hinges (``an.stage.rig.rig_structure``: ``Bone.parent`` is the
joint, ``Bone.limits`` its range). Until now the factory wrote none, so a solved
arm could fold through its own shoulder. The genre knows what a neck, a shoulder,
an elbow, a wrist, a hip and a knee are, so it states the ranges, once, by *part
type*, and a style may loosen or tighten them (a marionette's joints are loose;
``joints.limits`` in a style spec, :mod:`cutan.styles`).

**Convention.** A range is ``(lo, hi)`` degrees about the bone's rest angle,
written for the figure's RIGHT side (the bone ending ``_r``, at the viewer's
right on the unmirrored front view). A positive angle turns the part clockwise
on screen, so a hanging right arm swings its hand toward the viewer's LEFT,
that is toward the body: positive is *inward* (flexion), negative *outward*.
The left side is the mirror image, ``(-hi, -lo)``. A part that is not sided
(the head) is symmetric by construction.

>>> part_type("forearm_r"), part_type("arm_l"), part_type("head"), part_type("torso")
('elbow', 'shoulder', 'neck', None)
>>> limits_for("forearm_r"), limits_for("forearm_l")
((-10.0, 150.0), (-150.0, 10.0))

A style spec overrides by part type; the other types keep the genre's:

>>> limits_table({"joints": {"limits": {"elbow": [0, 90]}}})["elbow"]
(0.0, 90.0)
>>> limits_for("forearm_l", table=limits_table({"joints": {"limits": {"elbow": [0, 90]}}}))
(-90.0, 0.0)

Nothing here changes a character until :func:`apply_limits` (or the factory's
``add_limits``) writes the ranges onto its bones, and a bone's range only acts
when a shot declares a joint, a verb (``pin``, ``pull``, ``join``) or a hold: a
scene that declares none of them compiles byte for byte as it did. A bone added
later (a split arm's) has none until ``add_limits`` runs again.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

__all__ = [
    "GENRE_LIMITS",
    "LOOSE_LIMITS",
    "PART_TYPES",
    "apply_limits",
    "limits_for",
    "limits_table",
    "part_type",
]

#: The part types a bone name stands for, in the order they are tried: a
#: ``forearm_r`` is an elbow before it is an arm. Each pattern reads the bone's
#: name WITHOUT its side suffix (``_l``/``_r``). The names are the factory's
#: (``arm``, ``forearm``, ``hand``, ``leg``, ``shin``) and the ones an
#: illustrator's skeleton uses (``upper_arm``, ``fore``, ``thigh``, ``calf``).
PART_TYPES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("neck", re.compile(r"(neck|head)")),
    ("elbow", re.compile(r"(forearm|fore|lower_arm|elbow)")),
    ("wrist", re.compile(r"(hand|wrist)")),
    ("shoulder", re.compile(r"(arm|upper_arm|shoulder)")),
    ("knee", re.compile(r"(shin|calf|lower_leg|knee)")),
    ("ankle", re.compile(r"(foot|ankle)")),
    ("hip", re.compile(r"(leg|thigh|upper_leg|hip)")),
)

#: The genre's defaults: ``{part type: (lo, hi)}`` degrees about the rest pose,
#: for the right side (see the module's convention). A person's joint, as a
#: cartoon uses it: an elbow folds inward and barely hyperextends, a shoulder
#: swings overhead outward but only crosses the chest so far, a neck tilts but
#: does not roll the head upside down.
GENRE_LIMITS: dict[str, tuple[float, float]] = {
    "neck": (-45.0, 45.0),
    "shoulder": (-180.0, 60.0),
    "elbow": (-10.0, 150.0),
    "wrist": (-70.0, 70.0),
    "hip": (-80.0, 80.0),
    "knee": (-5.0, 140.0),
    "ankle": (-40.0, 40.0),
}

#: Limits that hardly constrain: what a puppet on strings has (the marionette
#: style's ``joints.limits``). Everything can still not fold through itself.
LOOSE_LIMITS: dict[str, tuple[float, float]] = {
    "neck": (-90.0, 90.0),
    "shoulder": (-180.0, 180.0),
    "elbow": (-170.0, 170.0),
    "wrist": (-120.0, 120.0),
    "hip": (-120.0, 120.0),
    "knee": (-170.0, 170.0),
    "ankle": (-80.0, 80.0),
}

#: Part types with no left and right (their range is the same on both sides).
_SYMMETRIC: frozenset[str] = frozenset({"neck"})
_SIDE = re.compile(r"^(?P<stem>.+?)(?:_(?P<side>[lr])|_(?P<word>left|right))$")


def _split_side(bone: str) -> tuple[str, str | None]:
    """``(stem, "l" | "r" | None)`` of a bone name.

    >>> _split_side("forearm_l"), _split_side("head"), _split_side("arm_right")
    (('forearm', 'l'), ('head', None), ('arm', 'r'))
    """
    m = _SIDE.match(bone)
    if m is None:
        return bone, None
    side = m.group("side") or m.group("word")[0]
    return m.group("stem"), side


def part_type(bone: str) -> str | None:
    """The part type a bone's name stands for (a key of :data:`GENRE_LIMITS`), or ``None``.

    A bone with no limbed name (``root``, ``torso``, a prop's ``grip``) has no
    type and no range.

    >>> [part_type(n) for n in ("neck", "arm_r", "fore_r", "hand_l", "leg_l", "shin_r", "root")]
    ['neck', 'shoulder', 'elbow', 'wrist', 'hip', 'knee', None]
    """
    stem, _ = _split_side(bone)
    for name, pattern in PART_TYPES:
        if pattern.fullmatch(stem):
            return name
    return None


def _pair(value: Any, *, where: str) -> tuple[float, float]:
    try:
        lo, hi = (float(v) for v in value)
    except (TypeError, ValueError):
        raise ValueError(f"{where}: a range is [lo, hi] degrees, got {value!r}") from None
    if not -180.0 <= lo <= hi <= 180.0:
        raise ValueError(
            f"{where}: {[lo, hi]} must be [lo, hi] with -180 <= lo <= hi <= 180"
        )
    return lo, hi


def limits_table(
    style: str | Mapping[str, Any] | None = None,
) -> dict[str, tuple[float, float]]:
    """``{part type: (lo, hi)}``: the genre's defaults under a style's ``joints.limits``.

    ``style`` is anything :func:`cutan.styles.resolve_style_spec` reads (a
    shipped name, a path, a spec mapping) or ``None`` for the genre's defaults.
    An unknown part type or a malformed range is refused, by name.

    >>> limits_table() == GENRE_LIMITS
    True
    >>> limits_table({"joints": {"limits": {"elbow": [-170, 170]}}})["elbow"]
    (-170.0, 170.0)
    >>> limits_table({"joints": {"limits": {"tail": [0, 10]}}})
    Traceback (most recent call last):
    ...
    ValueError: style joints.limits: unknown part type 'tail'; known: ankle, elbow, hip, knee, neck, shoulder, wrist
    """
    table = dict(GENRE_LIMITS)
    if style is None:
        return table
    from cutan.styles import resolve_style_spec

    spec = resolve_style_spec(style)
    declared = (spec.get("joints") or {}).get("limits") or {}
    for name, value in declared.items():
        if name not in GENRE_LIMITS:
            raise ValueError(
                f"style joints.limits: unknown part type {name!r}; "
                f"known: {', '.join(sorted(GENRE_LIMITS))}"
            )
        table[name] = _pair(value, where=f"style joints.limits.{name}")
    return table


def limits_for(
    bone: str, *, table: Mapping[str, tuple[float, float]] | None = None
) -> tuple[float, float] | None:
    """The range of a bone by its name, mirrored for the left side; ``None`` for a bone with no type.

    >>> limits_for("head"), limits_for("arm_r"), limits_for("arm_l"), limits_for("root")
    ((-45.0, 45.0), (-180.0, 60.0), (-60.0, 180.0), None)
    """
    kind = part_type(bone)
    if kind is None:
        return None
    lo, hi = (table or GENRE_LIMITS)[kind]
    _, side = _split_side(bone)
    if side == "l" and kind not in _SYMMETRIC:
        lo, hi = -hi, -lo
    return (lo + 0.0, hi + 0.0)


def apply_limits(
    bones: Iterable[Any],
    *,
    table: Mapping[str, tuple[float, float]] | None = None,
    overwrite: bool = False,
) -> list[str]:
    """Write each typed bone's range onto ``bones`` (in place); returns the names written.

    A bone that already has ``limits`` is the artist's and is kept, unless
    ``overwrite``.

    >>> from cutan.characters.schema import Bone
    >>> rig = [Bone(name="arm_r"), Bone(name="fore_r", parent="arm_r"), Bone(name="root"),
    ...        Bone(name="hand_r", parent="fore_r", limits=(-5, 5))]
    >>> apply_limits(rig)
    ['arm_r', 'fore_r']
    >>> [(b.name, b.limits) for b in rig]
    [('arm_r', (-180.0, 60.0)), ('fore_r', (-10.0, 150.0)), ('root', None), ('hand_r', (-5.0, 5.0))]
    """
    written: list[str] = []
    for bone in bones:
        if bone.limits is not None and not overwrite:
            continue
        found = limits_for(bone.name, table=table)
        if found is None:
            continue
        bone.limits = found
        written.append(bone.name)
    return written
