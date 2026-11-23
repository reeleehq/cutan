# cutan.characters.framing

Shot sizes from a character’s own rig: where a close-up and a medium shot cut THIS build (cutan#106).

`an` frames a viewpoint’s `size` (`close_up`, `medium`, …) by a table on
human proportions (`an.ir.schema.SHOT_SIZES`: a close-up is the top 35 % of
the subject’s box, about the chin of a person). A factory character’s head is
about a third of its height, a squat build’s more, a tall one’s less, so the
table cuts them at the wrong place. `an` asks a kind for its own bands
(`EntityKind.shot_sizes`, genre API level 14): [`character_shot_sizes()`](#cutan.characters.framing.character_shot_sizes)
answers from the rig, by compiling the character alone (its specimen shot, the
path `an` measures its box by) and reading where its parts are drawn:

- `medium`: from the top of the box to the bottom of the `torso` part itself
  (the hips; not its children: arms hang below it);
- `close_up`: from the top to the chin, the lowest point of the `head` and
  everything drawn under it (a mouth below a small head box counts), but no
  lower than keeps a cut from medium to close-up a change of size an’s
  jump-cut check accepts (`an.verify.constraints.JUMP_CUT_SIZE_RATIO`): a
  squat build’s big head would otherwise make the two sizes nearly the same
  frame. (That holds where the frame is limited by height; a portrait frame
  limited by the subject’s width gives every size one distance, in an:
  reeleehq/an#732.)

\*\*Columns (`an.genres.API_LEVEL` 19, an#769, cutan#223).\*\* Where the `an` in use
accepts them, each band also names its own columns, `(top, bottom, left, right)`,
as fractions of the box’s width from its left: the close-up the head’s (with what is
drawn under it), the medium the head’s and the torso’s together. `an` then frames
that true width, centred on it, so a close-up stays on the head when an arm or a
prop moves the box’s centre, and it applies its own crop policy (a partial size
stays a jump-cut step nearer than the next wider one, cropping only the sides), so
the cap above is not applied. An older `an` drops 4-tuples, so it gets the
2-tuples and the cap, as before.

`wide` and `full` stay the table’s (the whole figure). A rig with no part
named `head` or `torso` (the art-package contract’s names) gives no band for
the size that needs it, and the table applies.

### Module Attributes

| [`SPECIMEN_SIZE`](#cutan.characters.framing.SPECIMEN_SIZE)     | The canvas the specimen is compiled on.                                                                                                          |
|--------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------|
| [`SIZE_RATIO_MARGIN`](#cutan.characters.framing.SIZE_RATIO_MARGIN) | How far past an's jump-cut size ratio a capped close-up lands, so a ratio computed back from the frames is never a hair under it (1.2999999...). |
| [`COLUMNS_API_LEVEL`](#cutan.characters.framing.COLUMNS_API_LEVEL) | The first `an.genres.API_LEVEL` that accepts a band's own columns (an#769).                                                                      |

### Functions

| [`character_shot_sizes`](#cutan.characters.framing.character_shot_sizes)(entity, mall, box)   | `{size: (top, bottom)}` for `entity`'s rig, as fractions of `box`'s height from its top (`box`: its measured `(x0, y0, x1, y1)`), and `(top, bottom, left, right)` where the `an` in use takes columns ([`COLUMNS_API_LEVEL`](#cutan.characters.framing.COLUMNS_API_LEVEL)); `None` when the rig has neither a head nor a torso to measure.   |
|--------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|

### cutan.characters.framing.COLUMNS_API_LEVEL *: [int](https://docs.python.org/3/builtins/functions.html#int)* *= 19*

The first `an.genres.API_LEVEL` that accepts a band’s own columns (an#769).

### cutan.characters.framing.SIZE_RATIO_MARGIN *: [float](https://docs.python.org/3/builtins/functions.html#float)* *= 1e-06*

How far past an’s jump-cut size ratio a capped close-up lands, so a ratio
computed back from the frames is never a hair under it (1.2999999…).

### cutan.characters.framing.SPECIMEN_SIZE *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[int](https://docs.python.org/3/builtins/functions.html#int), [int](https://docs.python.org/3/builtins/functions.html#int)]* *= (1280, 720)*

The canvas the specimen is compiled on. The boxes are in scene pixels
relative to the placement point, which the canvas does not change.

### cutan.characters.framing.character_shot_sizes(entity, mall, box)

`{size: (top, bottom)}` for `entity`’s rig, as fractions of `box`’s
height from its top (`box`: its measured `(x0, y0, x1, y1)`), and
`(top, bottom, left, right)` where the `an` in use takes columns
([`COLUMNS_API_LEVEL`](#cutan.characters.framing.COLUMNS_API_LEVEL)); `None` when the rig has neither a head nor a
torso to measure.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`float`](https://docs.python.org/3/builtins/functions.html#float), [`...`](https://docs.python.org/3/builtins/constants.html#Ellipsis)]] | [`None`](https://docs.python.org/3/builtins/constants.html#None)
