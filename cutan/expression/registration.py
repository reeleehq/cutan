"""The face side of the cut-out genre, as declarations: ``expression`` and ``[emotion]``.

What the cut-out genre (:mod:`cutan.genre`) registers from here:

- the **``expression`` action kind** — :class:`ExpressionAction`
  (hold a facial expression, an#98): zero-width in a ``sequence`` when it runs
  to the shot end, and its ``scene.md`` spelling;
- the **``[emotion]`` dialogue sugar** — ``maya [happy]: Hi!`` fills
  :attr:`an.ir.schema.Dialogue.emotion`, which the expression provider turns
  into an expression over the line, in memory only.

Plain declarations: importing this module registers nothing.

>>> EXPRESSION.name, EMOTION.opener, EMOTION.parse(" Happy ")
('expression', '[', 'happy')
"""

from __future__ import annotations

import re
from typing import Any

from an.genres.registry import ActionKind, DialogueSugar
from typing import Literal

from pydantic import Field

from an.ir.compose import delay, flatten, sequence  # noqa: F401  (doctests)
from an.ir.schema import ExtensionAction, PathStr, Seconds


#: Default ramp in/out of an expression, seconds (0 = cut). The dialogue
#: `[emotion]` sugar uses its own in `an.expression.provider`.
DFLT_EXPRESSION_BLEND_S: float = 0.15


class ExpressionAction(ExtensionAction):
    """Hold a facial expression on an entity (an#98, epic #9 Wave 6).

    ``preset`` names one of :data:`an.expression.presets.PRESETS`; ``axes``
    are per-axis overrides layered on it (axis units, see
    :mod:`an.expression.axes`); ``None`` + no axes is a cheap "return to
    rest". ``duration=None`` runs to the shot end (the looping-play rule) and
    is **zero-width in a sequence**, like a looping ``play``. ``blend`` ramps the
    intensity in and out; two overlapping expressions cross-fade because the
    face solver sums offsets. The dialogue ``speaker [emotion]: …`` bracket is
    sugar for one of these over the line, desugared in memory only.

    A leaf action, flattened like ``play``: the compiler resolves it in the
    face solver (one channel per ``(node, property)``), never per action.

    The ramp is a min over the two ends, so a span shorter than ``2·blend``
    never reaches full intensity (a 0.2 s expression at the default 0.15 s
    blend peaks at 0.67) and a ``duration=0`` expression shows only where a
    frame lands on it with ``blend=0`` — cut the blend for a flash.
    """

    kind: Literal["expression"] = "expression"
    target: PathStr  # the ENTITY; the binding picks the nodes
    preset: str | None = None
    axes: dict[str, float] = Field(default_factory=dict)
    intensity: float = Field(default=1.0, ge=0.0, le=1.0)
    duration: Seconds | None = Field(default=None, ge=0.0)  # None = to the shot end
    blend: Seconds = Field(default=DFLT_EXPRESSION_BLEND_S, ge=0.0)


def expression(
    target: PathStr,
    preset: str | None = None,
    *,
    axes: dict[str, float] | None = None,
    intensity: float = 1.0,
    duration: Seconds | None = None,
    blend: Seconds = DFLT_EXPRESSION_BLEND_S,
) -> ExpressionAction:
    """Hold a facial expression on an entity (an#98).

    ``duration=None`` runs to the shot end and counts as **zero** in a
    ``sequence``, as a looping ``play`` does:

    >>> [f.start for f in flatten(sequence(expression("a", "happy"), delay(1.0), expression("a", "sad")))]
    [0.0, 1.0]
    >>> flatten(expression("a", "angry", duration=2.0))[0].end
    2.0
    """
    return ExpressionAction(
        target=target,
        preset=preset,
        axes=dict(axes or {}),
        intensity=intensity,
        duration=duration,
        blend=blend,
    )


#: What an emotion name may be: a preset name (``happy``, ``wry-smile``).
EMOTION_NAME_RE = re.compile(r"[\w-]+")


def expression_duration(action: ExpressionAction, extent: Any) -> float:
    """An expression's span: its ``duration``, else zero (it runs to the shot end).

    >>> expression_duration(ExpressionAction(target="a", duration=2.0), None)
    2.0
    >>> expression_duration(ExpressionAction(target="a"), None)
    0.0
    """
    return action.duration if action.duration is not None else 0.0


def read_expression_md(item: dict[str, Any], *, index: int) -> ExpressionAction:
    """``{kind: expression, target, [preset], [axes], [intensity], [duration], [blend]}``.

    Landed with its writer and round trip in one commit (an#98): the writer
    skips unknown leaves, so a parser-only entry would vanish from scene.md on
    the next sync and then from the JSON on the next md edit.
    """
    from an.ir.sync import SceneMarkdownError

    raw_axes = item.get("axes") or {}
    if not isinstance(raw_axes, dict):
        raise SceneMarkdownError(
            f"actions[{index}].axes must be a mapping; got {raw_axes!r}"
        )
    return expression(
        item["target"],
        item.get("preset"),
        axes={str(k): float(v) for k, v in raw_axes.items()},
        intensity=float(item.get("intensity", 1.0)),
        duration=(
            float(item["duration"]) if item.get("duration") is not None else None
        ),
        blend=float(item["blend"])
        if item.get("blend") is not None
        else DFLT_EXPRESSION_BLEND_S,
    )


def write_expression_md(leaf: ExpressionAction) -> dict[str, Any]:
    """The ``scene.md`` entry for ``leaf`` (``read_expression_md``'s inverse)."""
    entry: dict[str, Any] = {"kind": "expression", "target": leaf.target}
    if leaf.preset is not None:
        entry["preset"] = leaf.preset
    if leaf.axes:
        entry["axes"] = dict(leaf.axes)
    if leaf.intensity != 1.0:
        entry["intensity"] = leaf.intensity
    if leaf.duration is not None:
        entry["duration"] = leaf.duration
    if leaf.blend != DFLT_EXPRESSION_BLEND_S:
        entry["blend"] = leaf.blend
    return entry


def parse_emotion(content: str) -> str:
    """``[happy]``'s content to the line's emotion, lower-cased; refuse a non-name."""
    emotion = content.strip()
    if not EMOTION_NAME_RE.fullmatch(emotion):
        raise ValueError(f"has [{emotion}], which is not an emotion name")
    return emotion.lower()


def format_emotion(line: Any) -> str | None:
    """The ``[…]`` content for ``line``, or ``None`` when it carries no emotion."""
    return line.emotion or None


EXPRESSION = ActionKind(
    "expression",
    ExpressionAction,
    duration=expression_duration,
    read_md=read_expression_md,
    write_md=write_expression_md,
    description="hold a facial expression (an expression-sheet preset) on a character",
)

EMOTION = DialogueSugar(
    "emotion",
    "[",
    "emotion",
    parse=parse_emotion,
    format=format_emotion,
    description=(
        "`speaker [emotion]: text` — an expression over the line, desugared in "
        "memory by the expression provider"
    ),
)
