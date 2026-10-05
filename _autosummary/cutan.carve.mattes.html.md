# cutan.carve.mattes

Matte strategies: which pixels of an image are the subject.

A **matte** is any callable `(rgb, hint) -> alpha`: `rgb` an `HxWx3`
`uint8` array, `hint` a [`Hint`](#cutan.carve.mattes.Hint) (where the subject is, in `rgb`’s
own pixels), and `alpha` an `HxW` `float32` array in `[0, 1]` (1 is the
subject). It is the strategy seam of [`cutan.carve.carve()`](cutan.carve.html.md#cutan.carve.carve): no single
method wins (cutan#10), so each is one class here, chosen by name or passed as
an object, and two combine with `&` (both say subject) and `|` (either
does). `Polygon(points) & FlatColour()` is the hand outline cleaned by a
colour key, the recipe that won on flat cartoon frames.

```pycon
>>> import numpy as np
>>> rgb = np.full((40, 60, 3), 255, np.uint8)       # a white backdrop
>>> rgb[10:30, 20:40] = (200, 30, 30)              # a red square on it
>>> alpha = FlatColour()(rgb, Hint())
>>> round(float(alpha[20, 30]), 2), round(float(alpha[2, 2]), 2)
(1.0, 0.0)
>>> both = FlatColour() & Polygon([(20, 10), (30, 10), (30, 30), (20, 30)])
>>> float(both(rgb, Hint())[20, 35]) < 0.5         # inside the key, outside the outline
True
>>> red = ~FlatColour(colours=[(200, 30, 30)], connected=False)
>>> float(red(rgb, Hint())[20, 30]), float(red(rgb, Hint())[2, 2])
(1.0, 0.0)
```

### Module Attributes

| [`MATTES`](#cutan.carve.mattes.MATTES)   | The strategies by name, for `matte="<name>"`.   |
|-----------------------------------------------------------|-------------------------------------------------|

### Functions

| [`as_matte`](#cutan.carve.mattes.as_matte)(matte)                             | A [`Matte`](#cutan.carve.mattes.Matte) from a strategy's name, its recipe, a `Matte`, or any `(rgb, hint) -> alpha` callable.   |
|----------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------|
| [`border_colours`](#cutan.carve.mattes.border_colours)(rgb, \*[, max_colours, ...]) | The dominant colours of the image's border: the backdrop of a flat frame.                                                                         |
| [`register_matte`](#cutan.carve.mattes.register_matte)(cls, \*[, name])             | Make a third-party strategy nameable (`matte="<name>"`) and its recipes replayable: `register_matte(SamMatte)` (or as a class decorator).         |

### Classes

| [`Chroma`](#cutan.carve.mattes.Chroma)([hue, width, min_sat, min_val, ramp])    | Key out a saturated backdrop by its hue band (a stage drape, a green screen).   |
|--------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------|
| [`FlatColour`](#cutan.carve.mattes.FlatColour)([colours, tolerance, softness, ...]) | Key out the backdrop's flat colours, where they are connected to the border.    |
| [`Focus`](#cutan.carve.mattes.Focus)([window])                                 | The sharp region of an image whose background is out of focus.                  |
| [`GrabCut`](#cutan.carve.mattes.GrabCut)([box, iterations, margin, seed])        | OpenCV's GrabCut inside a box around one object.                                |
| [`Hint`](#cutan.carve.mattes.Hint)([box, point, offset, scale])               | Where the subject is, in the pixels of the image the matte is given.            |
| [`Levels`](#cutan.carve.mattes.Levels)([of, lo, range])                         | Re-map another matte's alpha: `clip((alpha - lo) / range, 0, 1)`.               |
| [`Matte`](#cutan.carve.mattes.Matte)()                                         | Base of the shipped strategies: a name, a recipe, and `&`, `|`, `~`.            |
| [`MatteLike`](#cutan.carve.mattes.MatteLike)(\*args, \*\*kwargs)                   | Anything that mattes: `(rgb, hint) -> alpha`.                                   |
| [`Polygon`](#cutan.carve.mattes.Polygon)([points, supersample])                  | A hand-given outline, `[(x, y), ...]` in the SOURCE image, anti-aliased.        |
| [`Rembg`](#cutan.carve.mattes.Rembg)([model, post_process])                    | `rembg`'s neural background removal (`pip install "cutan[rembg]"`).             |

### *class* cutan.carve.mattes.Chroma(hue=None, width=60.0, min_sat=0.28, min_val=0.03, ramp=10.0)

Bases: [`Matte`](#cutan.carve.mattes.Matte)

Key out a saturated backdrop by its hue band (a stage drape, a green screen).

`hue`: `(low, high)` in degrees (`high < low` wraps through red);
`None` centres a band `width` degrees wide on the border’s median hue.
A pixel is backdrop when its hue is in the band (`ramp` degrees soft at
each end), its saturation above `min_sat` and its value above `min_val`
(each with a soft ramp), so dark and grey pixels of the subject stay.

#### band(rgb)

The hue band in degrees: the declared one, or the border’s.

* **Return type:**
  [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`float`](https://docs.python.org/3/builtins/functions.html#float), [`float`](https://docs.python.org/3/builtins/functions.html#float)]

### *class* cutan.carve.mattes.FlatColour(colours=None, tolerance=24.0, softness=16.0, edge=2.0, connected=True, seeds=None)

Bases: [`Matte`](#cutan.carve.mattes.Matte)

Key out the backdrop’s flat colours, where they are connected to the border.

`colours`: the backdrop colours (RGB); `None` reads them off the
image’s border ([`border_colours()`](#cutan.carve.mattes.border_colours)). A pixel within `tolerance` (the
largest per-channel difference) of one is backdrop, with a `softness`
ramp beyond it for anti-aliased edges — but only within `edge` px (source
pixels) of the backdrop, so a subject colour a little off the backdrop’s
(a pale grey on white) stays solid inside instead of turning see-through.
`connected` keeps only backdrop regions that touch the image border (or
the `seeds`), so a white interior enclosed by an outline (an eye, a
shirt) stays in the subject.

### *class* cutan.carve.mattes.Focus(window=15)

Bases: [`Matte`](#cutan.carve.mattes.Matte)

The sharp region of an image whose background is out of focus.

Local detail (the Laplacian’s magnitude, averaged over `window` px) is
thresholded by Otsu’s method, closed, and its holes filled.

### *class* cutan.carve.mattes.GrabCut(box=None, iterations=8, margin=0.02, seed=0)

Bases: [`Matte`](#cutan.carve.mattes.Matte)

OpenCV’s GrabCut inside a box around one object.

`box`: `(x0, y0, x1, y1)` in the SOURCE image; `None` takes the
hint’s box, else the whole image less a `margin` share on each side.
`seed` seeds OpenCV’s random generator before the cut, so a recorded
recipe replays to the same matte.

### *class* cutan.carve.mattes.Hint(box=None, point=None, offset=(0.0, 0.0), scale=1.0)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Where the subject is, in the pixels of the image the matte is given.

`box` is `(x0, y0, x1, y1)` around the subject, `point` one pixel on
it. `to_local` maps a point given in the SOURCE image (before the crop
and the upscale [`carve()`](cutan.carve.html.md#cutan.carve.carve) applies) into these pixels,
for strategies that take coordinates (a polygon, a GrabCut box).

```pycon
>>> Hint(offset=(100, 50), scale=2.0).to_local([(110, 60)])
[(20.0, 20.0)]
```

### *class* cutan.carve.mattes.Levels(of=None, lo=0.4, range=0.35)

Bases: [`Matte`](#cutan.carve.mattes.Matte)

Re-map another matte’s alpha: `clip((alpha - lo) / range, 0, 1)`.

Raising `lo` drops a neural matte’s faint halo (the head carver’s
`edge_lo`); not the same as `choke`, which pulls the edge in by pixels.

### cutan.carve.mattes.MATTES *: [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [type](https://docs.python.org/3/builtins/functions.html#type)[[Matte](#cutan.carve.mattes.Matte)]]* *= {'chroma': <class 'cutan.carve.mattes.Chroma'>, 'flat_colour': <class 'cutan.carve.mattes.FlatColour'>, 'focus': <class 'cutan.carve.mattes.Focus'>, 'grabcut': <class 'cutan.carve.mattes.GrabCut'>, 'levels': <class 'cutan.carve.mattes.Levels'>, 'polygon': <class 'cutan.carve.mattes.Polygon'>, 'rembg': <class 'cutan.carve.mattes.Rembg'>}*

The strategies by name, for `matte="<name>"`.

### *class* cutan.carve.mattes.Matte

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Base of the shipped strategies: a name, a recipe, and `&`, `|`, `~`.

`recipe()` is what provenance records about how a part was cut: the
strategy’s name under `"matte"` and its constructor’s arguments (never
the image), plain JSON. It is also data a carve can be replayed from:
`as_matte(m.recipe())` builds the same matte.

#### otherwise(other, , min_coverage=0.01)

This matte, or `other` when this one keeps less than `min_coverage`
of the image (the head carver’s retry with another model on an empty matte).

* **Return type:**
  [`Matte`](#cutan.carve.mattes.Matte)

### *class* cutan.carve.mattes.MatteLike(\*args, \*\*kwargs)

Bases: [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol)

Anything that mattes: `(rgb, hint) -> alpha`.

### *class* cutan.carve.mattes.Polygon(points=(), supersample=4)

Bases: [`Matte`](#cutan.carve.mattes.Matte)

A hand-given outline, `[(x, y), ...]` in the SOURCE image, anti-aliased.

### *class* cutan.carve.mattes.Rembg(model='isnet-general-use', post_process=True)

Bases: [`Matte`](#cutan.carve.mattes.Matte)

`rembg`’s neural background removal (`pip install "cutan[rembg]"`).

`model`: a rembg model name (`isnet-general-use` for photos and faces,
`isnet-anime` for drawn figures, `u2net_human_seg` for people). The
model is downloaded by rembg on first use and its session kept for the
process.

### cutan.carve.mattes.as_matte(matte)

A [`Matte`](#cutan.carve.mattes.Matte) from a strategy’s name, its recipe, a `Matte`, or any
`(rgb, hint) -> alpha` callable.

A recipe (`Matte.recipe()`, as a carve records it) builds the same matte
back, so a strategy with its settings is plain data (a batch spec, a CLI):

* **Return type:**
  [`Matte`](#cutan.carve.mattes.Matte)

```pycon
>>> as_matte("chroma").name
'chroma'
>>> m = as_matte({"matte": "and", "of": [{"matte": "chroma", "width": 40},
...                                      {"matte": "polygon", "points": [[0, 0], [9, 0], [9, 9]]}]})
>>> m.recipe() == as_matte(m.recipe()).recipe(), m.recipe()["of"][0]["width"]
(True, 40)
>>> as_matte("rainbow")
Traceback (most recent call last):
  ...
ValueError: no matte strategy 'rainbow'; the strategies are: chroma, flat_colour, ...
```

### cutan.carve.mattes.border_colours(rgb, , max_colours=3, min_share=0.08, bits=4)

The dominant colours of the image’s border: the backdrop of a flat frame.

Border pixels are binned at `bits` per channel; every bin holding at least
`min_share` of the border (up to `max_colours`, most frequent first)
gives one colour, the median of its pixels.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`int`](https://docs.python.org/3/builtins/functions.html#int), [`int`](https://docs.python.org/3/builtins/functions.html#int), [`int`](https://docs.python.org/3/builtins/functions.html#int)]]

```pycon
>>> img = np.zeros((20, 20, 3), np.uint8); img[:] = (250, 240, 230)
>>> border_colours(img)
[(250, 240, 230)]
```

### cutan.carve.mattes.register_matte(cls, , name=None)

Make a third-party strategy nameable (`matte="<name>"`) and its recipes
replayable: `register_matte(SamMatte)` (or as a class decorator). The name
is the class’s `name`; registering a different class under a taken name
is refused, so a recorded recipe never changes meaning.

* **Return type:**
  [`type`](https://docs.python.org/3/builtins/functions.html#type)[[`Matte`](#cutan.carve.mattes.Matte)]
