"""The facial expression axes: what a cutout face can be asked to do (an#98).

Ten axes ship in Wave 6 of epic #9 — eight numeric, one selection
(``mouth_form``, which picks a ``viseme@<preset>`` set and is not a number),
one scalar (``intensity``). Every numeric value is an **offset over the built
rest** of the node it drives; rest is neutral. The ranges and the eyelid
ladder below are the only numbers in the vocabulary (research
``misc/docs/wave6_research.md`` §4, §6).

Deferred, named so nobody re-invents them: ``brow_squeeze``, ``squint``,
``head_yaw`` / ``head_pitch`` (Wave 7), ``mouth_open`` (the viseme set already
opens monotonically ``X → A → B → C → D``).

>>> AXES["brow_height_l"].clamp(3.0)
1.0
>>> lid_key(-0.9, available={"OPEN", "CLOSED"})
'CLOSED'
>>> lid_key(-0.5, available={"OPEN", "CLOSED"})          # no `half` art: stays open
'OPEN'
>>> lid_key(-0.5, available={"OPEN", "CLOSED", "HALF"})
'HALF'
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Axis:
    """One numeric axis: its range and its rest (neutral) value."""

    name: str
    lo: float
    hi: float
    rest: float = 0.0

    def clamp(self, value: float) -> float:
        return min(self.hi, max(self.lo, float(value)))


#: Brow height, per side: + raises the brow, scaled by the rig's eye height.
#: Brow angle, per side: + inner end up (worry), − inner end down (furrow);
#: the binding's per-side gain carries the screen sign.
#: Lid openness, per side: − closes (`half`, then `closed`), + widens (`wide`).
#: Gaze: pupil travel inside the eye, clamped by the rig's declared travel.
AXES: dict[str, Axis] = {
    "brow_height_l": Axis("brow_height_l", -1.0, 1.0),
    "brow_height_r": Axis("brow_height_r", -1.0, 1.0),
    "brow_angle_l": Axis("brow_angle_l", -1.0, 1.0),
    "brow_angle_r": Axis("brow_angle_r", -1.0, 1.0),
    "lid_open_l": Axis("lid_open_l", -1.0, 0.5),
    "lid_open_r": Axis("lid_open_r", -1.0, 0.5),
    "gaze_x": Axis("gaze_x", -1.0, 1.0),
    "gaze_y": Axis("gaze_y", -1.0, 1.0),
}

#: Which brow ladder input each brow axis feeds (either side's).
BROW_AXIS_KIND: dict[str, str] = {
    "brow_height_l": "height",
    "brow_height_r": "height",
    "brow_angle_l": "angle",
    "brow_angle_r": "angle",
}
BROW_AXES: tuple[str, ...] = tuple(BROW_AXIS_KIND)
LID_AXES: tuple[str, ...] = ("lid_open_l", "lid_open_r")
GAZE_AXES: tuple[str, ...] = ("gaze_x", "gaze_y")

#: The selection axis: which `viseme@<form>` set the mouth's key indexes.
MOUTH_FORM_AXIS: str = "mouth_form"
#: The scalar on every offset (MPEG-4 "excitation"); the blend ramp is a curve on it.
INTENSITY_AXIS: str = "intensity"

#: The eyelid ladder — one rule, stated once (research §6). A lid state
#: `min(lid_expr, lid_blink)` reads off these thresholds; a rig without the
#: intermediate art degrades to the key it has.
LID_WIDE_ABOVE: float = 0.25
LID_HALF_BELOW: float = -0.35
LID_CLOSED_BELOW: float = -0.85

#: Eyelid set keys the ladder can name, by openness.
LID_KEY_WIDE: str = "WIDE"
LID_KEY_OPEN: str = "OPEN"
LID_KEY_HALF: str = "HALF"
LID_KEY_CLOSED: str = "CLOSED"


#: The brow ladder (cutan#114), for a rig that draws its brows as a swap set:
#: a furrow (``brow_angle`` below the first) draws ``ANGRY``, else a raise
#: (``brow_height`` above the second) draws ``RAISED``, else ``NONE``.
BROW_FURROW_BELOW: float = -0.25
BROW_RAISED_ABOVE: float = 0.25

#: Brow set keys the ladder can name.
BROW_KEY_ANGRY: str = "ANGRY"
BROW_KEY_RAISED: str = "RAISED"
BROW_KEY_NONE: str = "NONE"


def clamp_axes(values: Mapping[str, float]) -> dict[str, float]:
    """Clamp every numeric axis to its range; an unknown axis is an error.

    >>> clamp_axes({"brow_height_l": 2.0, "lid_open_r": -3.0})
    {'brow_height_l': 1.0, 'lid_open_r': -1.0}
    >>> clamp_axes({"eyebrow": 1.0})
    Traceback (most recent call last):
    ...
    ValueError: unknown expression axis 'eyebrow' (known: brow_angle_l, ...)
    """
    out: dict[str, float] = {}
    for name, value in values.items():
        axis = AXES.get(name)
        if axis is None:
            raise ValueError(
                f"unknown expression axis {name!r} (known: {', '.join(sorted(AXES))})"
            )
        out[name] = axis.clamp(value)
    return out


def lid_key(value: float, *, available: Collection[str]) -> str:
    """The eyelid key a lid state selects, degraded to the art the rig declares.

    ``wide`` above +0.25, ``open``, ``half`` below −0.35, ``closed`` below −0.85;
    a rig without ``half`` stays open until the lower threshold and one without
    ``wide`` stays open above the upper one — never a blend of two drawings.
    """
    keys = {str(k).upper() for k in available}
    if value > LID_WIDE_ABOVE and LID_KEY_WIDE in keys:
        return LID_KEY_WIDE
    if value < LID_CLOSED_BELOW and LID_KEY_CLOSED in keys:
        return LID_KEY_CLOSED
    if value < LID_HALF_BELOW and LID_KEY_HALF in keys:
        return LID_KEY_HALF
    return LID_KEY_OPEN


def brow_key(height: float, angle: float, *, available: Collection[str]) -> str:
    """The brow key one side's height and angle select, degraded to the art declared.

    A furrow draws ``ANGRY``, else a raise ``RAISED``, else ``NONE`` — and a
    state the set has no drawing for is ``NONE``, never a blend.

    >>> brow_key(-0.6, -0.48, available={"ANGRY", "RAISED", "NONE"})
    'ANGRY'
    >>> brow_key(0.6, 0.0, available={"ANGRY", "RAISED", "NONE"})
    'RAISED'
    >>> brow_key(0.6, 0.0, available={"ANGRY", "NONE"})
    'NONE'
    >>> brow_key(0.1, -0.1, available={"ANGRY", "RAISED", "NONE"})
    'NONE'
    """
    keys = {str(k).upper() for k in available}
    if angle < BROW_FURROW_BELOW and BROW_KEY_ANGRY in keys:
        return BROW_KEY_ANGRY
    if height > BROW_RAISED_ABOVE and BROW_KEY_RAISED in keys:
        return BROW_KEY_RAISED
    return BROW_KEY_NONE
