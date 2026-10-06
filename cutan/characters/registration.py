"""The character side of the cut-out genre, as declarations: ``play`` and ``character``.

What the cut-out genre (:mod:`cutan.genre`) registers from here (ADR 0001
§First slice):

- the **``play`` action kind** — :class:`PlayAction`, how long a
  duration-less play occupies a ``sequence`` (its natural length, through the
  caller's extent resolver), and its ``scene.md`` spelling;
- the **``character`` entity kind** — a rigged character, whose nodes are
  nodes of the 2D stage engine (the ``stage.node`` property space).

Plain declarations: importing this module registers nothing.

>>> PLAY.name, CHARACTER.space
('play', 'stage.node')
"""

from __future__ import annotations

from typing import Any

from an.genres.registry import ActionKind, EntityKind
from typing import Literal

from pydantic import model_serializer

from an.ir.compose import delay, flatten, sequence  # noqa: F401  (doctests)
from an.ir.schema import ExtensionAction, PathStr, Seconds


class PlayAction(ExtensionAction):
    """Play a named animation of the target entity's descriptor (an#7).

    ``animation`` names an entry of ``CharacterDescriptor.animations`` (the
    seeded ``idle_breath`` and ``blink``, or anything an author adds); the
    compiler resolves its tracks into channels on the entity's nodes. A name
    the descriptor does NOT declare — or any name on an entity with no
    descriptor (a procedural rig, a prop) — falls back to the motion presets
    of :data:`cutan.motion.PRESETS` (``hop``, ``nod``, …), which expand to
    ordinary tweens at the target's built rest pose; a descriptor animation of
    the same name wins (an#166). Both halves are decided by
    :func:`cutan.characters.play.play_problems`, the one resolver ``an validate``
    and the compiler share. For a preset, ``args`` are its parameters,
    ``duration`` stretches the whole move to that length, ``speed`` divides
    it, and ``loop: true`` is refused (a preset is a one-shot).
    ``duration`` widens/narrows the placement window; ``None`` means the
    animation's own duration — or, when the resolved ``loop`` is true, the
    rest of the shot, because a loop bounded by its own natural duration
    never loops. ``loop`` overrides the animation's declared ``loop``
    (``None`` = use the descriptor's). Inside a ``sequence`` a play with
    ``duration=None`` occupies its NATURAL length — a motion preset's own
    length, a non-looping descriptor animation's ``duration``, both over
    ``speed`` — so the next sibling starts when it ends; a looping one runs to
    the shot end and occupies ZERO (:func:`an.characters.play.play_extent`).
    """

    kind: Literal["play"] = "play"
    target: PathStr
    animation: str  # a key of the entity descriptor's `animations`
    duration: Seconds | None = None  # None = the animation's natural duration
    speed: float = 1.0
    loop: bool | None = None  # None = the descriptor animation's own `loop`
    #: Parameters of a MOTION PRESET (an#166) — ``{"height": 30}`` for a
    #: ``hop`` — passed to its :data:`cutan.motion.PRESETS` function as keyword
    #: arguments. ``None`` (the default, omitted from JSON) means the preset's
    #: own defaults. A descriptor animation takes none, and one given to it is
    #: refused; ``rest`` is never one — it is read off the built scene.
    args: dict[str, Any] | None = None

    @model_serializer(mode="wrap")
    def _omit_unset_args(self, handler):
        """``args: null`` leaves no trace: every committed ``scene.json`` with
        a ``play`` predates the field (the an#112 omit-when-unset rule)."""
        data = handler(self)
        if isinstance(data, dict) and data.get("args") is None:
            data.pop("args", None)
        return data


def play(
    target: PathStr,
    animation: str,
    *,
    duration: Seconds | None = None,
    speed: float = 1.0,
    loop: bool | None = None,
    args: dict[str, Any] | None = None,
) -> PlayAction:
    """Play a named animation of the target entity's descriptor (an#7).

    ``duration=None`` fills the animation's natural length — or the shot's
    remainder for a looping one. In a ``sequence`` a play with no ``duration``
    occupies its **natural** length (a motion preset's own length divided by
    ``speed``; a non-looping descriptor animation's likewise), so the sibling
    after it starts when it ends; a looping one runs to the shot end and
    occupies **zero**:

    >>> [f.start for f in flatten(sequence(play("a", "idle_breath"), delay(1.0), play("a", "blink")))]
    [0.0, 1.0]
    >>> [f.start for f in flatten(sequence(play("a", "idle_breath", duration=2.0), play("a", "blink")))]
    [0.0, 2.0]
    >>> [f.start for f in flatten(sequence(play("a", "hop"), play("a", "nod")))]
    [0.0, 0.5]
    >>> [f.start for f in flatten(sequence(play("a", "hop", speed=2.0), play("a", "nod")))]
    [0.0, 0.25]

    (Bare ``flatten`` knows only the presets, by name; ``an validate`` and the
    compiler pass the entity's descriptor too — :func:`cutan.characters.play.play_extent`
    — so a descriptor animation that shares a preset's name is measured as the
    descriptor's.)

    A name the descriptor does not declare falls back to a motion preset of
    :data:`cutan.motion.PRESETS`, with ``args`` as its parameters (an#166):

    >>> play("charlie", "hop", args={"height": 30}).args
    {'height': 30}
    """
    return PlayAction(
        target=target,
        animation=animation,
        duration=duration,
        speed=speed,
        loop=loop,
        args=args,
    )


