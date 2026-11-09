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
tested without a store or a scene; :func:`check_eyeline` is the adapter from a
scene's resolved timelines, and ``cutout.eyeline`` registers it on the genre.

Only a view that SHOWS a direction is judged (:data:`DIRECTIONAL_VIEWS`: the profile
and the three-quarter). A ``front`` character looks at the camera, and mirroring it
is invisible as an eyeline (gaze, not facing, directs it); a ``back`` one looks away
from it. Lines are judged at their start AND end, and warned only when the speaker
faces wrongly at both: a turn toward the listener during the line is the author's fix.

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
from typing import Any, Callable, Optional, Sequence

from cutan.characters.checks import _rig_document, _turns_of
from cutan.characters.play import facing_at
from cutan.characters.schema import DFLT_VIEW, CharacterDescriptor

#: What a character faces when nothing set it: the rig's rest (``scale_x`` > 0; the
#: factory draws its profile facing the viewer's right).
REST_DIRECTION: str = "right"
#: The views that show a direction on screen; any other view is not judged.
DIRECTIONAL_VIEWS: frozenset[str] = frozenset({"side", "three_quarter"})
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


def _presence(
    entity: Any,
    events: Any,
    t: float,
    *,
    speaker: str | None,
    rest_view: str,
    directional_views: frozenset[str],
    rest_direction: str,
) -> Presence:
    """``entity`` of a shot as the rules see it at ``t``."""
    facing = facing_at(events, entity.id, t)
    view = facing.view or rest_view
    at = entity.stage.at if entity.stage is not None else None
    return Presence(
        entity.id,
        direction=(facing.direction or rest_direction)
        if view in directional_views
        else None,
        x=float(at[0]) if at else None,
        speaks=entity.id == speaker,
    )


def _share_a_place(a: Any, b: Any) -> bool:
    """Whether two shots show the same set: a non-character entity (an environment,
    a prop) with the same ``ref`` in both. Two single-character shots in different
    places are two scenes, not a shot and its reverse."""

    def places(shot: Any) -> set[tuple[str, str]]:
        return {(e.kind, e.ref) for e in shot.entities if e.kind != "character"}

    return bool(places(a) & places(b))


def check_eyeline(
    ctx: Any,
    *,
    directional_views: frozenset[str] = DIRECTIONAL_VIEWS,
    rest_direction: str = REST_DIRECTION,
    share_a_place: Callable[[Any, Any], bool] = _share_a_place,
) -> None:
    """The cut-out genre's eyeline warnings: a speaker facing away from the one
    character it speaks to, and a shot/reverse-shot pair whose speakers face the
    same way. Needs the characters store, like the other turn checks (without it
    the check did not run). Keyword-only parameters are the seams a host
    registers its own check with (``functools.partial``): the views that show a
    direction, what a character faces at rest, and what makes two shots one place.
    """
    from an.ir.validate import _dialogue_layout  # TODO an#767: a public layout

    shots = ctx.shots
    resolved = [_turns_of(ctx, i, shot) for i, shot in enumerate(shots)]
    if any(r is None for r in resolved):
        return
    chars = [[e for e in shot.entities if e.kind == "character"] for shot in shots]
    lines = [list(_dialogue_layout(shot)) for shot in shots]

    def rest_view_of(entity: Any) -> str:
        doc = _rig_document(entity, ctx.stores)
        try:
            return (
                CharacterDescriptor.model_validate(doc).rest_view if doc else DFLT_VIEW
            )
        except Exception:  # noqa: BLE001 - a malformed descriptor is the play check's to report
            return DFLT_VIEW

    def present_at(i: int, t: float, speaker: str) -> list[Presence]:
        return [
            _presence(
                e,
                resolved[i][0].events,
                t,
                speaker=speaker,
                rest_view=rest_view_of(e),
                directional_views=directional_views,
                rest_direction=rest_direction,
            )
            for e in chars[i]
        ]

    for i in range(len(shots)):
        for k, line, start, end, _estimated in lines[i]:
            at_start = {
                f.entity for f in shot_findings(present_at(i, start, line.speaker))
            }
            for f in shot_findings(present_at(i, end, line.speaker)):
                if f.entity in at_start:  # wrong all through the line
                    ctx.report.add("warning", f"timeline/{i}/dialogue/{k}", f.message)
    for i in range(1, len(shots)):
        if not (lines[i - 1] and lines[i]) or not share_a_place(shots[i - 1], shots[i]):
            continue
        _, last, last_start, *_ = lines[i - 1][-1]
        _, first, first_start, *_ = lines[i][0]
        before = present_at(i - 1, last_start, last.speaker)
        after = present_at(i, first_start, first.speaker)
        if before and after and before[0].speaks and after[0].speaks:
            for f in cut_findings(before, after):
                ctx.report.add("warning", f"timeline/{i}/entities", f.message)


__all__ = [
    "DIRECTIONAL_VIEWS",
    "check_eyeline",
    "REST_DIRECTION",
    "EyelineFinding",
    "Presence",
    "cut_findings",
    "shot_findings",
]
