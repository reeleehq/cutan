# cutan.characters.lids

A HALF eyelid drawing, made from a character’s own OPEN and CLOSED lid art (cutan#65).

The expression solver picks an eyelid DRAWING per lid state (the ladder: wide,
open, half, closed; [`cutan.expression.axes.lid_key()`](cutan.expression.axes.md#cutan.expression.axes.lid_key)). A rig whose
`eyelid` set draws only `OPEN` and `CLOSED` shows `OPEN` for a partial
lid, so a squint, suspicion or annoyance cannot narrow the eyes, and the
validator says so. This module gives such a rig its `HALF` drawing without an
illustrator: for each eye, the CLOSED drawing clipped to its upper part, with
the OPEN drawing (its outline) laid over it. It works on any pair of SVG eye
drawings that share a view box, the factory’s or a hand-drawn rig’s.

```pycon
>>> half_lid_svg(
...     '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 32"><ellipse cx="32" cy="16" rx="14" ry="10" fill="none" stroke="#222"/></svg>',
...     '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 32"><ellipse cx="32" cy="16" rx="14" ry="10" fill="#8b5a3b"/></svg>',
... ).count("clip-path")
1
```

The `half` attachment copies the `open` one’s placement. Its source says
what it was derived from; when both drawings carry the same licence it carries
that licence too, pinned to the new file’s digest, so the asset library and
`an credits` can state it. Otherwise it is left unlabelled (UNVERIFIED), never
guessed.

### Module Attributes

| [`DFLT_HALF_LID_FRACTION`](#cutan.characters.lids.DFLT_HALF_LID_FRACTION)   | How much of the eye the half lid covers, from the top of the drawing.   |
|---------------------------------------------------------------------------|-------------------------------------------------------------------------|
| [`HALF_ATTACHMENT`](#cutan.characters.lids.HALF_ATTACHMENT)          | The attachment name the HALF key points at.                             |
| [`HALF_LID_PROVIDER`](#cutan.characters.lids.HALF_LID_PROVIDER)        | The provider of the source a derived half lid carries.                  |

### Functions

| [`add_half_lid`](#cutan.characters.lids.add_half_lid)(char_dir, \*[, fraction, overwrite])   | Give the character at `char_dir` a `HALF` eyelid drawing; return its descriptor path.   |
|------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------|
| [`half_lid_svg`](#cutan.characters.lids.half_lid_svg)(open_svg, closed_svg, \*[, fraction])  | The HALF drawing: `closed_svg` clipped to its top `fraction`, under `open_svg`.         |

### cutan.characters.lids.DFLT_HALF_LID_FRACTION *: [float](https://docs.python.org/3/builtins/functions.html#float)* *= 0.5*

How much of the eye the half lid covers, from the top of the drawing.

### cutan.characters.lids.HALF_ATTACHMENT *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'half'*

The attachment name the HALF key points at.

### cutan.characters.lids.HALF_LID_PROVIDER *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= "cutan add-half-lid (derived from the rig's own lid art)"*

The provider of the source a derived half lid carries.

### cutan.characters.lids.add_half_lid(char_dir, , fraction=0.5, overwrite=False)

Give the character at `char_dir` a `HALF` eyelid drawing; return its descriptor path.

For every slot of the default skin that holds both the `OPEN` and the
`CLOSED` attachment of the `eyelid` set, writes the half drawing beside
the open one (`eye_l_open.svg` -> `eye_l_half.svg`), adds a `half`
attachment placed like the open one, and maps `HALF` to it. Idempotent.
A rig that already has a `HALF` it did not get from here is refused
unless `overwrite`: that drawing is an illustrator’s.

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

### cutan.characters.lids.half_lid_svg(open_svg, closed_svg, , fraction=0.5)

The HALF drawing: `closed_svg` clipped to its top `fraction`, under
`open_svg`. Both must share a view box (else `HalfLidError`).

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)
