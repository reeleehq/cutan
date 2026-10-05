# cutan.motion

The cut-out genre’s motion presets: moves that name a rig’s parts or swap its views.

`nod`, `point`, `turn`, `walk`, `waddle` and `speech_pulse` moved
here from `an.motion` (an#322): each names a part of a cut-out rig
(`<entity>/head`, the arm and leg nodes) or swaps a view, so they belong to
the genre, not to the core. The rig-free moves on the entity container
(`pop_in`, `hop`, `shake`, `slide_in`/`slide_out`,
`squash_stretch`, `crawl`) stay in `an.motion`, together with the
helpers every preset is built from (`rest`, landing `set``s,
:func:`~an.motion.stage_poses`, :func:`~an.motion.as_leaves`). ``an.motion`
keeps live aliases at the old names (the 14-day shim rule in this repository’s
`CLAUDE.md`).

Like the core’s, each preset EXPANDS to ordinary `tween` (and, for `turn`,
`set`) actions; nothing downstream learns a preset exists. [`PRESETS`](#cutan.motion.PRESETS)
is the table a `play` resolves a name in ([`cutan.characters.play`](cutan.characters.play.md#module-cutan.characters.play)): the
core’s presets and this module’s, by name. Importing this module is what puts
the genre’s presets into it.

```pycon
>>> sorted(RIG_PRESETS), set(RIG_PRESETS) <= set(PRESETS)
(['nod', 'point', 'speech_pulse', 'turn', 'waddle', 'walk'], True)
>>> [(f.action.target, round(f.action.to_value, 2)) for f in _tweens(nod("charlie", count=1))]
[('charlie/head', 0.18), ('charlie/head', 0.0)]
```

### Module Attributes

| [`WALK_LANDING_S`](#cutan.motion.WALK_LANDING_S)    | Every channel of a walk — a limb's and the body's (cutan#15) — ends with a constant tween this long at its end value instead of a settling `set`: it lands the value exactly (a held tween END is evaluated at its own end, which float drift cannot put a grid step early), and unlike a `set` — whose hold outranks a view's pose channel, and holds again when a longer authored tween on the property ends — it lets later motion carry on.   |
|--------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`WALK_LEG_NAMES`](#cutan.motion.WALK_LEG_NAMES)    | the rig contract's (descriptor rigs, `an character new`), then the procedural placeholder's.                                                                                                                                                                                                                                                                                                                                                      |
| [`GAITS`](#cutan.motion.GAITS)             | persisted in character descriptors and `play` args (`cutan.characters.schema.GAITS`), so a spelling is never renamed.                                                                                                                                                                                                                                                                                                                             |
| [`LEGGED_GAITS`](#cutan.motion.LEGGED_GAITS)      | The gaits that move a leg pair — and need one (the `limbs.legs` capability).                                                                                                                                                                                                                                                                                                                                                                      |
| [`DFLT_LEGLESS_GAIT`](#cutan.motion.DFLT_LEGLESS_GAIT) | the locomotion chain's last link.                                                                                                                                                                                                                                                                                                                                                                                                                 |
| [`GAIT_DEFAULTS`](#cutan.motion.GAIT_DEFAULTS)     | Each gait's departures from `WALK_PARAM_DEFAULTS`.                                                                                                                                                                                                                                                                                                                                                                                                |
| [`DFLT_TURN_SET`](#cutan.motion.DFLT_TURN_SET)     | the factory's turnaround (an#197).                                                                                                                                                                                                                                                                                                                                                                                                                |
| [`RIG_PRESETS`](#cutan.motion.RIG_PRESETS)       | The genre's presets, by name.                                                                                                                                                                                                                                                                                                                                                                                                                     |
| [`PRESETS`](#cutan.motion.PRESETS)           | Every preset a `play` can name — the core's and the genre's — the one table the skill, the demos, the vocabulary and the `play` fallback ([`cutan.characters.play.play_source()`](cutan.characters.play.md#cutan.characters.play.play_source), an#166) read.                                                                                                                                                                   |
| [`PRESET_VERSIONS`](#cutan.motion.PRESET_VERSIONS)   | [`PRESETS`](#cutan.motion.PRESETS)' vocabulary versions.                                                                                                                                                                                                                                                                                                                                                                    |

### Functions

| [`face_toward`](#cutan.motion.face_toward)(shot, who, other, \*[, view, ...])     | [`turn()`](#cutan.motion.turn) `who` to `view`, facing `other` — the direction read off the stage, so a profile looks at the other character wherever the layout put them.   |
|-----------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`gait_params`](#cutan.motion.gait_params)(gait, \*[, scale])                     | The parameters a `gait` walks with: `given` where not `None`, else its default.                                                                                                                       |
| [`nod`](#cutan.motion.nod)(target, \*[, part, angle, duration, ...])      | Dip the head `count` times (a rotation of `<target>/<part>`).                                                                                                                                         |
| [`point`](#cutan.motion.point)(target, \*[, angle, raise_duration, ...])    | Swing an arm out to point, hold it, and lower it again.                                                                                                                                               |
| [`speech_pulse`](#cutan.motion.speech_pulse)(target, \*[, beats, strength, ...])   | Pulse a part on each syllable: speech carried without a mouth (an#248).                                                                                                                               |
| [`turn`](#cutan.motion.turn)(target, \*[, to, direction, ...])             | Turn a character to the view `to` — the classic cut-out turn (an#197).                                                                                                                                |
| [`waddle`](#cutan.motion.waddle)(target, \*[, steps, step_duration, ...])    | A walk cycle for a rig with no legs to animate: rock and bob per step.                                                                                                                                |
| [`walk`](#cutan.motion.walk)(target, \*[, to_x, distance, direction, ...]) | Walk: the body travels on `x` while the gait moves it — legs that alternate, a hop, a bounce, a glide (an#214, an#224).                                                                               |

### cutan.motion.DFLT_LEGLESS_GAIT *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'glide'*

the locomotion chain’s last link.

* **Type:**
  The gait of a figure with no leg pair

### cutan.motion.DFLT_TURN_SET *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'view'*

the factory’s turnaround (an#197).

* **Type:**
  The swap set a turn swaps

### cutan.motion.GAITS *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), ...]* *= ('legs', 'hem', 'rock', 'profile', 'shuffle', 'waddle', 'hop', 'bounce', 'glide')*

persisted in character
descriptors and `play` args (`cutan.characters.schema.GAITS`), so a
spelling is never renamed. Each is a locomotion method
([`cutan.characters.methods`](cutan.characters.methods.md#module-cutan.characters.methods)); `misc/docs/locomotion_gaits.md` is the
classification behind them.

* **Type:**
  The gaits `walk` knows (`gait=`, an#220, an#224)

### cutan.motion.GAIT_DEFAULTS *: [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [float](https://docs.python.org/3/builtins/functions.html#float)]]* *= {'bounce': {'arm_swing': 0.15, 'bob': 8.0, 'lift': 4.0, 'stride': 0.1}, 'glide': {'arm_swing': 0.0, 'bob': 1.5}, 'hem': {}, 'hop': {'arm_swing': 0.0}, 'legs': {}, 'profile': {'arm_swing': 0.35, 'stride': 0.45}, 'rock': {}, 'shuffle': {'arm_swing': 0.1, 'bob': 1.0, 'lift': 3.0, 'step_length': 40.0, 'step_s': 0.3, 'stride': 0.12}, 'waddle': {'arm_swing': 0.15, 'bob': 4.0, 'lift': 5.0, 'rock': 0.12}}*

Each gait’s departures from `WALK_PARAM_DEFAULTS`. The first three are
the pre-an#224 gaits and keep the shared defaults exactly (no pixel moves).

### cutan.motion.LEGGED_GAITS *: [frozenset](https://docs.python.org/3/builtins/stdtypes.html#frozenset)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)]* *= frozenset({'hem', 'legs', 'profile', 'shuffle'})*

The gaits that move a leg pair — and need one (the `limbs.legs` capability).

### cutan.motion.PRESETS *: [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[...], [Annotated](https://docs.python.org/3/library/typing.html#typing.Annotated)[[Annotated](https://docs.python.org/3/library/typing.html#typing.Annotated)[SetAction, Tag(tag=[set](https://docs.python.org/3/builtins/stdtypes.html#set))] | [Annotated](https://docs.python.org/3/library/typing.html#typing.Annotated)[TweenAction, Tag(tag=tween)] | [Annotated](https://docs.python.org/3/library/typing.html#typing.Annotated)[SequenceAction, Tag(tag=sequence)] | [Annotated](https://docs.python.org/3/library/typing.html#typing.Annotated)[ParallelAction, Tag(tag=parallel)] | [Annotated](https://docs.python.org/3/library/typing.html#typing.Annotated)[DelayAction, Tag(tag=delay)] | [Annotated](https://docs.python.org/3/library/typing.html#typing.Annotated)[LoopAction, Tag(tag=loop)] | [Annotated](https://docs.python.org/3/library/typing.html#typing.Annotated)[ExtensionAction, SerializeAsAny(), Tag(tag=extension)], Discriminator(discriminator=\_action_tag, custom_error_type=[None](https://docs.python.org/3/builtins/constants.html#None), custom_error_message=[None](https://docs.python.org/3/builtins/constants.html#None), custom_error_context=[None](https://docs.python.org/3/builtins/constants.html#None))]]]* *= {'crawl': <function crawl>, 'hop': <function hop>, 'nod': <function nod>, 'point': <function point>, 'pop_in': <function pop_in>, 'shake': <function shake>, 'slide_in': <function slide_in>, 'slide_out': <function slide_out>, 'speech_pulse': <function speech_pulse>, 'squash_stretch': <function squash_stretch>, 'turn': <function turn>, 'waddle': <function waddle>, 'walk': <function walk>}*

Every preset a `play` can name — the core’s and the genre’s — the one table
the skill, the demos, the vocabulary and the `play` fallback
([`cutan.characters.play.play_source()`](cutan.characters.play.md#cutan.characters.play.play_source), an#166) read. A genre preset wins a
name the core also has.

### cutan.motion.PRESET_VERSIONS *: [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [str](https://docs.python.org/3/builtins/stdtypes.html#str)]* *= {'crawl': '1', 'hop': '1', 'nod': '1', 'point': '1', 'pop_in': '1', 'shake': '1', 'slide_in': '1', 'slide_out': '1', 'speech_pulse': '1', 'squash_stretch': '1', 'turn': '1', 'waddle': '1', 'walk': '4'}*

[`PRESETS`](#cutan.motion.PRESETS)’ vocabulary versions.

### cutan.motion.RIG_PRESETS *: [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[...], [Annotated](https://docs.python.org/3/library/typing.html#typing.Annotated)[[Annotated](https://docs.python.org/3/library/typing.html#typing.Annotated)[SetAction, Tag(tag=[set](https://docs.python.org/3/builtins/stdtypes.html#set))] | [Annotated](https://docs.python.org/3/library/typing.html#typing.Annotated)[TweenAction, Tag(tag=tween)] | [Annotated](https://docs.python.org/3/library/typing.html#typing.Annotated)[SequenceAction, Tag(tag=sequence)] | [Annotated](https://docs.python.org/3/library/typing.html#typing.Annotated)[ParallelAction, Tag(tag=parallel)] | [Annotated](https://docs.python.org/3/library/typing.html#typing.Annotated)[DelayAction, Tag(tag=delay)] | [Annotated](https://docs.python.org/3/library/typing.html#typing.Annotated)[LoopAction, Tag(tag=loop)] | [Annotated](https://docs.python.org/3/library/typing.html#typing.Annotated)[ExtensionAction, SerializeAsAny(), Tag(tag=extension)], Discriminator(discriminator=\_action_tag, custom_error_type=[None](https://docs.python.org/3/builtins/constants.html#None), custom_error_message=[None](https://docs.python.org/3/builtins/constants.html#None), custom_error_context=[None](https://docs.python.org/3/builtins/constants.html#None))]]]* *= {'nod': <function nod>, 'point': <function point>, 'speech_pulse': <function speech_pulse>, 'turn': <function turn>, 'waddle': <function waddle>, 'walk': <function walk>}*

The genre’s presets, by name.

### cutan.motion.WALK_LANDING_S *: [float](https://docs.python.org/3/builtins/functions.html#float)* *= 0.001*

Every channel of a walk — a limb’s and the body’s (cutan#15) — ends with a
constant tween this long at its end value instead of a settling `set`: it
lands the value exactly (a held tween END is evaluated at its own end, which
float drift cannot put a grid step early), and unlike a `set` — whose hold
outranks a view’s pose channel, and holds again when a longer authored tween
on the property ends — it lets later motion carry on.

### cutan.motion.WALK_LEG_NAMES *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [str](https://docs.python.org/3/builtins/stdtypes.html#str)], ...]* *= (('leg_l', 'leg_r'), ('left_leg', 'right_leg'))*

the rig contract’s
(descriptor rigs, `an character new`), then the procedural placeholder’s.

* **Type:**
  Leg and arm node names a walk looks for, in order

### cutan.motion.face_toward(shot, who, other, , view='side', from_direction=None, duration=0.3, mall=None)

[`turn()`](#cutan.motion.turn) `who` to `view`, facing `other` — the direction read
off the stage, so a profile looks at the other character wherever the
layout put them.

(These examples build character entities, the cut-out genre’s; they are not run here.)

* **Return type:**
  `Union`[`SetAction`, `TweenAction`, `SequenceAction`, `ParallelAction`, `DelayAction`, `LoopAction`, `ExtensionAction`]

```pycon
>>> from an.ir.schema import AssetRef
>>> two = Shot(id="s", entities=[
...     AssetRef(kind="character", id=n, store="characters", ref=n) for n in ("a", "b")])
>>> [f.action.to_value for f in _tweens(face_toward(two, "b", "a"))]
[0.0, -1.0]
```

### cutan.motion.gait_params(gait, , scale=1.0, \*\*given)

The parameters a `gait` walks with: `given` where not `None`, else its default.

A default length (`SCALED_GAIT_PARAMS`: the step, the body’s bob, a
hop) is stated for a figure at drawn scale 1 and multiplied by `scale`
(the figure’s drawn scale: its stage scale, an#224); an explicit value is
scene px as given. Angles and a leg’s `lift` (in the figure’s own frame,
already scaled with it) never scale.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`float`](https://docs.python.org/3/builtins/functions.html#float)]

```pycon
>>> gait_params("legs")["step_length"], gait_params("legs", scale=2.0)["step_length"]
(80.0, 160.0)
>>> gait_params("shuffle", scale=2.0, step_length=50.0)["step_length"]
50.0
```

### cutan.motion.nod(target, , part='head', angle=0.18, duration=0.5, count=2, rest=None)

Dip the head `count` times (a rotation of `<target>/<part>`).

In a front-facing 2D cut-out a nod reads as a small head rotation about
its pivot; `rest` is the HEAD’s rest, not the entity’s.

* **Return type:**
  `Union`[`SetAction`, `TweenAction`, `SequenceAction`, `ParallelAction`, `DelayAction`, `LoopAction`, `ExtensionAction`]

```pycon
>>> [(f.action.target, round(f.action.to_value, 2)) for f in _tweens(nod("charlie", count=1))]
[('charlie/head', 0.18), ('charlie/head', 0.0)]
```

### cutan.motion.point(target, , angle=-1.3, raise_duration=0.25, hold=0.6, easing=(0.34, 1.56, 0.64, 1.0), rest=None)

Swing an arm out to point, hold it, and lower it again.

`target` is the ARM node — `"charlie/right_arm"` on the procedural
rig, `"maya/arm_r"` on a descriptor rig (and there, since that arm hangs
on the viewer’s left, pass a positive `angle` to point outward).

* **Return type:**
  `Union`[`SetAction`, `TweenAction`, `SequenceAction`, `ParallelAction`, `DelayAction`, `LoopAction`, `ExtensionAction`]

```pycon
>>> [(f.start, f.action.to_value) for f in _tweens(point("charlie/right_arm", hold=0.5))]
[(0.0, -1.3), (0.75, 0.0)]
```

### cutan.motion.speech_pulse(target, , beats=(0.0,), strength=0.06, part='head', attack=0.06, release=0.1, rest=None)

Pulse a part on each syllable: speech carried without a mouth (an#248).

The requirement-free last link of the speech aspect (ADR 0002 decision 5,
method `speech.pose_only`): a character whose face is baked into its art
(`face_overlay: false`) still reads as speaking. On each time in `beats`
(seconds from the start) `<target>/<part>` stretches its `scale_y` by
`strength` over `attack` and settles over `release`; `part=""`
pulses the whole body. A beat that would start before the previous pulse
settles is skipped, so the pulse never stacks. `strength=0` is a mime.
`rest` is the PART’s rest, as for [`nod()`](#cutan.motion.nod); it lands with a constant
tween rather than a settling `set`, so played once per syllable (as the
speech aspect does) each pulse rides whatever the head is doing.

* **Return type:**
  `Union`[`SetAction`, `TweenAction`, `SequenceAction`, `ParallelAction`, `DelayAction`, `LoopAction`, `ExtensionAction`]

```pycon
>>> [(round(f.start, 2), f.action.to_value) for f in _tweens(speech_pulse("al", beats=(0.0, 0.3)))]
[(0.0, 1.06), (0.06, 1.0), (0.3, 1.06), (0.36, 1.0), (0.46, 1.0)]
```

### cutan.motion.turn(target, , to='back', direction='right', from_direction=None, duration=0.3, view_set='view', rest=None)

Turn a character to the view `to` — the classic cut-out turn (an#197).

`scale_x` squashes to 0 (the character edge-on), the view swaps at that
midpoint, and `scale_x` opens again to the rest scale — mirrored when
`direction="left"`: a `side` view is drawn facing the viewer’s right,
so `direction` is which way the character FACES after the turn.
`from_direction` is which way it faced before — by default the sign of
the rest `scale_x` (a character staged mirrored faces left). Called from
Python the preset cannot see an EARLIER turn, so turning back from a
left-facing profile is `turn(to="front", from_direction="left")`; PLAYED
by name (`{kind: play, animation: turn}`) the compiler fills it in from
the timeline before it ([`cutan.characters.play.resolve_turns()`](cutan.characters.play.md#cutan.characters.play.resolve_turns), an#203).

`to` is a key of the character’s `view` set — `front`, `back`,
`side` or `three_quarter` on a factory character
(`an character new --offline`); the swap is a `set` on the ENTITY,
which the compiler fans out to the head and torso and which poses the face
(the back hides it, the profile keeps one eye). `rest` is the entity’s:
its `scale_x` magnitude is where the turn opens to.

* **Return type:**
  `Union`[`SetAction`, `TweenAction`, `SequenceAction`, `ParallelAction`, `DelayAction`, `LoopAction`, `ExtensionAction`]

```pycon
>>> def lands(a):  # a tween's end value, a set's value
...     return a.to_value if a.kind == "tween" else a.value
>>> [(round(f.start, 2), f.action.property, lands(f.action))
...  for f in flatten(turn("ned", to="side", direction="left"))]
[(0.0, 'scale_x', 0.0), (0.15, 'view', 'side'), (0.15, 'scale_x', -1.0), (0.3, 'scale_x', -1.0)]
```

### cutan.motion.waddle(target, , steps=4, step_duration=0.3, angle=0.1, lift=6.0, travel=0.0, rest=None)

A walk cycle for a rig with no legs to animate: rock and bob per step.

Each step rocks the body to alternate sides by `angle` and bobs it up by
`lift`; `angle=0` is a plain bob. `travel` (scene px, signed)
carries the body sideways over the whole walk — the one `x` move here,
so it is the one that needs `rest` in a multi-character shot.

* **Return type:**
  `Union`[`SetAction`, `TweenAction`, `SequenceAction`, `ParallelAction`, `DelayAction`, `LoopAction`, `ExtensionAction`]

```pycon
>>> w = _tweens(waddle("charlie", steps=2, travel=100))
>>> sorted({f.action.property for f in w})
['rotation', 'x', 'y']
>>> max(f.end for f in w)
0.6
```

### cutan.motion.walk(target, , to_x=None, distance=None, direction=None, steps=None, step_s=None, step_length=None, stride=None, lift=None, bob=None, arm_swing=None, rock=None, hem_tilt=None, hop_height=None, lean=None, view=None, gait=None, legs=None, arms=None, parts=None, rest=None, scale=None)

Walk: the body travels on `x` while the gait moves it — legs that
alternate, a hop, a bounce, a glide (an#214, an#224).

**Where to.** `to_x` (absolute scene x) or `distance` (signed px; with
`direction` `"left"`/`"right"` its sign is the direction’s), or
neither to walk on the spot. The walk starts where the entity IS —
played by name, `rest` is its pose at the play’s start (an#212), so
`set x -800` then `walk to_x: -100` walks in from off-screen.

**How many steps.** `steps`, else `|distance| / step_length`, else
`DFLT_WALK_STEPS` — never counted from the start position, so the
walk’s length (`steps × step_s`) is known before it is placed and a
`sequence` waits for exactly that long.

**Gait** (`gait`, one of [`GAITS`](#cutan.motion.GAITS); the locomotion methods of
[`cutan.characters.methods`](cutan.characters.methods.md#module-cutan.characters.methods), classified in
`misc/docs/locomotion_gaits.md`). Each has its own defaults
([`GAIT_DEFAULTS`](#cutan.motion.GAIT_DEFAULTS)); a parameter passed overrides them.

- `legs`: in a view in `WALK_SWING_VIEWS` (`side`,
  `three_quarter`) each leg swings `stride` radians either side of its
  rest about the hip, the two in opposition; in any other view the
  stepping leg rises `lift` px and sets down; the body bobs `bob` once
  per step and the arms swing `arm_swing` against the legs.
- `profile`: the four-pose cycle of a profile walk (contact, down,
  passing, up): the legs swing whatever the view, the body sinks after
  each contact (a third of `bob`) and rises before the next (two
  thirds): `bob` is its whole travel between two contacts.
- `shuffle`: `legs` with the feet barely leaving the ground — short,
  quick steps, no bob to speak of.
- `hem`: a robe whose leg slots are the two halves of its hem: facing
  the camera the halves TILT in turn by `hem_tilt` radians while the body
  sways by `rock` and bobs (in a profile they swing like legs).
- `waddle`: the body rocks `rock` from foot to foot and bobs; legs, if
  any, lift in turn.
- `hop`: the body jumps `hop_height` px on every step.
- `bounce`: the body bobs `bob` on every step while it slides; legs,
  if any, flick (a South Park walk).
- `glide`: the body slides, leaning `lean` radians into the move and
  bobbing `bob` gently; no limb moves.
- `rock`: no leg moves; the body rocks `rock` and bobs.

A sway (`rock`) follows the figure’s facing (the sign of `rest`’s
`scale_x`, cutan#20): with legs, it leans onto the standing foot. An
amplitude set to 0 writes no channel at all (cutan#14), and every channel
— the body’s included — lands with a [`WALK_LANDING_S`](#cutan.motion.WALK_LANDING_S) constant
tween rather than a settling `set` (cutan#15), so an authored move on
the same property that outlasts the walk carries on where it is.

Unset: `legs` when the rig builds a leg pair, else [`DFLT_LEGLESS_GAIT`](#cutan.motion.DFLT_LEGLESS_GAIT)
— the locomotion chain’s default (played by name, the compiler resolves the
gait on the capability registry first: the author’s, else the
descriptor’s, else the chain). A legged gait on a rig with no leg pair
walks the legless default too.

**Size.** `step_length`, `bob` and `hop_height` default to lengths
for a figure at drawn scale 1, multiplied by `scale`, the figure’s drawn
scale — its STAGE scale (`stage.scale`, the rig as built), which the
compiler fills in when the walk is played by name — so a character staged
at `scale: 2` strides twice as far (an#224). Pass them to set scene px
outright. Called from Python with no `scale`, the `scale_y` of
`rest` stands in; that is the pose at the play’s start, which a
`pop_in` running under the walk holds at 0 (cutan#13) — refused, naming
the scale — so the compiler never relies on it.

**Legs and arms.** `legs`/`arms` name the two limb nodes; by default
the first pair in [`WALK_LEG_NAMES`](#cutan.motion.WALK_LEG_NAMES) / `WALK_ARM_NAMES` that the
rig builds (`parts`: the entity’s built parts with their pose at the
start, filled in by the compiler). Played by name, `view` is the one in
force on the timeline at the play’s start (else the descriptor’s
`rest_view`, an#220). Limbs land on their rest with a
[`WALK_LANDING_S`](#cutan.motion.WALK_LANDING_S) constant tween, not a settling `set`: a `set`’s
hold would outrank the view’s pose channel and keep a profile’s splay
after a later turn to the front.

The walk does not turn the character: in a side view, face the way it
walks first (`turn`, `direction`) — the classic walk-off is `turn`
then `walk`.

```pycon
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
```

* **Return type:**
  `Union`[`SetAction`, `TweenAction`, `SequenceAction`, `ParallelAction`, `DelayAction`, `LoopAction`, `ExtensionAction`]
