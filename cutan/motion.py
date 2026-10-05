"""The cut-out genre's motion presets: moves that name a rig's parts or swap its views.

``nod``, ``point``, ``turn``, ``walk``, ``waddle`` and ``speech_pulse`` moved
here from :mod:`an.motion` (an#322): each names a part of a cut-out rig
(``<entity>/head``, the arm and leg nodes) or swaps a view, so they belong to
the genre, not to the core. The rig-free moves on the entity container
(``pop_in``, ``hop``, ``shake``, ``slide_in``/``slide_out``,
``squash_stretch``, ``crawl``) stay in :mod:`an.motion`, together with the
helpers every preset is built from (``rest``, landing ``set``s,
:func:`~an.motion.stage_poses`, :func:`~an.motion.as_leaves`). ``an.motion``
keeps live aliases at the old names (the 14-day shim rule in this repository's
``CLAUDE.md``).

Like the core's, each preset EXPANDS to ordinary ``tween`` (and, for ``turn``,
``set``) actions; nothing downstream learns a preset exists. :data:`PRESETS`
is the table a ``play`` resolves a name in (:mod:`cutan.characters.play`): the
core's presets and this module's, by name. Importing this module is what puts
the genre's presets into it.

>>> sorted(RIG_PRESETS), set(RIG_PRESETS) <= set(PRESETS)
(['nod', 'point', 'speech_pulse', 'turn', 'waddle', 'walk'], True)
>>> [(f.action.target, round(f.action.to_value, 2)) for f in _tweens(nod("charlie", count=1))]
[('charlie/head', 0.18), ('charlie/head', 0.0)]
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping
from typing import Any

from an.base import EasingSpec, PathStr, Seconds
from an.ir.compose import delay, duration_of, flatten, parallel, sequence, set_, tween
from an.ir.schema import Action, Shot
from an.motion import (
    DFLT_IN_EASING,
    DFLT_OSCILLATION_EASING,
    DFLT_OUT_EASING,
    HOME_PRESETS,
    OVERSHOOT,
    PRESET_VERSIONS as CORE_PRESET_VERSIONS,
    PRESETS as CORE_PRESETS,
    Rest,
    _alternating,
    _positive,
    _rest,
    _settled,
    _side_sign,
    _through,
    _tweens,
    stage_poses,
)

# -----------------------------------------------------------------------------
# Defaults
# -----------------------------------------------------------------------------

DFLT_NOD_PART: str = "head"
DFLT_NOD_ANGLE: float = 0.18  # radians
DFLT_NOD_DURATION: Seconds = 0.5
DFLT_NOD_COUNT: int = 2
#: Negative is counter-clockwise on screen: an arm hanging from a shoulder
#: swings its hand to the VIEWER'S RIGHT — outward for the procedural rig's
#: ``right_arm``. A descriptor rig's ``arm_r`` hangs on the viewer's left, so
#: point it outward with a positive angle.
DFLT_POINT_ANGLE: float = -1.3  # radians
DFLT_POINT_RAISE: Seconds = 0.25
DFLT_POINT_HOLD: Seconds = 0.6
DFLT_WADDLE_STEPS: int = 4
DFLT_WADDLE_STEP_DURATION: Seconds = 0.3
DFLT_WADDLE_ANGLE: float = 0.1  # radians
DFLT_WADDLE_LIFT: float = 6.0  # scene px
DFLT_TURN_DURATION: Seconds = 0.3
DFLT_WALK_STEP_S: Seconds = 0.4
#: Steps a walk takes when neither ``steps`` nor ``distance`` sets them: a walk
#: to an ABSOLUTE ``to_x`` cannot count its steps from where it starts, because
#: a ``sequence`` must know a play's length before anything is placed.
DFLT_WALK_STEPS: int = 6
DFLT_WALK_STEP_LENGTH: float = 80.0  # scene px per step, for ``distance``
DFLT_WALK_STRIDE: float = 0.35  # radians a leg swings either side (side view)
DFLT_WALK_LIFT: float = 10.0  # scene px a stepping leg rises (front view)
DFLT_WALK_BOB: float = 6.0  # scene px the body rises between contacts
DFLT_WALK_ARM_SWING: float = 0.3  # radians
DFLT_WALK_ROCK: float = 0.06  # radians, a legless figure's side-to-side rock
#: Radians each hem half tilts about its hip, in turn, in a ``hem`` gait seen
#: from the front (an#220) — what read on a carved robe figure, where lifting
#: one half by ``lift`` px barely showed.
DFLT_WALK_HEM_TILT: float = 0.24
#: A limb's move ends with a constant tween this long at its end value instead
#: of a settling ``set``: it lands the value exactly (a held tween END is
#: evaluated at its own end, which float drift cannot put a grid step early),
#: and unlike a ``set`` — whose hold outranks a view's pose channel — it lets
#: a later view change pose the limb again.
WALK_LANDING_S: Seconds = 1e-3
#: Leg and arm node names a walk looks for, in order: the rig contract's
#: (descriptor rigs, ``an character new``), then the procedural placeholder's.
WALK_LEG_NAMES: tuple[tuple[str, str], ...] = (
    ("leg_l", "leg_r"),
    ("left_leg", "right_leg"),
)
WALK_ARM_NAMES: tuple[tuple[str, str], ...] = (
    ("arm_l", "arm_r"),
    ("left_arm", "right_arm"),
)
#: Views whose legs SWING about the hip (the character seen from the side);
#: every other view (``front``, ``back``, none) steps them up and down.
WALK_SWING_VIEWS: frozenset[str] = frozenset({"side", "three_quarter"})
#: A speech pulse (ADR 0002's requirement-free speech, an#248): the part that
#: pulses on each syllable — ``head`` lifts like a hinged jaw (the cut-out
#: "head flap"); ``""`` pulses the whole body.
DFLT_PULSE_PART: str = "head"
#: How far the part stretches on a syllable, as a fraction of its rest
#: ``scale_y``. Masters who mime set 0 (study_the_masters §4, Reiniger).
DFLT_PULSE_STRENGTH: float = 0.06
DFLT_PULSE_ATTACK_S: Seconds = 0.06
DFLT_PULSE_RELEASE_S: Seconds = 0.1
#: How high a ``hop`` gait jumps on each step (scene px at drawn scale 1).
DFLT_WALK_HOP_HEIGHT: float = 18.0
#: How far a ``glide`` leans into its travel (radians).
DFLT_WALK_LEAN: float = 0.04

#: The gaits ``walk`` knows (``gait=``, an#220, an#224): persisted in character
#: descriptors and ``play`` args (:data:`cutan.characters.schema.GAITS`), so a
#: spelling is never renamed. Each is a locomotion method
#: (:mod:`cutan.characters.methods`); ``misc/docs/locomotion_gaits.md`` is the
#: classification behind them.
GAITS: tuple[str, ...] = (
    "legs",
    "hem",
    "rock",
    "profile",
    "shuffle",
    "waddle",
    "hop",
    "bounce",
    "glide",
)
#: The gaits that move a leg pair — and need one (the ``limbs.legs`` capability).
LEGGED_GAITS: frozenset[str] = frozenset({"legs", "hem", "profile", "shuffle"})
#: The gait of a figure with no leg pair: the locomotion chain's last link.
DFLT_LEGLESS_GAIT: str = "glide"
#: Every walk parameter a gait reads, with the shared default.
WALK_PARAM_DEFAULTS: dict[str, float] = {
    "step_s": DFLT_WALK_STEP_S,
    "step_length": DFLT_WALK_STEP_LENGTH,
    "stride": DFLT_WALK_STRIDE,
    "lift": DFLT_WALK_LIFT,
    "bob": DFLT_WALK_BOB,
    "arm_swing": DFLT_WALK_ARM_SWING,
    "rock": DFLT_WALK_ROCK,
    "hem_tilt": DFLT_WALK_HEM_TILT,
    "hop_height": DFLT_WALK_HOP_HEIGHT,
    "lean": DFLT_WALK_LEAN,
}
#: The lengths that scale with the figure's drawn scale (the rest are angles,
#: times, or a leg's lift in the figure's own frame).
SCALED_GAIT_PARAMS: frozenset[str] = frozenset({"step_length", "bob", "hop_height"})
#: Each gait's departures from :data:`WALK_PARAM_DEFAULTS`. The first three are
#: the pre-an#224 gaits and keep the shared defaults exactly (no pixel moves).
GAIT_DEFAULTS: dict[str, dict[str, float]] = {
    "legs": {},
    "hem": {},
    "rock": {},
    # Williams' four poses: a longer stride, the body sinking after contact.
    "profile": {"stride": 0.45, "arm_swing": 0.35},
    # Feet barely leave the ground: short, quick steps, no bob to speak of.
    "shuffle": {
        "step_s": 0.3,
        "step_length": 40.0,
        "stride": 0.12,
        "lift": 3.0,
        "bob": 1.0,
        "arm_swing": 0.1,
    },
    # From foot to foot: a big rock, a small lift.
    "waddle": {"rock": 0.12, "lift": 5.0, "bob": 4.0, "arm_swing": 0.15},
    "hop": {"arm_swing": 0.0},
    # South Park: a pronounced bob while sliding, the feet flicking.
    "bounce": {"bob": 8.0, "lift": 4.0, "stride": 0.1, "arm_swing": 0.15},
    # A slide with a gentle bob and a lean into the move; no limb moves.
    "glide": {"bob": 1.5, "arm_swing": 0.0},
}

#: The swap set a turn swaps: the factory's turnaround (an#197).
DFLT_TURN_SET: str = "view"
DFLT_TURN_TO: str = "back"


# -----------------------------------------------------------------------------
# Presets
# -----------------------------------------------------------------------------


def nod(
    target: PathStr,
    *,
    part: str = DFLT_NOD_PART,
    angle: float = DFLT_NOD_ANGLE,
    duration: Seconds = DFLT_NOD_DURATION,
    count: int = DFLT_NOD_COUNT,
    rest: Rest | None = None,
) -> Action:
    """Dip the head ``count`` times (a rotation of ``<target>/<part>``).

    In a front-facing 2D cut-out a nod reads as a small head rotation about
    its pivot; ``rest`` is the HEAD's rest, not the entity's.

    >>> [(f.action.target, round(f.action.to_value, 2)) for f in _tweens(nod("charlie", count=1))]
    [('charlie/head', 0.18), ('charlie/head', 0.0)]
    """
    if count < 1:
        raise ValueError(f"nod needs a count of at least 1, got {count}")
    _positive(duration=duration)
    path = f"{target}/{part}" if part else target
    r0 = _rest(rest, "rotation")
    values = [r0] + [r0 + angle, r0] * count
    n = len(values) - 1
    return _through(
        path,
        "rotation",
        values,
        durations=[duration / n] * n,
        easings=_alternating(n, DFLT_OUT_EASING, DFLT_IN_EASING),
    )


def point(
    target: PathStr,
    *,
    angle: float = DFLT_POINT_ANGLE,
    raise_duration: Seconds = DFLT_POINT_RAISE,
    hold: Seconds = DFLT_POINT_HOLD,
    easing: EasingSpec = OVERSHOOT,
    rest: Rest | None = None,
) -> Action:
    """Swing an arm out to point, hold it, and lower it again.

    ``target`` is the ARM node — ``"charlie/right_arm"`` on the procedural
    rig, ``"maya/arm_r"`` on a descriptor rig (and there, since that arm hangs
    on the viewer's left, pass a positive ``angle`` to point outward).

    >>> [(f.start, f.action.to_value) for f in _tweens(point("charlie/right_arm", hold=0.5))]
    [(0.0, -1.3), (0.75, 0.0)]
    """
    _positive(raise_duration=raise_duration)
    if hold < 0:
        raise ValueError(f"hold must not be negative, got {hold!r}")
    r0 = _rest(rest, "rotation")
    return _settled(
        target,
        "rotation",
        r0,
        tween(
            target,
            "rotation",
            to=r0 + angle,
            duration=raise_duration,
            from_=r0,
            easing=easing,
        ),
        delay(hold),
        tween(
            target,
            "rotation",
            to=r0,
            duration=raise_duration,
            from_=r0 + angle,
            easing=DFLT_OSCILLATION_EASING,
        ),
    )


def waddle(
    target: PathStr,
    *,
    steps: int = DFLT_WADDLE_STEPS,
    step_duration: Seconds = DFLT_WADDLE_STEP_DURATION,
    angle: float = DFLT_WADDLE_ANGLE,
    lift: float = DFLT_WADDLE_LIFT,
    travel: float = 0.0,
    rest: Rest | None = None,
) -> Action:
    """A walk cycle for a rig with no legs to animate: rock and bob per step.

    Each step rocks the body to alternate sides by ``angle`` and bobs it up by
    ``lift``; ``angle=0`` is a plain bob. ``travel`` (scene px, signed)
    carries the body sideways over the whole walk — the one ``x`` move here,
    so it is the one that needs ``rest`` in a multi-character shot.

    >>> w = _tweens(waddle("charlie", steps=2, travel=100))
    >>> sorted({f.action.property for f in w})
    ['rotation', 'x', 'y']
    >>> max(f.end for f in w)
    0.6
    """
    if steps < 1:
        raise ValueError(f"waddle needs at least one step, got {steps}")
    _positive(step_duration=step_duration)
    r0, y0 = _rest(rest, "rotation"), _rest(rest, "y")
    half = step_duration / 2
    rock = [r0]
    bob = [y0]
    for i in range(steps):
        rock += [r0 + (angle if i % 2 == 0 else -angle), r0]
        bob += [y0 - lift, y0]
    n = 2 * steps
    easings = _alternating(n, DFLT_OUT_EASING, DFLT_IN_EASING)
    moves = [
        _through(target, "rotation", rock, durations=[half] * n, easings=easings),
        _through(target, "y", bob, durations=[half] * n, easings=easings),
    ]
    if travel:
        x0 = _rest(rest, "x")
        moves.append(
            _settled(
                target,
                "x",
                x0 + travel,
                tween(
                    target,
                    "x",
                    to=x0 + travel,
                    duration=steps * step_duration,
                    from_=x0,
                    easing="linear",
                ),
            )
        )
    return parallel(*moves)


def _limb_pair(
    names: tuple[str, str] | None,
    candidates: tuple[tuple[str, str], ...],
    parts: Mapping[str, Rest] | None,
) -> tuple[str, str] | None:
    """The two limb nodes a walk moves: ``names`` when given (``()``: none),
    else the first candidate pair the rig builds (``parts``), else — with no
    rig to look at — the rig contract's names."""
    if names is not None:
        if len(names) not in (0, 2):
            raise ValueError(f"give two limb names (or none), got {names!r}")
        return tuple(names) if names else None  # type: ignore[return-value]
    if parts is None:
        return candidates[0]
    return next((pair for pair in candidates if all(n in parts for n in pair)), None)


def gait_params(
    gait: str, *, scale: float = 1.0, **given: float | None
) -> dict[str, float]:
    """The parameters a ``gait`` walks with: ``given`` where not ``None``, else its default.

    A default length (:data:`SCALED_GAIT_PARAMS`: the step, the body's bob, a
    hop) is stated for a figure at drawn scale 1 and multiplied by ``scale``
    (the figure's drawn scale: its stage scale, an#224); an explicit value is
    scene px as given. Angles and a leg's ``lift`` (in the figure's own frame,
    already scaled with it) never scale.

    >>> gait_params("legs")["step_length"], gait_params("legs", scale=2.0)["step_length"]
    (80.0, 160.0)
    >>> gait_params("shuffle", scale=2.0, step_length=50.0)["step_length"]
    50.0
    """
    if gait not in GAITS:
        raise ValueError(f"gait must be one of {list(GAITS)}, got {gait!r}")
    out: dict[str, float] = {}
    for name, base in WALK_PARAM_DEFAULTS.items():
        value = given.get(name)
        if value is None:
            value = GAIT_DEFAULTS[gait].get(name, base)
            if name in SCALED_GAIT_PARAMS:
                value = value * scale
        out[name] = float(value)
    return out


def walk(
    target: PathStr,
    *,
    to_x: float | None = None,
    distance: float | None = None,
    direction: str | None = None,
    steps: int | None = None,
    step_s: Seconds | None = None,
    step_length: float | None = None,
    stride: float | None = None,
    lift: float | None = None,
    bob: float | None = None,
    arm_swing: float | None = None,
    rock: float | None = None,
    hem_tilt: float | None = None,
    hop_height: float | None = None,
    lean: float | None = None,
    view: str | None = None,
    gait: str | None = None,
    legs: tuple[str, str] | None = None,
    arms: tuple[str, str] | None = None,
    parts: Mapping[str, Rest] | None = None,
    rest: Rest | None = None,
    scale: float | None = None,
) -> Action:
    """Walk: the body travels on ``x`` while the gait moves it — legs that
    alternate, a hop, a bounce, a glide (an#214, an#224).

    **Where to.** ``to_x`` (absolute scene x) or ``distance`` (signed px; with
    ``direction`` ``"left"``/``"right"`` its sign is the direction's), or
    neither to walk on the spot. The walk starts where the entity IS —
    played by name, ``rest`` is its pose at the play's start (an#212), so
    ``set x -800`` then ``walk to_x: -100`` walks in from off-screen.

    **How many steps.** ``steps``, else ``|distance| / step_length``, else
    :data:`DFLT_WALK_STEPS` — never counted from the start position, so the
    walk's length (``steps × step_s``) is known before it is placed and a
    ``sequence`` waits for exactly that long.

    **Gait** (``gait``, one of :data:`GAITS`; the locomotion methods of
    :mod:`cutan.characters.methods`, classified in
    ``misc/docs/locomotion_gaits.md``). Each has its own defaults
    (:data:`GAIT_DEFAULTS`); a parameter passed overrides them.

    - ``legs``: in a view in :data:`WALK_SWING_VIEWS` (``side``,
      ``three_quarter``) each leg swings ``stride`` radians either side of its
      rest about the hip, the two in opposition; in any other view the
      stepping leg rises ``lift`` px and sets down; the body bobs ``bob`` once
      per step and the arms swing ``arm_swing`` against the legs.
    - ``profile``: the four-pose cycle of a profile walk (contact, down,
      passing, up): the legs swing whatever the view, the body sinks after
      each contact (a third of ``bob``) and rises before the next (two
      thirds): ``bob`` is its whole travel per step.
    - ``shuffle``: ``legs`` with the feet barely leaving the ground — short,
      quick steps, no bob to speak of.
    - ``hem``: a robe whose leg slots are the two halves of its hem: facing
      the camera the halves TILT in turn by ``hem_tilt`` radians while the body
      sways by ``rock`` and bobs (in a profile they swing like legs).
    - ``waddle``: the body rocks ``rock`` from foot to foot and bobs; legs, if
      any, lift in turn.
    - ``hop``: the body jumps ``hop_height`` px on every step.
    - ``bounce``: the body bobs ``bob`` on every step while it slides; legs,
      if any, flick (a South Park walk).
    - ``glide``: the body slides, leaning ``lean`` radians into the move and
      bobbing ``bob`` gently; no limb moves.
    - ``rock``: no leg moves; the body rocks ``rock`` and bobs.

    A sway (``rock``) leans onto the standing foot: it follows the figure's
    facing (the sign of ``rest``'s ``scale_x``, cutan#20). A parameter set to
    0 writes no channel at all (cutan#14), and every channel — the body's
    included — lands with a :data:`WALK_LANDING_S` constant tween rather than
    a settling ``set`` (cutan#15), so an authored move on the same property
    that outlasts the walk carries on where it is.

    Unset: ``legs`` when the rig builds a leg pair, else :data:`DFLT_LEGLESS_GAIT`
    — the locomotion chain's default (played by name, the compiler resolves the
    gait on the capability registry first: the author's, else the
    descriptor's, else the chain). A legged gait on a rig with no leg pair
    walks the legless default too.

    **Size.** ``step_length``, ``bob`` and ``hop_height`` default to lengths
    for a figure at drawn scale 1, multiplied by ``scale``, the figure's drawn
    scale — its STAGE scale (``stage.scale``, the rig as built), which the
    compiler fills in when the walk is played by name — so a character staged
    at ``scale: 2`` strides twice as far (an#224). Pass them to set scene px
    outright. Called from Python with no ``scale``, the ``scale_y`` of
    ``rest`` stands in; that is the pose at the play's start, which a
    ``pop_in`` running under the walk holds at 0 (cutan#13) — refused, naming
    the scale — so the compiler never relies on it.

    **Legs and arms.** ``legs``/``arms`` name the two limb nodes; by default
    the first pair in :data:`WALK_LEG_NAMES` / :data:`WALK_ARM_NAMES` that the
    rig builds (``parts``: the entity's built parts with their pose at the
    start, filled in by the compiler). Played by name, ``view`` is the one in
    force on the timeline at the play's start (else the descriptor's
    ``rest_view``, an#220). Limbs land on their rest with a
    :data:`WALK_LANDING_S` constant tween, not a settling ``set``: a ``set``'s
    hold would outrank the view's pose channel and keep a profile's splay
    after a later turn to the front.

    The walk does not turn the character: in a side view, face the way it
    walks first (``turn``, ``direction``) — the classic walk-off is ``turn``
    then ``walk``.

    >>> w = walk("bob", distance=160, steps=2, step_s=0.5)
    >>> sorted({(f.action.target, f.action.property) for f in _tweens(w)})
    [('bob', 'x'), ('bob', 'y'), ('bob/arm_l', 'rotation'), ('bob/arm_r', 'rotation'), ('bob/leg_l', 'y'), ('bob/leg_r', 'y')]
    >>> round(max(f.end for f in flatten(w)), 6), {f.action.to_value for f in _tweens(w) if f.action.property == "x"}
    (1.0, {160.0})
    >>> sorted({f.action.property for f in _tweens(walk("bob", distance=80, view="side"))
    ...         if f.action.target == "bob/leg_l"})
    ['rotation']
    >>> sorted({(f.action.target, f.action.property) for f in _tweens(walk("blob", steps=2, legs=(), arms=()))})
    [('blob', 'y')]
    >>> sorted({(f.action.target, f.action.property) for f in _tweens(walk("al", steps=2, gait="hem"))
    ...         if f.action.target in ("al", "al/leg_l")})
    [('al', 'rotation'), ('al', 'y'), ('al/leg_l', 'rotation')]
    >>> [round(f.action.to_value, 1) for f in _tweens(walk("k", steps=2, gait="hop", legs=(), arms=()))]
    [-18.0, 0.0, -18.0, 0.0, 0.0]
    >>> {f.action.to_value for f in _tweens(walk("k", distance=160, rest={"scale_y": 2.0}, legs=()))
    ...  if f.action.property == "x"}
    {160.0}
    >>> round(duration_of(walk("k", distance=160, scale=2.0, legs=())), 6), round(duration_of(walk("k", distance=160, legs=())), 6)
    (0.4, 0.8)
    """
    if gait is not None and gait not in GAITS:
        raise ValueError(f"gait must be one of {list(GAITS)}, got {gait!r}")
    if to_x is not None and distance is not None:
        raise ValueError("give to_x (absolute) or distance (relative), not both")
    if direction is not None:
        sign = _side_sign(direction)
        if distance is None:
            raise ValueError("direction goes with distance (to_x is already a place)")
        distance = sign * abs(distance)
    leg_pair = _limb_pair(legs, WALK_LEG_NAMES, parts)
    arm_pair = _limb_pair(arms, WALK_ARM_NAMES, parts)
    if gait is None:
        gait = "legs" if leg_pair is not None else DFLT_LEGLESS_GAIT
    elif gait in LEGGED_GAITS and leg_pair is None:
        gait = DFLT_LEGLESS_GAIT
    if gait not in LEGGED_GAITS | {"waddle", "bounce"}:
        leg_pair = None  # this gait moves no leg
    given_scale = scale is not None
    if scale is None:
        scale = abs(_rest(rest, "scale_y"))
    if not (math.isfinite(scale) and scale > 0):
        raise ValueError(
            f"the figure's drawn scale is {scale!r}"
            + ("" if given_scale else " (its scale_y at the play's start)")
            + ": a walk needs a finite, positive scale (its stage scale)"
        )
    if step_length is not None:
        _positive(step_length=step_length)
    p = gait_params(
        gait,
        scale=abs(scale),
        step_s=step_s,
        step_length=step_length,
        stride=stride,
        lift=lift,
        bob=bob,
        arm_swing=arm_swing,
        rock=rock,
        hem_tilt=hem_tilt,
        hop_height=hop_height,
        lean=lean,
    )
    step_s = p["step_s"]
    _positive(step_s=step_s)
    if step_s <= 4 * WALK_LANDING_S:
        raise ValueError(
            f"step_s must be longer than {4 * WALK_LANDING_S}s, got {step_s!r}"
        )
    if steps is None:
        steps = (
            max(1, round(abs(distance) / p["step_length"]))
            if distance is not None
            else DFLT_WALK_STEPS
        )
    if steps < 1:
        raise ValueError(f"walk needs at least one step, got {steps}")
    x0, y0 = _rest(rest, "x"), _rest(rest, "y")
    x1 = to_x if to_x is not None else x0 + (distance or 0.0)
    half = step_s / 2
    n = 2 * steps
    up_down = _alternating(n, DFLT_OUT_EASING, DFLT_IN_EASING)
    moves: list[Action] = []

    def limb(name: str) -> str:
        return f"{target}/{name}"

    def part_rest(name: str) -> Rest | None:
        return (parts or {}).get(name)

    def unsettled(
        path: str, prop: str, values: list[float], durations, easings
    ) -> Action:
        # The landing takes its time out of the last segment: the walk's length
        # is exactly `steps × step_s`, which `play_extent` promised. The body's
        # channels land this way too (cutan#15): a settling `set` would hold
        # again when a longer authored tween on the property ends, snapping the
        # body back to where the walk left it.
        durations = [*durations[:-1], durations[-1] - WALK_LANDING_S]
        return sequence(
            *(
                tween(path, prop, to=b, duration=d, from_=a, easing=e)
                for a, b, d, e in zip(values, values[1:], durations, easings)
            ),
            tween(
                path,
                prop,
                to=values[-1],
                duration=WALK_LANDING_S,
                from_=values[-1],
                easing="linear",
            ),
        )

    def swing(path: str, r0: float, amount: float, phase: float) -> Action:
        # Extremes at every contact (a step boundary), the rest at both ends. A
        # one-step walk has no interior contact: its one extreme is mid-step
        # (cutan#16: `[r0, r0]` moved nothing while the body travelled).
        if steps == 1:
            values = [r0, r0 + phase * amount, r0]
            durations = [half, half]
        else:
            values = (
                [r0]
                + [r0 + phase * amount * (-1) ** k for k in range(steps - 1)]
                + [r0]
            )
            durations = [step_s] * steps
        return unsettled(
            path,
            "rotation",
            values,
            durations,
            [DFLT_OSCILLATION_EASING] * len(durations),
        )

    def step_lift(path: str, ly: float, amount: float, phase: float) -> Action:
        # This leg steps on every other step; the other one stands.
        values, durations, easings = [ly], [], []
        for i in range(steps):
            if (i % 2 == 0) == (phase > 0):
                values += [ly - amount, ly]
                durations += [half, half]
                easings += [DFLT_OUT_EASING, DFLT_IN_EASING]
            else:
                values += [ly]
                durations += [step_s]
                easings += ["linear"]
        return unsettled(path, "y", values, durations, easings)

    def body_bob(height: float) -> Action:
        values = [y0]
        for _ in range(steps):
            values += [y0 - height, y0]
        return unsettled(target, "y", values, [half] * n, up_down)

    def body_cycle(height: float) -> Action:
        # Williams' four poses between two CONTACTS (a step boundary, the legs
        # at their widest): contact → down (lowest, a quarter step in) →
        # passing (the legs cross, mid-step) → up (highest, three quarters in)
        # → contact. `height` is the body's whole travel: it sinks a third of
        # it and rises two thirds. The walk starts and ends STANDING (the legs
        # together, a passing pose), so the first step gets the half of the
        # cycle before a contact (up) and the last the half after one (down);
        # a one-step walk's contact is mid-step (cutan#18, cutan#16).
        q = step_s / 4
        up, down = y0 - 2 * height / 3, y0 + height / 3
        values: list[float] = [y0]
        durations: list[Seconds] = []
        easings: list[EasingSpec] = []
        if steps == 1:
            values += [up, y0, down, y0]
            durations += [3 * q / 2, q / 2, q / 2, 3 * q / 2]
            easings += [DFLT_OUT_EASING, DFLT_IN_EASING] * 2
        else:
            for i in range(steps):
                if i == 0:
                    values += [up, y0]
                    durations += [3 * q, q]
                    easings += [DFLT_OUT_EASING, DFLT_IN_EASING]
                elif i == steps - 1:
                    values += [down, y0]
                    durations += [q, 3 * q]
                    easings += [DFLT_OUT_EASING, DFLT_IN_EASING]
                else:
                    values += [down, up, y0]
                    durations += [q, 2 * q, q]
                    easings += [
                        DFLT_OUT_EASING,
                        DFLT_OSCILLATION_EASING,
                        DFLT_IN_EASING,
                    ]
        return unsettled(target, "y", values, durations, easings)

    def body_rock(amount: float) -> Action:
        # Onto the standing foot: a positive rotation (clockwise on screen)
        # leans the body over the viewer's right while `leg_l` — on the
        # viewer's left on every rig — lifts on the even steps. The body's
        # rotation is applied AFTER its mirror, the legs move WITH it, so a
        # figure facing left (rest `scale_x` < 0) leans the other way (cutan#20).
        r0 = _rest(rest, "rotation")
        facing = -1.0 if _rest(rest, "scale_x") < 0 else 1.0
        rock_values = [r0] + [
            v for i in range(steps) for v in (r0 + facing * amount * (-1) ** i, r0)
        ]
        return unsettled(target, "rotation", rock_values, [half] * n, up_down)

    def body_lean(amount: float) -> Action:
        r0 = _rest(rest, "rotation")
        tilt = r0 + (amount if x1 > x0 else -amount)
        ramp = min(step_s, steps * step_s / 4)
        hold = steps * step_s - 2 * ramp
        values, durations, easings = [r0, tilt], [ramp], [DFLT_OUT_EASING]
        if hold > 0:
            values.append(tilt)
            durations.append(hold)
            easings.append("linear")
        values.append(r0)
        durations.append(ramp)
        easings.append(DFLT_IN_EASING)
        return unsettled(target, "rotation", values, durations, easings)

    # A zero amplitude writes NO channel (cutan#14): a constant tween would
    # still outrank an authored move on the property for the walk's length.
    # The travel.
    if x1 != x0:
        moves.append(unsettled(target, "x", [x0, x1], [steps * step_s], ["linear"]))
    # The body's rise and fall.
    rise = p["hop_height"] if gait == "hop" else p["bob"]
    if rise:
        moves.append(body_cycle(rise) if gait == "profile" else body_bob(rise))
    # The legs.
    swinging = view in WALK_SWING_VIEWS or gait == "profile"
    hem = gait == "hem" and not swinging
    if leg_pair is not None:
        for phase, name in zip((1.0, -1.0), leg_pair):
            pose = part_rest(name)
            if gait != "waddle" and (swinging or hem):
                amount = p["hem_tilt"] if hem else p["stride"]
                if amount:
                    moves.append(
                        swing(limb(name), _rest(pose, "rotation"), amount, phase)
                    )
            elif p["lift"]:
                moves.append(step_lift(limb(name), _rest(pose, "y"), p["lift"], phase))
    # The body's sway.
    if (hem or gait in ("rock", "waddle")) and p["rock"]:
        moves.append(body_rock(p["rock"]))
    elif gait == "glide" and p["lean"] and x1 != x0:
        moves.append(body_lean(p["lean"]))
    # The arms, against the legs: the leg_l phase is +1, so arm_l's is -1.
    if arm_pair is not None and p["arm_swing"]:
        for phase, name in zip((-1.0, 1.0), arm_pair):
            moves.append(
                swing(
                    limb(name),
                    _rest(part_rest(name), "rotation"),
                    p["arm_swing"],
                    phase,
                )
            )
    if not moves:
        # Nothing to move (on the spot, every amplitude 0): the walk still
        # takes its time, as `play_extent` promised a `sequence`.
        moves.append(delay(steps * step_s))
    return parallel(*moves)


_FACINGS: tuple[str, ...] = ("right", "left")


def _facing_sign(name: str, value: str) -> float:
    if value not in _FACINGS:
        raise ValueError(f"{name} must be one of {list(_FACINGS)}, got {value!r}")
    return -1.0 if value == "left" else 1.0


def turn(
    target: PathStr,
    *,
    to: str = DFLT_TURN_TO,
    direction: str = "right",
    from_direction: str | None = None,
    duration: Seconds = DFLT_TURN_DURATION,
    view_set: str = DFLT_TURN_SET,
    rest: Rest | None = None,
) -> Action:
    """Turn a character to the view ``to`` — the classic cut-out turn (an#197).

    ``scale_x`` squashes to 0 (the character edge-on), the view swaps at that
    midpoint, and ``scale_x`` opens again to the rest scale — mirrored when
    ``direction="left"``: a ``side`` view is drawn facing the viewer's right,
    so ``direction`` is which way the character FACES after the turn.
    ``from_direction`` is which way it faced before — by default the sign of
    the rest ``scale_x`` (a character staged mirrored faces left). Called from
    Python the preset cannot see an EARLIER turn, so turning back from a
    left-facing profile is ``turn(to="front", from_direction="left")``; PLAYED
    by name (``{kind: play, animation: turn}``) the compiler fills it in from
    the timeline before it (:func:`cutan.characters.play.resolve_turns`, an#203).

    ``to`` is a key of the character's ``view`` set — ``front``, ``back``,
    ``side`` or ``three_quarter`` on a factory character
    (``an character new --offline``); the swap is a ``set`` on the ENTITY,
    which the compiler fans out to the head and torso and which poses the face
    (the back hides it, the profile keeps one eye). ``rest`` is the entity's:
    its ``scale_x`` magnitude is where the turn opens to.

    >>> def lands(a):  # a tween's end value, a set's value
    ...     return a.to_value if a.kind == "tween" else a.value
    >>> [(round(f.start, 2), f.action.property, lands(f.action))
    ...  for f in flatten(turn("ned", to="side", direction="left"))]
    [(0.0, 'scale_x', 0.0), (0.15, 'view', 'side'), (0.15, 'scale_x', -1.0), (0.3, 'scale_x', -1.0)]
    """
    _positive(duration=duration)
    if not isinstance(to, str) or not to:
        raise ValueError(
            f"to must name a view (a key of the {view_set!r} set), got {to!r}"
        )
    rest_sx = _rest(rest, "scale_x")
    s0 = abs(rest_sx)
    if from_direction is None:
        from_direction = "left" if rest_sx < 0 else "right"
    before = _facing_sign("from_direction", from_direction) * s0
    after = _facing_sign("direction", direction) * s0
    half = duration / 2
    return sequence(
        tween(
            target,
            "scale_x",
            to=0.0,
            duration=half,
            from_=before,
            easing=DFLT_IN_EASING,
        ),
        parallel(
            set_(target, view_set, to),
            _settled(
                target,
                "scale_x",
                after,
                tween(
                    target,
                    "scale_x",
                    to=after,
                    duration=half,
                    from_=0.0,
                    easing=DFLT_OUT_EASING,
                ),
            ),
        ),
    )


def face_toward(
    shot: Shot,
    who: str,
    other: str,
    *,
    view: str = "side",
    from_direction: str | None = None,
    duration: Seconds = DFLT_TURN_DURATION,
    mall: Mapping[str, Mapping] | None = None,
) -> Action:
    """:func:`turn` ``who`` to ``view``, facing ``other`` — the direction read
    off the stage, so a profile looks at the other character wherever the
    layout put them.

    (These examples build character entities, the cut-out genre's; they are not run here.)
    >>> from an.ir.schema import AssetRef  # doctest: +SKIP
    >>> two = Shot(id="s", entities=[  # doctest: +SKIP
    ...     AssetRef(kind="character", id=n, store="characters", ref=n) for n in ("a", "b")])
    >>> [f.action.to_value for f in _tweens(face_toward(two, "b", "a"))]  # doctest: +SKIP
    [0.0, -1.0]
    """
    poses = stage_poses(shot, mall=mall)
    for name in (who, other):
        if name not in poses:
            raise KeyError(f"no entity {name!r} in the shot; built: {sorted(poses)}")
    direction = "right" if poses[other]["x"] >= poses[who]["x"] else "left"
    return turn(
        who,
        to=view,
        direction=direction,
        from_direction=from_direction,
        duration=duration,
        rest=poses[who],
    )


def speech_pulse(
    target: PathStr,
    *,
    beats: tuple[Seconds, ...] = (0.0,),
    strength: float = DFLT_PULSE_STRENGTH,
    part: str = DFLT_PULSE_PART,
    attack: Seconds = DFLT_PULSE_ATTACK_S,
    release: Seconds = DFLT_PULSE_RELEASE_S,
    rest: Rest | None = None,
) -> Action:
    """Pulse a part on each syllable: speech carried without a mouth (an#248).

    The requirement-free last link of the speech aspect (ADR 0002 decision 5,
    method ``speech.pose_only``): a character whose face is baked into its art
    (``face_overlay: false``) still reads as speaking. On each time in ``beats``
    (seconds from the start) ``<target>/<part>`` stretches its ``scale_y`` by
    ``strength`` over ``attack`` and settles over ``release``; ``part=""``
    pulses the whole body. A beat that would start before the previous pulse
    settles is skipped, so the pulse never stacks. ``strength=0`` is a mime.
    ``rest`` is the PART's rest, as for :func:`nod`; it lands with a constant
    tween rather than a settling ``set``, so played once per syllable (as the
    speech aspect does) each pulse rides whatever the head is doing.

    >>> [(round(f.start, 2), f.action.to_value) for f in _tweens(speech_pulse("al", beats=(0.0, 0.3)))]
    [(0.0, 1.06), (0.06, 1.0), (0.3, 1.06), (0.36, 1.0), (0.46, 1.0)]
    """
    _positive(attack=attack, release=release)
    if not beats:
        raise ValueError("speech_pulse needs at least one beat")
    path = f"{target}/{part}" if part else target
    s0 = _rest(rest, "scale_y")
    peak = s0 * (1.0 + strength)
    moves: list[Action] = []
    t = 0.0
    for beat in sorted(float(b) for b in beats):
        if beat < t:
            continue
        if beat > t:
            moves.append(delay(beat - t))
        moves += [
            tween(
                path,
                "scale_y",
                to=peak,
                duration=attack,
                from_=s0,
                easing=DFLT_OUT_EASING,
            ),
            tween(
                path,
                "scale_y",
                to=s0,
                duration=release,
                from_=peak,
                easing=DFLT_IN_EASING,
            ),
        ]
        t = beat + attack + release
    # Lands with a constant tween, not a settling `set` (as a walk's limbs do):
    # a `set` would hold `s0` and freeze an authored head-scale tween running
    # under the pulse; a tween ends, and the authored one carries on.
    moves.append(
        tween(
            path, "scale_y", to=s0, duration=WALK_LANDING_S, from_=s0, easing="linear"
        )
    )
    return sequence(*moves)


#: The genre's presets, by name.
RIG_PRESETS: dict[str, Callable[..., Action]] = {
    f.__name__: f for f in (nod, point, waddle, turn, walk, speech_pulse)
}
#: Each genre preset's vocabulary version (ADR 0003 decision 2): bump one in the
#: SAME change that makes it expand differently for the same args, so every shot
#: that plays it re-renders visibly instead of silently.
RIG_PRESET_VERSIONS: dict[str, str] = {
    **{name: "1" for name in RIG_PRESETS},
    # 2 (an#224): the gaits, a legless figure glides instead of rocking, and
    # the default lengths scale with the figure's drawn scale.
    # 3 (cutan#13): the drawn scale is the stage scale, not the pose at the
    # play's start (a figure resized by an authored move strides as drawn).
    # 4 (cutan#14-#16, #18, #20): a one-step walk swings its limbs; the profile
    # cycle is phased to the contacts and `bob` is its whole travel; the sway
    # mirrors with the figure; a zero amplitude writes no channel; the body
    # lands with the landing tween, not a settling set.
    "walk": "4",
}

#: Every preset a ``play`` can name — the core's and the genre's — the one table
#: the skill, the demos, the vocabulary and the ``play`` fallback
#: (:func:`cutan.characters.play.play_source`, an#166) read. A genre preset wins a
#: name the core also has.
PRESETS: dict[str, Callable[..., Action]] = {**CORE_PRESETS, **RIG_PRESETS}
#: :data:`PRESETS`' vocabulary versions.
PRESET_VERSIONS: dict[str, str] = {**CORE_PRESET_VERSIONS, **RIG_PRESET_VERSIONS}


__all__ = [
    "CORE_PRESETS",
    "DFLT_TURN_SET",
    "DFLT_LEGLESS_GAIT",
    "GAITS",
    "GAIT_DEFAULTS",
    "HOME_PRESETS",
    "LEGGED_GAITS",
    "PRESETS",
    "PRESET_VERSIONS",
    "RIG_PRESETS",
    "WALK_ARM_NAMES",
    "WALK_LANDING_S",
    "WALK_LEG_NAMES",
    "face_toward",
    "gait_params",
    "nod",
    "point",
    "speech_pulse",
    "turn",
    "waddle",
    "walk",
]
