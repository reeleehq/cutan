# cutan.carve.parts

Split a carved prop into moving parts, each with a declared pivot.

A clock’s hands come off its face, a camera into tripod, body and lens: each
part is lifted out of a [`Carving`](cutan.carve.html.md#cutan.carve.Carving) by a mask, gets a pivot
(the point it turns about), and the base keeps what is left. Where a part
lay *inside* the base (a hand on the face), the base is painted in under it
from the surrounding pixels, so the part can move without leaving a hole;
where it stuck *out* (a lens past the body), the base simply loses it.

Masks and pivots are in the SOURCE image’s pixels, like every other
coordinate [`cutan.carve`](cutan.carve.html.md#module-cutan.carve) takes, so a part spec can be written before the
carve runs (the carving’s trim decides its own pixels). A mask may also be an
array of the carving’s size.

```pycon
>>> import numpy as np
>>> from cutan.carve import carve
>>> img = np.full((40, 60, 3), 250, np.uint8); img[10:30, 10:50] = (200, 40, 40)
>>> img[18:22, 30:46] = (40, 40, 200)                        # a blue hand on a red face
>>> face = carve(img, point=(20, 20))
>>> split = split_parts(face, {"hand": PartSpec(mask=[(29, 17), (47, 17), (47, 23), (29, 23)],
...                                             pivot=(30, 20))})
>>> hand = split.parts[0]
>>> (hand.origin[0] + hand.pivot[0], hand.origin[1] + hand.pivot[1]) == face.to_part([(30, 20)])[0]
True
>>> tuple(int(v) for v in np.asarray(split.base)[10, 35])   # painted in under the hand, opaque
(200, 40, 40, 255)
```

### Functions

| [`split_parts`](#cutan.carve.parts.split_parts)(carving, parts, \*[, paint_out, ...])   | Lift `parts` (`{name: PartSpec}`, in draw order) off `carving`.   |
|------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------|

### Classes

| [`Part`](#cutan.carve.parts.Part)(name, image, pivot, origin, draw_order)   | One lifted part: its RGBA image, its pivot in that image, where it sits in the carving.   |
|-------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------|
| [`PartSet`](#cutan.carve.parts.PartSet)(carving, base[, parts])                | A carving split into a base (`None` when every pixel went to a part) and parts.           |
| [`PartSpec`](#cutan.carve.parts.PartSpec)(mask, pivot[, grow, reach])           | What to lift off a carving: a `mask` and the `pivot` it turns about.                      |

### *class* cutan.carve.parts.Part(name, image, pivot, origin, draw_order)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

One lifted part: its RGBA image, its pivot in that image, where it sits in the carving.

#### *property* anchor *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[float](https://docs.python.org/3/builtins/functions.html#float), [float](https://docs.python.org/3/builtins/functions.html#float)]*

The pivot as an attachment anchor (0..1 of the image).

### *class* cutan.carve.parts.PartSet(carving, base, parts=<factory>)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A carving split into a base (`None` when every pixel went to a part) and parts.

### *class* cutan.carve.parts.PartSpec(mask, pivot, grow=1, reach=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

What to lift off a carving: a `mask` and the `pivot` it turns about.

`mask`: a polygon `[(x, y), ...]` in source pixels, a matte called on
the carving’s RGB with the carving’s frame as its hint (so a matte’s own
coordinates are source pixels too; `~FlatColour(colours=[grey],
connected=False)` selects the grey strokes), or an array of the carving’s
size (bool or 0..1). `pivot`: `(x, y)` in source pixels. `grow`:
carving px the mask is widened by before lifting (anti-aliased strokes).
`reach`: keep only the mask’s pieces that come within this many source
px of the pivot (a colour key also matches specks elsewhere: a tick’s grey
edge).

### cutan.carve.parts.split_parts(carving, parts, , paint_out=True, inpaint_radius=4, pad=2)

Lift `parts` (`{name: PartSpec}`, in draw order) off `carving`.

Each part takes the carving’s pixels under its mask. Parts are drawn in
the order listed, the last on top, and the one drawn on top owns a pixel
two masks share (a clock’s hub cap, listed after the hands, keeps the hub).
The base keeps the rest, and stays opaque under a part’s soft edge (no
seam at rest); where a part was enclosed by the base, `paint_out`
re-paints the base under it (`cv2.inpaint`) so it stays whole when the
part moves. A part’s `origin` and `pivot` are in the carving’s pixels
(where [`write_prop()`](cutan.carve.html.md#cutan.carve.write_prop) places it).

* **Return type:**
  [`PartSet`](#cutan.carve.parts.PartSet)
