"""The eyeline lint: do two characters in an exchange look at each other?

Two rules, both advisory (a warning is the author's to override on purpose), both
about the SIGN a character faces (``scale_x``), the only facing a flat timeline
carries (:func:`cutan.characters.play.facing_at`):

* **Within a shot** (:func:`shot_findings`): a character speaking to the one other
  character on screen should face their side of the frame. ``at: [x, y]`` places
  them; a speaker left of the listener who faces left looks away.
* **Across a cut** (:func:`cut_findings`): a shot/reverse-shot pair keeps the line
  (the 180-degree rule). ``A`` speaks alone in one shot, ``B`` answers alone in the
  next; ``A`` should face one way and ``B`` the other. Both facing the same way
  makes the cut jump the line, and the pair read as one looking past the other.

The rules are pure functions over small records (:class:`Presence`), so they are
tested without a store or a scene; :func:`eyeline_findings` is the adapter from a
scene's resolved timelines, and ``cutout.eyeline`` registers it on the genre.
Facing that is not a direction (a ``back`` view, no facing known) is not judged.

>>> a = Presence("ana", direction="right", x=-1.0, speaks=True)
>>> b = Presence("ben", direction="left", x=1.0)
>>> shot_findings([a, b])
[]
>>> [f.entity for f in shot_findings([Presence("ana", "left", -1.0, True), b])]
['ana']
>>> cut_findings([a], [Presence("ben", "right", 0.0, True)])[0].entity
'ben'
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

#: What a character faces when nothing set it: the rig's rest (``scale_x`` > 0).
REST_DIRECTION: str = "right"
#: Views whose facing is not a direction on screen (the character shows its back).
UNJUDGED_VIEWS: frozenset[str] = frozenset({"back"})
_OPPOSITE = {"left": "right", "right": "left"}


@dataclass(frozen=True)
class Presence:
    """A character on screen at one instant of a shot.

    ``direction`` is ``"left"``/``"right"``, or ``None`` when it is not judged (a
    view that shows no direction); ``x`` its horizontal screen position, or
    ``None`` when the shot does not place it; ``speaks`` whether it is the shot's
    speaker in the exchange.
    """

    entity: str
    direction: Optional[str] = None
    x: Optional[float] = None
    speaks: bool = False


@dataclass(frozen=True)
class EyelineFinding:
    """One thing to warn about: which entity, and what is wrong with its facing."""

    entity: str
    message: str


def shot_findings(present: Sequence[Presence]) -> list[EyelineFinding]:
    """A speaker facing away from the one other character in the shot.

    Judged only with exactly one other character, both placed, at different ``x``
    and a known direction: with more people the addressee is not knowable here.
    """
    speakers = [p for p in present if p.speaks]
    others = [p for p in present if not p.speaks]
    if len(speakers) != 1 or len(others) != 1:
        return []
    speaker, other = speakers[0], others[0]
    if None in (speaker.x, other.x, speaker.direction) or speaker.x == other.x:
        return []
    toward = "right" if other.x > speaker.x else "left"
    if speaker.direction == toward:
        return []
    return [
        EyelineFinding(
            speaker.entity,
            f"{speaker.entity!r} speaks to {other.entity!r}, who stands to its "
            f"{toward}, but faces {speaker.direction}: a negative `scale_x` turns "
            "it, or `at` puts the two the other way round.",
        )
    ]


def cut_findings(
    before: Sequence[Presence], after: Sequence[Presence]
) -> list[EyelineFinding]:
    """A shot/reverse-shot pair whose speakers face the same way (the line is jumped).

    Judged only for a true pair: each shot holds exactly one character, and they
    differ. The finding is on the second shot's character, the one to turn.
    """
    if len(before) != 1 or len(after) != 1:
        return []
    first, second = before[0], after[0]
    if first.entity == second.entity or None in (first.direction, second.direction):
        return []
    if second.direction != first.direction:
        return []
    return [
        EyelineFinding(
            second.entity,
            f"{first.entity!r} faces {first.direction} and {second.entity!r} "
            f"answers facing {second.direction} across the cut: the pair does not "
            f"look at each other (the 180-degree rule). Turn {second.entity!r} to "
            f"face {_OPPOSITE[second.direction]} (a negative `scale_x` set at 0).",
        )
    ]


__all__ = [
    "REST_DIRECTION",
    "UNJUDGED_VIEWS",
    "EyelineFinding",
    "Presence",
    "cut_findings",
    "shot_findings",
]
