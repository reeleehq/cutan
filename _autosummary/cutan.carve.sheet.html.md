# cutan.carve.sheet

A reference sheet becomes an art package: carve each region, set it on the rig (cutan#128).

A character delivered as a reference sheet (front, three-quarter, side and back
views; a face sheet of mouth shapes) used to become a rig only by hand: carve each
view, cut the parts at the joints, point the descriptor at them, read every
quality warning. This is that recipe, as data over two components that exist:
[`carve()`](cutan.carve.html.md#cutan.carve.carve) cuts a region of the sheet, and
[`set_part()`](cutan.characters.set_part.html.md#cutan.characters.set_part.set_part) draws a factory attachment with the
result. The rig (bones, slots, swap sets, the contract) is a factory character’s
(`an character new`); the sheet supplies its drawings.

A recipe is a list of [`SheetPart`](#cutan.carve.sheet.SheetPart): an attachment’s name, the region of the
sheet that holds it, and the `carve` arguments for it (the matte as its recipe,
so a recipe is JSON). Cutting at a joint is a polygon matte over the same sheet:
`{"matte": {"name": "polygon", ...}}` composed with a key. A part whose carve
gives a `point` (a pixel on the subject) takes that point as the attachment’s
anchor, so the joint a neck or a shoulder turns about is where the rig puts it.

```pycon
>>> from cutan.carve.sheet import SheetPart
>>> SheetPart("head", crop=(0, 0, 100, 120), carve={"point": (50, 90)}).attachment
'head'
```

Every part is carved, and every attachment named, BEFORE the character is
touched, and a failure while setting the parts puts the character back as it
was, so a bad recipe changes nothing. Provenance is required, as for
[`write_prop()`](cutan.carve.html.md#cutan.carve.write_prop): the sheet’s `source` (`frame_source`), or
`ours=True` for pixels that are the caller’s. The report carries each part’s
quality warnings in words, for the writer to read before anything renders.

Moving parts that share one carving (a torso and its arms, a clock face and its
hands) are one [`SheetPart`](#cutan.carve.sheet.SheetPart) with a `split`: the region is carved once,
[`split_parts()`](cutan.carve.html.md#cutan.carve.split_parts) lifts each named part at its mask with its pivot
as the attachment’s anchor, and the part’s own attachment draws what is left.

A picture is drawn at the width of the factory drawing it replaces, so parts from
one sheet would lose their relative scale. The recipe’s `unit` (view-box units
per sheet pixel) declares each picture’s width from its carved size instead: one
unit for the whole sheet, so a hand stays as long next to a body as on the sheet.
A part with no `point` keeps the factory’s anchor, which belongs to a different
picture’s framing (the report says so). With a `unit` a split part is also
placed: its attachment’s offset is set so its pivot is drawn where the sheet has it
from the base’s anchor, as the rig builder draws both
([`cutan.characters.placement.place_attachment()`](cutan.characters.placement.html.md#cutan.characters.placement.place_attachment)); the attachments of that
slot drawn by the same file move with it, while view keys drawn by other files
keep their own offset. Without a `unit`, or when the base is drawn turned or
scaled at rest, the report gives the offset in sheet pixels instead.

The recipe as a document is [`load_recipe()`](#cutan.carve.sheet.load_recipe) (`schema_version` 1).

Needs OpenCV: `pip install "cutan[carve]"`.

### Module Attributes

| [`RECIPE_SCHEMA_VERSION`](#cutan.carve.sheet.RECIPE_SCHEMA_VERSION)   | The recipe document's version, written as `schema_version`.   |
|--------------------------------------------------------------------------|---------------------------------------------------------------|

### Functions

| [`load_recipe`](#cutan.carve.sheet.load_recipe)(doc)                             | The [`Recipe`](#cutan.carve.sheet.Recipe) of a recipe document.   |
|-----------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------|
| [`sheet_to_package`](#cutan.carve.sheet.sheet_to_package)(sheet, parts, char_dir, \*) | Carve `parts` out of `sheet` and draw them on the factory character at `char_dir`.  |

### Classes

| [`PartResult`](#cutan.carve.sheet.PartResult)(attachment, warnings, replacement)     | What became of one part: the descriptor change and the quality warnings.                                      |
|----------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------|
| [`SheetPart`](#cutan.carve.sheet.SheetPart)(attachment[, crop, carve, mode, split]) | One attachment and where on the sheet it is drawn.                                                            |
| [`Recipe`](#cutan.carve.sheet.Recipe)(parts, source, ours, unit)                 | A recipe document read: `sheet_to_package(sheet, **recipe._asdict(), ...)`.                                   |
| [`SheetReport`](#cutan.carve.sheet.SheetReport)(parts)                                | The package built: one [`PartResult`](#cutan.carve.sheet.PartResult) per part, in recipe order. |

### *class* cutan.carve.sheet.PartResult(attachment, warnings, replacement)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

What became of one part: the descriptor change and the quality warnings.

### cutan.carve.sheet.RECIPE_SCHEMA_VERSION *= 1*

The recipe document’s version, written as `schema_version`.

### *class* cutan.carve.sheet.Recipe(parts, source, ours, unit)

Bases: [`NamedTuple`](https://docs.python.org/3/library/typing.html#typing.NamedTuple)

A recipe document read: `sheet_to_package(sheet, **recipe._asdict(), ...)`.

#### ours *: [bool](https://docs.python.org/3/builtins/functions.html#bool)*

Alias for field number 2

#### parts *: [list](https://docs.python.org/3/builtins/stdtypes.html#list)[[SheetPart](#cutan.carve.sheet.SheetPart)]*

Alias for field number 0

#### source *: AssetSource | [None](https://docs.python.org/3/builtins/constants.html#None)*

Alias for field number 1

#### unit *: [float](https://docs.python.org/3/builtins/functions.html#float) | [None](https://docs.python.org/3/builtins/constants.html#None)*

Alias for field number 3

### *class* cutan.carve.sheet.SheetPart(attachment, crop=None, carve=dict(), mode='part', split=dict())

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

One attachment and where on the sheet it is drawn.

attachment: the attachment’s name (`head`, `mouth_a`), or `slot/name`
crop: `(x0, y0, x1, y1)` in the sheet’s pixels, the region carved

> (`mode="part"`; a head is located by `carve["face"]` instead)

carve: the other arguments of the carver (`matte`, `point`, `keep`,
: `superres`…), JSON-able; a `point` anchors the part

mode: `"part"` ([`carve()`](cutan.carve.html.md#cutan.carve.carve)) or `"head"`
: ([`carve_head()`](cutan.carve.html.md#cutan.carve.carve_head): neck cut, fixed canvas, face centre as anchor)

split: `{attachment: PartSpec or its dict}`: moving parts lifted off this
: carving ([`split_parts()`](cutan.carve.html.md#cutan.carve.split_parts); masks and pivots in the
  sheet’s pixels). Each is drawn by its own attachment, anchored at its
  pivot; `attachment` above draws the base, what is left

#### *property* anchored *: [bool](https://docs.python.org/3/builtins/functions.html#bool)*

Does the carve fix the anchor (a `point`, or a head’s face centre)?

### *class* cutan.carve.sheet.SheetReport(parts)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

The package built: one [`PartResult`](#cutan.carve.sheet.PartResult) per part, in recipe order.

#### *property* derived *: [list](https://docs.python.org/3/builtins/stdtypes.html#list)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)]*

Factory drawings derived from a replaced part (its views, lid states,
mouth variants) still in use: they will not match the new picture.

#### *property* warnings *: [list](https://docs.python.org/3/builtins/stdtypes.html#list)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)]*

Every part’s warnings, each led by its attachment’s name.

### cutan.carve.sheet.load_recipe(doc)

The [`Recipe`](#cutan.carve.sheet.Recipe) of a recipe document.

`{"schema_version": 1, "source": {frame_source's arguments} | null,
"ours": false, "unit": null, "parts": [{"attachment", "crop", "carve",
"mode", "split"}]}`

* **Return type:**
  [`Recipe`](#cutan.carve.sheet.Recipe)

### cutan.carve.sheet.sheet_to_package(sheet, parts, char_dir, , source=None, ours=False, unit=None, work_dir=None)

Carve `parts` out of `sheet` and draw them on the factory character at `char_dir`.

sheet: a path, a PIL image or an array (the whole reference sheet)
parts: the recipe, [`SheetPart`](#cutan.carve.sheet.SheetPart) or their dicts; each file the rig

> draws from is replaced once (two attachments of one file are one part)

source: the sheet’s provenance (`frame_source`); required unless `ours`
ours: the sheet’s pixels are the caller’s own art (no source is recorded)
unit: view-box units per SHEET pixel (`write_prop`’s is per carved pixel;

> they differ under super-resolution); each picture is declared that many
> units wide per carved pixel (default: the factory drawing’s width)

work_dir: where the carved pictures are first written (default: a temporary
: folder, gone afterwards; the rig keeps its own copy beside it either way)

Raises `ValueError` before anything is written when provenance is
missing, an attachment is unknown, ambiguous or shares its file with another
part; if setting a part fails, the character is restored.

* **Return type:**
  [`SheetReport`](#cutan.carve.sheet.SheetReport)
