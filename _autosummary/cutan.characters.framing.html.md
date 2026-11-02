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

`wide` and `full` stay the table’s (the whole figure). A rig with no part
named `head` or `torso` (the art-package contract’s names) gives no band for
the size that needs it, and the table applies.

### Module Attributes

| [`SPECIMEN_SIZE`](#cutan.characters.framing.SPECIMEN_SIZE)     | The canvas the specimen is compiled on.                                                                                                          |
|--------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------|
| [`SIZE_RATIO_MARGIN`](#cutan.characters.framing.SIZE_RATIO_MARGIN) | How far past an's jump-cut size ratio a capped close-up lands, so a ratio computed back from the frames is never a hair under it (1.2999999...). |

### Functions

| [`character_shot_sizes`](#cutan.characters.framing.character_shot_sizes)(entity, mall, box)   | `{size: (top, bottom)}` for `entity`'s rig, as fractions of `box`'s height from its top (`box`: its measured `(x0, y0, x1, y1)`); `None` when the rig has neither a head nor a torso to measure.   |
|--------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|

### cutan.characters.framing.SIZE_RATIO_MARGIN *: [float](https://docs.python.org/3/builtins/functions.html#float)* *= 1e-06*

How far past an’s jump-cut size ratio a capped close-up lands, so a ratio
computed back from the frames is never a hair under it (1.2999999…).

### cutan.characters.framing.SPECIMEN_SIZE *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[int](https://docs.python.org/3/builtins/functions.html#int), [int](https://docs.python.org/3/builtins/functions.html#int)]* *= (1280, 720)*

The canvas the specimen is compiled on. The boxes are in scene pixels
relative to the placement point, which the canvas does not change.

### cutan.characters.framing.character_shot_sizes(entity, mall, box)

`{size: (top, bottom)}` for `entity`’s rig, as fractions of `box`’s
height from its top (`box`: its measured `(x0, y0, x1, y1)`); `None`
when the rig has neither a head nor a torso to measure.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`float`](https://docs.python.org/3/builtins/functions.html#float), [`float`](https://docs.python.org/3/builtins/functions.html#float)]] | [`None`](https://docs.python.org/3/builtins/constants.html#None)
