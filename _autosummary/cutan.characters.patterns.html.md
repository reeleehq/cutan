# cutan.characters.patterns

Clothing prints for the factory’s figures (cutan#94): an SVG `<pattern>` over the clothing fill.

A flat `clothing` colour cannot show a loud holiday shirt, a striped jumper or a
check suit. A [`ClothingPattern`](#cutan.characters.patterns.ClothingPattern) names a print (`stripes`, `check`,
`floral`), its colours and its scale; the factory draws it as a `<pattern>`
definition plus one overlay rect in every clothing part — the torso (front and
each view) and the arm sleeves — on top of the base fill and under the outline.
The base fill keeps its `clothing` colour role, so a style pack still
recolours it; the print’s own literals carry no role and are made distinct from
the part’s role literals, so a swap never catches them. The swap channels and
the rig contract are untouched: a print is paint, not geometry.

`tile` is a print you draw yourself: a small PNG (`MAX_TILE_SIDE` px a side,
[`MAX_TILE_BYTES`](#cutan.characters.patterns.MAX_TILE_BYTES) bytes), one pixel per rect. It is vectors on purpose: the
core refuses an `<image>` inside a part’s SVG (an#211: it hides its pixels from
every check), and the tile’s bytes live in the recorded spec as base64, so the
factory’s recipe replays it on any machine (a file path could not be replayed).
[`read_tile()`](#cutan.characters.patterns.read_tile) turns a file into that base64.

A spec is one string on the command line or one mapping in the descriptor:

```default
floral:base=#e8735a,motif=#ffffff,leaf=#2f6b3a
tile:image=<base64 of a small PNG>,base=#345678
stripes
check:scale=0.7
none
```

```pycon
>>> p = parse_clothing_pattern("floral:base=#e8735a,motif=#fff")
>>> p.kind, p.base, p.motif, p.leaf, p.scale
('floral', '#e8735a', '#ffffff', '#2f6b3a', 1.0)
>>> parse_clothing_pattern("none") is None and parse_clothing_pattern(None) is None
True
>>> parse_clothing_pattern({"kind": "stripes", "scale": 0.5}).as_dict()
{'kind': 'stripes', 'scale': 0.5}
```

### Module Attributes

| [`PATTERN_KINDS`](#cutan.characters.patterns.PATTERN_KINDS)   | The prints the factory draws; `none` is the flat default.                |
|------------------------------------------------------------------|--------------------------------------------------------------------------|
| [`MAX_TILE_BYTES`](#cutan.characters.patterns.MAX_TILE_BYTES)  | its PNG's bytes (they sit in the recipe, which is bounded) and its side. |
| [`PATTERN_ID`](#cutan.characters.patterns.PATTERN_ID)      | The id of the `<pattern>` element in a part, referenced by its overlay.  |

### Functions

| [`parse_clothing_pattern`](#cutan.characters.patterns.parse_clothing_pattern)(spec)                 | A [`ClothingPattern`](#cutan.characters.patterns.ClothingPattern) from a spec string or mapping; `None` for no print.                                                                                          |
|-----------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`pattern_defs`](#cutan.characters.patterns.pattern_defs)(pattern)                        | The `<defs><pattern>` text a clothing part carries, in its own units.                                                                                                                                           |
| [`pattern_overlay`](#cutan.characters.patterns.pattern_overlay)(shape_attrs)                 | The overlay that paints the print over a clothing shape's base fill.                                                                                                                                            |
| [`painted_fill`](#cutan.characters.patterns.painted_fill)(shape_attrs, \*, fill, pattern) | A clothing shape's paint, without its outline: the base `fill`, then the print over it (the definition, the fill, the overlay), the one order every clothing drawer shares; the caller adds its own ink on top. |
| [`distinct_pattern`](#cutan.characters.patterns.distinct_pattern)(pattern, taken)             | The print with its literals nudged clear of `taken` (the part's role literals and its ink), so a role swap never rewrites the print.                                                                            |
| [`read_tile`](#cutan.characters.patterns.read_tile)(path)                              | A tile PNG file as the base64 a `tile` spec carries (checked on the way).                                                                                                                                       |
| [`resolve_tile_paths`](#cutan.characters.patterns.resolve_tile_paths)(spec)                     | `spec` with a file given as `image=` read into its base64, so the spec that is recorded (and replayed elsewhere) holds the bytes, not a path.                                                                   |

### Classes

| [`ClothingPattern`](#cutan.characters.patterns.ClothingPattern)(kind[, base, motif, leaf, ...])   | One print: its kind, its colours and its scale.   |
|----------------------------------------------------------------------------------------------------|---------------------------------------------------|

### *class* cutan.characters.patterns.ClothingPattern(kind, base=None, motif='#f4f1ea', leaf='#2f6b3a', scale=1.0, image=None, palette=())

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

One print: its kind, its colours and its scale.

#### as_dict()

The spec as a mapping, defaults left out: what the descriptor records.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

#### image *: [Optional](https://docs.python.org/3/library/typing.html#typing.Optional)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)]* *= None*

the PNG, base64 (what the descriptor records).

* **Type:**
  `tile`

#### palette *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)* *= ()*

drawn colour per colour of the image, set by [`distinct_pattern()`](#cutan.characters.patterns.distinct_pattern).

* **Type:**
  `tile`

### cutan.characters.patterns.MAX_TILE_BYTES *: [int](https://docs.python.org/3/builtins/functions.html#int)* *= 3072*

its PNG’s bytes (they sit in the recipe, which is bounded) and its side.

* **Type:**
  A tile’s limits

### cutan.characters.patterns.PATTERN_ID *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'clothing_print'*

The id of the `<pattern>` element in a part, referenced by its overlay.

### cutan.characters.patterns.PATTERN_KINDS *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), ...]* *= ('none', 'stripes', 'check', 'floral', 'tile')*

The prints the factory draws; `none` is the flat default.

### cutan.characters.patterns.distinct_pattern(pattern, taken)

The print with its literals nudged clear of `taken` (the part’s role
literals and its ink), so a role swap never rewrites the print.

```pycon
>>> distinct_pattern(ClothingPattern("stripes", motif="#ffffff"), {"#ffffff"}).motif
'#fffffe'
```

* **Return type:**
  [`ClothingPattern`](#cutan.characters.patterns.ClothingPattern)

### cutan.characters.patterns.painted_fill(shape_attrs, , fill, pattern)

A clothing shape’s paint, without its outline: the base `fill`, then the
print over it (the definition, the fill, the overlay), the one order every
clothing drawer shares; the caller adds its own ink on top.

```pycon
>>> painted_fill('x="0"', fill="#fff", pattern=None)
'<rect x="0" fill="#fff"/>'
>>> out = painted_fill('x="0"', fill="#fff", pattern=ClothingPattern("check"))
>>> out.startswith("<defs>") and out.endswith('<rect x="0" fill="url(#clothing_print)"/>')
True
```

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### cutan.characters.patterns.parse_clothing_pattern(spec)

A [`ClothingPattern`](#cutan.characters.patterns.ClothingPattern) from a spec string or mapping; `None` for no print.

```pycon
>>> parse_clothing_pattern("stripes:motif=#000")
ClothingPattern(kind='stripes', base=None, motif='#000000', leaf='#2f6b3a', scale=1.0)
>>> parse_clothing_pattern("plaid")
Traceback (most recent call last):
...
ValueError: unknown clothing pattern 'plaid'; known: none, stripes, check, floral, tile
>>> parse_clothing_pattern("stripes:leaf=#000")
Traceback (most recent call last):
...
ValueError: clothing pattern 'stripes' takes base, motif, scale; not 'leaf'
```

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`ClothingPattern`](#cutan.characters.patterns.ClothingPattern)]

### cutan.characters.patterns.pattern_defs(pattern)

The `<defs><pattern>` text a clothing part carries, in its own units.

```pycon
>>> 'patternUnits="userSpaceOnUse"' in pattern_defs(ClothingPattern("check"))
True
```

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### cutan.characters.patterns.pattern_overlay(shape_attrs)

The overlay that paints the print over a clothing shape’s base fill.

`shape_attrs` is the shape’s own geometry (a rect’s `x y width height rx ry`),
so the print is clipped to the clothing exactly as the fill is.

```pycon
>>> pattern_overlay('x="0" y="0" width="4" height="4"')
'<rect x="0" y="0" width="4" height="4" fill="url(#clothing_print)"/>'
```

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### cutan.characters.patterns.read_tile(path)

A tile PNG file as the base64 a `tile` spec carries (checked on the way).

```pycon
>>> import tempfile, pathlib
>>> from PIL import Image
>>> with tempfile.TemporaryDirectory() as d:
...     Image.new("RGBA", (2, 2), (200, 30, 30, 255)).save(pathlib.Path(d) / "t.png")
...     tile = read_tile(pathlib.Path(d) / "t.png")
>>> tile.startswith("iVBORw0KGgo") and parse_clothing_pattern({"kind": "tile", "image": tile}).kind
'tile'
```

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### cutan.characters.patterns.resolve_tile_paths(spec)

`spec` with a file given as `image=` read into its base64, so the spec
that is recorded (and replayed elsewhere) holds the bytes, not a path.

```pycon
>>> resolve_tile_paths("stripes")
'stripes'
>>> resolve_tile_paths({"kind": "tile", "image": "iVBORw0KGgoAAAA"})["image"]
'iVBORw0KGgoAAAA'
```

* **Return type:**
  [`Union`](https://docs.python.org/3/library/typing.html#typing.Union)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Mapping`](https://docs.python.org/3/library/typing.html#typing.Mapping), [`None`](https://docs.python.org/3/builtins/constants.html#None)]