def default_play_extent(action: PlayAction) -> Seconds:
    """A duration-less play's extent when no descriptor is known: a motion
    preset's natural length over ``speed``, else ``0.0``.

    The one resolver is :func:`cutan.characters.play.play_extent`; this is it with
    ``desc=None``.

    >>> default_play_extent(PlayAction(target="a", animation="hop"))
    0.5
    >>> default_play_extent(PlayAction(target="a", animation="not_a_preset"))
    0.0
    """
    from cutan.characters.play import play_extent  # lazy: play imports the IR

    return play_extent(None, action)


def play_duration(action: PlayAction, extent: Any) -> float:
    """The span a ``play`` occupies: its ``duration``, else its natural extent.

    ``extent`` is the caller's resolver (the compiler and ``an validate`` pass
    one bound to the entity's descriptor); without one, a motion preset's own
    length (:func:`default_play_extent`).

    >>> play_duration(PlayAction(target="a", animation="hop", duration=2.0), None)
    2.0
    >>> play_duration(PlayAction(target="a", animation="hop"), None)
    0.5
    """
    if action.duration is not None:
        return action.duration
    if extent is None:
        extent = default_play_extent
    return extent(action)


def _play_args(raw: Any, *, index: int) -> dict[str, Any] | None:
    """A ``play``'s ``args:`` — a mapping of motion-preset parameters, or absent."""
    from an.ir.sync import SceneMarkdownError

    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise SceneMarkdownError(
            f"actions[{index}].args must be a mapping of motion-preset "
            f"parameters (e.g. `args: {{height: 30}}`); got {raw!r}"
        )
    return {str(k): v for k, v in raw.items()}


def read_play_md(item: dict[str, Any], *, index: int) -> PlayAction:
    """``{kind: play, target, animation, [duration], [speed], [loop], [args]}``.

    Resolved at compile against the target entity's descriptor ``animations``
    (an#7), falling back to the motion presets of ``cutan.motion.PRESETS`` for a
    name the descriptor does not declare, with ``args`` as the preset's
    parameters (an#166). ``loop`` omitted means the animation's own. This
    reader accepted the shape from the start, then #24 made it refuse (nothing
    resolved a play) while the writer kept emitting it — three days of a
    project's own scene.md failing to parse.
    """
    return play(
        item["target"],
        item["animation"],
        duration=(
            float(item["duration"]) if item.get("duration") is not None else None
        ),
        speed=float(item.get("speed", 1.0)),
        loop=(bool(item["loop"]) if item.get("loop") is not None else None),
        args=_play_args(item.get("args"), index=index),
    )


def write_play_md(leaf: PlayAction) -> dict[str, Any]:
    """The ``scene.md`` entry for ``leaf`` (``read_play_md``'s inverse)."""
    entry: dict[str, Any] = {
        "kind": "play",
        "target": leaf.target,
        "animation": leaf.animation,
    }
    if leaf.duration is not None:
        entry["duration"] = leaf.duration
    if leaf.speed != 1.0:
        entry["speed"] = leaf.speed
    if leaf.loop is not None:
        entry["loop"] = bool(leaf.loop)
    if leaf.args is not None:
        entry["args"] = dict(leaf.args)
    return entry


PLAY = ActionKind(
    "play",
    PlayAction,
    duration=play_duration,
    read_md=read_play_md,
    write_md=write_play_md,
    description=(
        "play a named animation (an action / animation clip) of the target "
        "entity's descriptor, falling back to a motion preset"
    ),
)

CHARACTER = EntityKind(
    "character",
    space="stage.node",
    store="characters",
    description=(
        "a rigged cut-out character: a skeleton of bones with slots, drawn by "
        "the stage engine; its nodes are stage nodes"
    ),
)


def character_specimen(ref: Any) -> Any:
    """The shot that shows one character on its own (an#347's
    ``EntityKind.specimen``, cutan#40): the character at rest, facing the camera
    (its rest view, untouched), alone, so the rig builder places its root at
    the stage centre. ``an library sheet`` draws its first frame on a canvas
    sized from the descriptor's ``view_box`` and trims it to what it shows.

    >>> from an.ir.schema import AssetRef
    >>> shot = character_specimen(AssetRef(kind="character", id="ned", store="characters", ref="ned"))
    >>> shot.renderer, [e.id for e in shot.entities], shot.actions
    ('cutout', ['ned'], [])
    """
    from an.ir.schema import SPECIMEN_DURATION, SPECIMEN_SHOT_ID, Shot

    from cutan import RENDERER_NAME

    return Shot(
        id=SPECIMEN_SHOT_ID,
        renderer=RENDERER_NAME,
        duration=SPECIMEN_DURATION,
        entities=[ref],
    )
