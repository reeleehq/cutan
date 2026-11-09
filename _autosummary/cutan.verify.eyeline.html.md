# cutan.verify.eyeline

The eyeline lint: do two characters in an exchange look at each other?

Two rules, both advisory (a warning is the author’s to override on purpose), both
about the SIGN a character faces (`scale_x`), the only facing a flat timeline
carries ([`cutan.characters.play.facing_at()`](cutan.characters.play.html.md#cutan.characters.play.facing_at)):

* **Within a shot** ([`shot_findings()`](#cutan.verify.eyeline.shot_findings)): a character speaking to the one other
  character on screen should face their side of the frame. `at: [x, y]` places
  them; a speaker left of the listener who faces left looks away.
* **Across a cut** ([`cut_findings()`](#cutan.verify.eyeline.cut_findings)): a shot/reverse-shot pair keeps the line
  (the 180-degree rule). `A` speaks alone in one shot, `B` answers alone in the
  next; `A` should face one way and `B` the other. Both facing the same way
  makes the cut jump the line, and the pair read as one looking past the other.

The rules are pure functions over small records ([`Presence`](#cutan.verify.eyeline.Presence)), so they are
tested without a store or a scene; [`check_eyeline()`](#cutan.verify.eyeline.check_eyeline) is the adapter from a
scene’s resolved timelines, and `cutout.eyeline` registers it on the genre.

Only a view that SHOWS a direction is judged ([`DIRECTIONAL_VIEWS`](#cutan.verify.eyeline.DIRECTIONAL_VIEWS): the profile
and the three-quarter). A `front` character looks at the camera, and mirroring it
is invisible as an eyeline (gaze, not facing, directs it); a `back` one looks away
from it. Lines are judged at their start AND end, and warned only when the speaker
faces wrongly at both: a turn toward the listener during the line is the author’s fix.

```pycon
>>> a = Presence("ana", direction="right", x=-1.0, speaks=True)
>>> b = Presence("ben", direction="left", x=1.0)
>>> shot_findings([a, b])
[]
>>> [f.entity for f in shot_findings([Presence("ana", "left", -1.0, True), b])]
['ana']
>>> cut_findings([a], [Presence("ben", "right", 0.0, True)])[0].entity
'ben'
```

### Module Attributes

| [`REST_DIRECTION`](#cutan.verify.eyeline.REST_DIRECTION)    | the rig's rest (`scale_x` > 0; the factory draws its profile facing the viewer's right).   |
|--------------------------------------------------------------------|--------------------------------------------------------------------------------------------|
| [`DIRECTIONAL_VIEWS`](#cutan.verify.eyeline.DIRECTIONAL_VIEWS) | The views that show a direction on screen; any other view is not judged.                   |

### Functions

| [`check_eyeline`](#cutan.verify.eyeline.check_eyeline)(ctx, \*[, directional_views, ...])   | The cut-out genre's eyeline warnings: a speaker facing away from the one character it speaks to, and a shot/reverse-shot pair whose speakers face the same way.   |
|-----------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`cut_findings`](#cutan.verify.eyeline.cut_findings)(before, after)                        | A shot/reverse-shot pair whose speakers face the same way (the line is jumped).                                                                                   |
| [`shot_findings`](#cutan.verify.eyeline.shot_findings)(present)                             | A speaker facing away from the one other character in the shot.                                                                                                   |

### Classes

| [`EyelineFinding`](#cutan.verify.eyeline.EyelineFinding)(entity, message)          | One thing to warn about: which entity, and what is wrong with its facing.   |
|-------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------|
| [`Presence`](#cutan.verify.eyeline.Presence)(entity[, direction, x, speaks]) | A character on screen at one instant of a shot.                             |

### cutan.verify.eyeline.DIRECTIONAL_VIEWS *: [frozenset](https://docs.python.org/3/builtins/stdtypes.html#frozenset)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)]* *= frozenset({'side', 'three_quarter'})*

The views that show a direction on screen; any other view is not judged.

### *class* cutan.verify.eyeline.EyelineFinding(entity, message)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

One thing to warn about: which entity, and what is wrong with its facing.

### *class* cutan.verify.eyeline.Presence(entity, direction=None, x=None, speaks=False)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A character on screen at one instant of a shot.

`direction` is `"left"`/`"right"`, or `None` when it is not judged (a
view that shows no direction); `x` its horizontal screen position, or
`None` when the shot does not place it; `speaks` whether it is the shot’s
speaker in the exchange.

### cutan.verify.eyeline.REST_DIRECTION *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'right'*

the rig’s rest (`scale_x` > 0; the
factory draws its profile facing the viewer’s right).

* **Type:**
  What a character faces when nothing set it

### cutan.verify.eyeline.check_eyeline(ctx, \*, directional_views=frozenset({'side', 'three_quarter'}), rest_direction='right', share_a_place=<function \_share_a_place>)

The cut-out genre’s eyeline warnings: a speaker facing away from the one
character it speaks to, and a shot/reverse-shot pair whose speakers face the
same way. Needs the characters store, like the other turn checks (without it
the check did not run). Keyword-only parameters are the seams a host
registers its own check with (`functools.partial`): the views that show a
direction, what a character faces at rest, and what makes two shots one place.

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### cutan.verify.eyeline.cut_findings(before, after)

A shot/reverse-shot pair whose speakers face the same way (the line is jumped).

Judged only for a true pair: each shot holds exactly one character, and they
differ. The finding is on the second shot’s character, the one to turn.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`EyelineFinding`](#cutan.verify.eyeline.EyelineFinding)]

### cutan.verify.eyeline.shot_findings(present)

A speaker facing away from the one other character in the shot.

Judged only with exactly one other character, both placed, at different `x`
and a known direction: with more people the addressee is not knowable here.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`EyelineFinding`](#cutan.verify.eyeline.EyelineFinding)]
