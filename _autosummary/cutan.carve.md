# cutan.carve

Carve: a photo or a video frame in, a matted, normalised, provenance-carrying cut-out part out (cutan#10).

Every production that carves parts re-wrote the same pipeline by hand:
locate → crop → matte → cut → de-spill → normalise → publish with provenance.
This is that pipeline once, with the matte as a strategy seam, because no
single method wins: a colour key beats a neural matte on flat cartoon frames,
a neural matte wins on photos, GrabCut on a single prop in a rough box.

```pycon
>>> import numpy as np
>>> frame = np.full((90, 120, 3), 245, np.uint8)            # a flat backdrop
>>> frame[20:70, 30:90] = (40, 110, 200)                    # a prop on it
>>> part = carve(frame, point=(60, 45))                     # flat_colour, the default
>>> part.size, part.anchor, part.quality.warnings()
((70, 60), (0.5, 0.5), [])
```

- **One part:** [`carve()`](#cutan.carve.carve) (`matte=` a name from `MATTES` or a
  [`Matte`](#cutan.carve.Matte); `Polygon(points) & FlatColour()` is a hand outline cleaned
  > by a key). A video frame comes from [`grab_frame()`](#cutan.carve.grab_frame).
- **A head:** [`carve_head()`](#cutan.carve.carve_head) cuts the neck under the jaw and puts the face
  on a fixed canvas (512², the face centre as origin); the face is a hand box
  or found by a locator (`insightface`, `pip install "cutan[faces]"`).
- **Moving parts:** [`split_parts()`](#cutan.carve.split_parts) lifts parts off a carving, each with a
  pivot (clock hands off the face), painting the base in under them.
- **Provenance:** [`frame_source()`](#cutan.carve.frame_source) (a licence is required, a YouTube URL
  gets its `&t=` deep link); [`write_prop()`](#cutan.carve.write_prop) writes `prop.json` +
  `parts/` with the source in the descriptor, recipe and quality included,
  so `an library publish` gets the rights by construction.
- **Quality:** every [`Carving`](#cutan.carve.Carving) carries [`CarveQuality`](#cutan.carve.CarveQuality) (coverage,
  backdrop left on the rim, how much de-spill repainted, a see-through
  interior, glyphs left attached or cut off, a subject cut off by the crop);
  `quality.warnings()` says which look wrong.
- **Data, not code:** every coordinate is in the source’s pixels, and a
  carving’s `recipe` is its arguments by name, the matte as its recipe
  (`as_matte` reads one back): `carve(frame, **part.recipe)` replays it,
  so a batch of carves is a list of recipes.

Needs OpenCV: `pip install "cutan[carve]"` (`check_requirements()` lists
what is installed). Nothing here is imported by `import cutan`.

### Functions

| [`as_matte`](#cutan.carve.as_matte)(matte)                                   | A [`Matte`](#cutan.carve.Matte) from a strategy's name, its recipe, a `Matte`, or any `(rgb, hint) -> alpha` callable.   |
|----------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------|
| [`border_colours`](#cutan.carve.border_colours)(rgb, \*[, max_colours, ...])       | The dominant colours of the image's border: the backdrop of a flat frame.                                                                         |
| [`carve`](#cutan.carve.carve)(image, \*[, matte, crop, box, point, ...])  | Cut a part out of `image`; every coordinate is in the source image's pixels.                                                                      |
| [`carve_head`](#cutan.carve.carve_head)(image, \*[, face, locate, pick, ...])  | A head cut out at the neck and normalised onto a `canvas`-px square.                                                                              |
| [`check_requirements`](#cutan.carve.check_requirements)(\*[, verbose])                 | Which optional dependencies of carving are installed (printing how to get the rest).                                                              |
| [`frame_source`](#cutan.carve.frame_source)(url, \*, license[, t, author, ...])  | The provenance of a part carved from `url` (a video at time `t`, or an image).                                                                    |
| [`grab_frame`](#cutan.carve.grab_frame)(video, t, \*[, ffmpeg])                | The frame of `video` at `t` seconds, as RGB (needs the `ffmpeg` binary).                                                                          |
| [`load_rgb`](#cutan.carve.load_rgb)(image)                                   | An `HxWx3` `uint8` RGB array from a path, a PIL image or an array.                                                                                |
| [`neck_cut`](#cutan.carve.neck_cut)(shape, face, \*[, cut, neck, soft, ...]) | A `shape` mask, 1 above the neck cut and 0 below, with a soft edge.                                                                               |
| [`pick_face`](#cutan.carve.pick_face)(faces[, pick])                          | One face of several: `largest`, `leftmost`, `rightmost` or `best` (score).                                                                        |
| [`register_matte`](#cutan.carve.register_matte)(cls, \*[, name])                   | Make a third-party strategy nameable (`matte="<name>"`) and its recipes replayable: `register_matte(SamMatte)` (or as a class decorator).         |
| [`split_parts`](#cutan.carve.split_parts)(carving, parts, \*[, paint_out, ...]) | Lift `parts` (`{name: PartSpec}`, in draw order) off `carving`.                                                                                   |
| [`write_prop`](#cutan.carve.write_prop)(carved, folder, \*[, name, unit, ...]) | Write `carved` to `folder` as `prop.json` + `parts/*.png`; return the descriptor.                                                                 |
| [`youtube_id`](#cutan.carve.youtube_id)(url)                                   | The video id of a YouTube URL, else `None`.                                                                                                       |

### Classes

| [`CarveQuality`](#cutan.carve.CarveQuality)(coverage, rim_backdrop_share, ...)   | Signals worth reading before a part is used (cutan#10).                                 |
|----------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------|
| [`Carving`](#cutan.carve.Carving)(image, anchor, offset, scale, ...[, ...]) | A carved part.                                                                          |
| [`Chroma`](#cutan.carve.Chroma)([hue, width, min_sat, min_val, ramp])      | Key out a saturated backdrop by its hue band (a stage drape, a green screen).           |
| [`Face`](#cutan.carve.Face)(box[, jaw, score, landmarks])                | A face in an image: its box and, when known, its jaw contour.                           |
| [`FlatColour`](#cutan.carve.FlatColour)([colours, tolerance, softness, ...])   | Key out the backdrop's flat colours, where they are connected to the border.            |
| [`Focus`](#cutan.carve.Focus)([window])                                   | The sharp region of an image whose background is out of focus.                          |
| [`GrabCut`](#cutan.carve.GrabCut)([box, iterations, margin, seed])          | OpenCV's GrabCut inside a box around one object.                                        |
| [`Hint`](#cutan.carve.Hint)([box, point, offset, scale])                 | Where the subject is, in the pixels of the image the matte is given.                    |
| [`InsightFaceLocator`](#cutan.carve.InsightFaceLocator)(\*[, model, min_score, ...])   | Faces and their jaw contours from `insightface` (106 landmarks; 0–32 are the jaw).      |
| [`Levels`](#cutan.carve.Levels)([of, lo, range])                           | Re-map another matte's alpha: `clip((alpha - lo) / range, 0, 1)`.                       |
| [`Matte`](#cutan.carve.Matte)()                                           | Base of the shipped strategies: a name, a recipe, and `&`, `|`, `~`.                    |
| [`Part`](#cutan.carve.Part)(name, image, pivot, origin, draw_order)      | One lifted part: its RGBA image, its pivot in that image, where it sits in the carving. |
| [`PartSet`](#cutan.carve.PartSet)(carving, base[, parts])                   | A carving split into a base (`None` when every pixel went to a part) and parts.         |
| [`PartSpec`](#cutan.carve.PartSpec)(mask, pivot[, grow, reach])              | What to lift off a carving: a `mask` and the `pivot` it turns about.                    |
| [`Polygon`](#cutan.carve.Polygon)([points, supersample])                    | A hand-given outline, `[(x, y), ...]` in the SOURCE image, anti-aliased.                |
| [`Rembg`](#cutan.carve.Rembg)([model, post_process])                      | `rembg`'s neural background removal (`pip install "cutan[rembg]"`).                     |

### Exceptions

| [`MissingDependencyError`](#cutan.carve.MissingDependencyError)   | An optional dependency of `cutan.carve` is not installed.   |
|---------------------------------------------------------------------------|-------------------------------------------------------------|

### *class* cutan.carve.CarveQuality(coverage, rim_backdrop_share, repainted_share, soft_interior_share, detached_pieces, attached_pieces, touches_edge)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Signals worth reading before a part is used (cutan#10).

`coverage`: the subject’s share of the carved region (near 0 or 1 means
the matte took nothing or everything). `rim_backdrop_share`: the share
of the part’s partly transparent edge whose colour is still close to the
backdrop’s (a halo). `repainted_share`: the share of the subject whose
colour de-spill replaced (high means it repainted real content: lower
`despill`). `soft_interior_share`: the share of the subject’s interior
(3 px or more inside its edge) that is see-through. `detached_pieces`:
pieces `detach` cut off; `attached_pieces`: pieces still hanging on
the subject by a neck under 4 px (caption glyphs, or a genuinely thin
part). `touches_edge`: the subject runs into the carved region’s border,
so the crop probably cut it off.

#### warnings()

The signals that look wrong, in words.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

### *class* cutan.carve.Carving(image, anchor, offset, scale, quality, recipe, source=None, meta=<factory>, mode='part')

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A carved part.

`image`: the RGBA part. `anchor`: its origin as `(u, v)` in 0..1 of
the image (Pixi’s convention, an `Attachment.anchor`): the point for a
plain carve, the face centre for a head. `to_part` maps a source pixel
into the part’s pixels (`part = (source - offset) * scale`; the 2×3
matrix is `meta["source_to_part"]`). `mode` is `"part"` or
`"head"`; `recipe` the arguments it was made with (replayable:
`carve(image, **recipe)` or `carve_head`); `source` the provenance;
`quality` the signals; `meta` mode-specific facts.

#### *property* alpha *: ndarray*

The alpha channel as floats in 0..1.

#### provenance()

The source with how it was carved in its `extra.carve`: the mode, the
recipe, the quality and where the part sits in the source.

* **Return type:**
  `AssetSource` | [`None`](https://docs.python.org/3/builtins/constants.html#None)

#### to_part(points)

Source pixels to this part’s pixels.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`float`](https://docs.python.org/3/builtins/functions.html#float), [`float`](https://docs.python.org/3/builtins/functions.html#float)]]

### *class* cutan.carve.Chroma(hue=None, width=60.0, min_sat=0.28, min_val=0.03, ramp=10.0)

Bases: [`Matte`](cutan.carve.mattes.md#cutan.carve.mattes.Matte)

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

### *class* cutan.carve.Face(box, jaw=None, score=1.0, landmarks=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A face in an image: its box and, when known, its jaw contour.

`box` is `(x0, y0, x1, y1)`; `jaw` a sequence of `(x, y)` points
along the jaw, ear to ear (any order, at least three); `landmarks` the
detector’s full set when there is one (kept, mapped onto the canvas, so a
later step can place eyes and mouth without re-carving); `score` the
detector’s confidence (1 for a hand box).

```pycon
>>> f = Face((10, 20, 50, 80))
>>> f.width, f.height, f.centre, f.chin_y
(40.0, 60.0, (30.0, 50.0), 80.0)
```

#### as_dict()

JSON-ready, the inverse of [`of()`](#cutan.carve.Face.of).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

#### *property* chin_y *: [float](https://docs.python.org/3/builtins/functions.html#float)*

The lowest point of the jaw, else the box’s bottom.

#### *classmethod* of(face)

A face from a `Face`, a box `(x0, y0, x1, y1)`, or a mapping (`box`, `jaw`, …).

* **Return type:**
  [`Face`](cutan.carve.head.md#cutan.carve.head.Face)

```pycon
>>> Face.of({"box": [0, 0, 10, 12], "jaw": [[0, 6], [5, 12], [10, 6]]}).chin_y
12.0
```

### *class* cutan.carve.FlatColour(colours=None, tolerance=24.0, softness=16.0, edge=2.0, connected=True, seeds=None)

Bases: [`Matte`](cutan.carve.mattes.md#cutan.carve.mattes.Matte)

Key out the backdrop’s flat colours, where they are connected to the border.

`colours`: the backdrop colours (RGB); `None` reads them off the
image’s border ([`border_colours()`](#cutan.carve.border_colours)). A pixel within `tolerance` (the
largest per-channel difference) of one is backdrop, with a `softness`
ramp beyond it for anti-aliased edges — but only within `edge` px (source
pixels) of the backdrop, so a subject colour a little off the backdrop’s
(a pale grey on white) stays solid inside instead of turning see-through.
`connected` keeps only backdrop regions that touch the image border (or
the `seeds`), so a white interior enclosed by an outline (an eye, a
shirt) stays in the subject.

### *class* cutan.carve.Focus(window=15)

Bases: [`Matte`](cutan.carve.mattes.md#cutan.carve.mattes.Matte)

The sharp region of an image whose background is out of focus.

Local detail (the Laplacian’s magnitude, averaged over `window` px) is
thresholded by Otsu’s method, closed, and its holes filled.

### *class* cutan.carve.GrabCut(box=None, iterations=8, margin=0.02, seed=0)

Bases: [`Matte`](cutan.carve.mattes.md#cutan.carve.mattes.Matte)

OpenCV’s GrabCut inside a box around one object.

`box`: `(x0, y0, x1, y1)` in the SOURCE image; `None` takes the
hint’s box, else the whole image less a `margin` share on each side.
`seed` seeds OpenCV’s random generator before the cut, so a recorded
recipe replays to the same matte.

### *class* cutan.carve.Hint(box=None, point=None, offset=(0.0, 0.0), scale=1.0)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Where the subject is, in the pixels of the image the matte is given.

`box` is `(x0, y0, x1, y1)` around the subject, `point` one pixel on
it. `to_local` maps a point given in the SOURCE image (before the crop
and the upscale [`carve()`](#cutan.carve.carve) applies) into these pixels,
for strategies that take coordinates (a polygon, a GrabCut box).

```pycon
>>> Hint(offset=(100, 50), scale=2.0).to_local([(110, 60)])
[(20.0, 20.0)]
```

### *class* cutan.carve.InsightFaceLocator(, model='buffalo_l', min_score=0.4, det_size=960)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Faces and their jaw contours from `insightface` (106 landmarks; 0–32 are the jaw).

`min_score` drops weak detections; the model (`buffalo_l`) is fetched
by insightface on first use and kept for the process.

### *class* cutan.carve.Levels(of=None, lo=0.4, range=0.35)

Bases: [`Matte`](cutan.carve.mattes.md#cutan.carve.mattes.Matte)

Re-map another matte’s alpha: `clip((alpha - lo) / range, 0, 1)`.

Raising `lo` drops a neural matte’s faint halo (the head carver’s
`edge_lo`); not the same as `choke`, which pulls the edge in by pixels.

### *class* cutan.carve.Matte

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
  [`Matte`](cutan.carve.mattes.md#cutan.carve.mattes.Matte)

### *exception* cutan.carve.MissingDependencyError

Bases: [`ImportError`](https://docs.python.org/3/builtins/exceptions.html#ImportError)

An optional dependency of `cutan.carve` is not installed.

### *class* cutan.carve.Part(name, image, pivot, origin, draw_order)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

One lifted part: its RGBA image, its pivot in that image, where it sits in the carving.

#### *property* anchor *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[float](https://docs.python.org/3/builtins/functions.html#float), [float](https://docs.python.org/3/builtins/functions.html#float)]*

The pivot as an attachment anchor (0..1 of the image).

### *class* cutan.carve.PartSet(carving, base, parts=<factory>)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A carving split into a base (`None` when every pixel went to a part) and parts.

### *class* cutan.carve.PartSpec(mask, pivot, grow=1, reach=None)

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

### *class* cutan.carve.Polygon(points=(), supersample=4)

Bases: [`Matte`](cutan.carve.mattes.md#cutan.carve.mattes.Matte)

A hand-given outline, `[(x, y), ...]` in the SOURCE image, anti-aliased.

### *class* cutan.carve.Rembg(model='isnet-general-use', post_process=True)

Bases: [`Matte`](cutan.carve.mattes.md#cutan.carve.mattes.Matte)

`rembg`’s neural background removal (`pip install "cutan[rembg]"`).

`model`: a rembg model name (`isnet-general-use` for photos and faces,
`isnet-anime` for drawn figures, `u2net_human_seg` for people). The
model is downloaded by rembg on first use and its session kept for the
process.

### cutan.carve.as_matte(matte)

A [`Matte`](#cutan.carve.Matte) from a strategy’s name, its recipe, a `Matte`, or any
`(rgb, hint) -> alpha` callable.

A recipe (`Matte.recipe()`, as a carve records it) builds the same matte
back, so a strategy with its settings is plain data (a batch spec, a CLI):

* **Return type:**
  [`Matte`](cutan.carve.mattes.md#cutan.carve.mattes.Matte)

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

### cutan.carve.border_colours(rgb, , max_colours=3, min_share=0.08, bits=4)

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

### cutan.carve.carve(image, , matte='flat_colour', crop=None, box=None, point=None, keep='point', fill_holes=True, detach=0, choke=0, feather=0.6, despill=1, upscale=1, pad=4, source=None)

Cut a part out of `image`; every coordinate is in the source image’s pixels.

* **Return type:**
  [`Carving`](cutan.carve.core.md#cutan.carve.core.Carving)

image: a path, a PIL image or an RGB(A) array (`grab_frame` for video)
matte: the strategy ([`cutan.carve.mattes`](cutan.carve.mattes.md#module-cutan.carve.mattes)): a name, a recipe mapping,

> a `Matte` (`Polygon(pts) & FlatColour()`) or any `(rgb, hint) -> alpha`

crop: `(x0, y0, x1, y1)`, the region carved (default: the whole image)
box: a box around the subject (GrabCut’s default rectangle)
point: a pixel on the subject; `keep="point"` keeps its component, and it

> becomes the part’s anchor (default: the part’s centre)

keep: `"point"` (its component and pieces within a few px), `"largest"`
: or `"all"` components

fill_holes: fill what the subject encloses (a pale face the matte missed)
detach: cut off pieces hanging on the subject by a neck narrower than

> `2 * detach` px (caption letters; also any part that thin); 0 keeps
> them and reports them

choke: pull the edge in by this many px, then `feather` softens it (px)
despill: re-paint the edge from the subject’s pixels at least this many px

> inside it (1: the anti-aliased band; about 4 for a neural matte’s
> fuzzy fringe; 0: off)

upscale: matte at this whole factor of the source resolution, then come
: back: smoother edges on small or low-resolution subjects

pad: transparent px left around the trimmed part
source: provenance ([`frame_source()`](cutan.carve.provenance.md#cutan.carve.provenance.frame_source)), kept

> with the recipe and the quality in `Carving.provenance()`
```pycon
>>> img = np.full((60, 80, 3), 250, np.uint8); img[15:45, 20:60] = (30, 90, 200)
>>> part = carve(img)
>>> part.size, round(part.quality.coverage, 2), part.quality.warnings()
((50, 40), 0.25, [])
>>> carve(img, **part.recipe).recipe == part.recipe     # the recipe replays the carve
True
```

### cutan.carve.carve_head(image, , face=None, locate=None, pick='largest', matte='flat_colour', cut='auto', neck=None, neck_soft=0.05, pad_x=1.05, pad_top=1.25, pad_bottom=1.0, upscale=3, keep='point', fill_holes=True, detach=0, choke=0, feather=0.6, despill=1, canvas=512, face_h=270.0, centre=(256.0, 300.0), margin=6, view=None, source=None)

A head cut out at the neck and normalised onto a `canvas`-px square.

* **Return type:**
  [`Carving`](cutan.carve.core.md#cutan.carve.core.Carving)

face: the face, a [`Face`](cutan.carve.head.md#cutan.carve.head.Face) (box and, when known, a
: jaw contour and landmarks), a box `(x0, y0, x1, y1)` or a mapping
  (`Face.as_dict()`); `None` runs `locate`

locate: a face locator `rgb -> [Face]` (default
: [`InsightFaceLocator`](cutan.carve.head.md#cutan.carve.head.InsightFaceLocator), `cutan[faces]`);
  `pick` chooses among several faces

cut: the neck cut, `"auto"` (along the jaw when the face has a contour,
: else flat under the chin), `"jaw"`, `"flat"` or `"none"`;
  `neck` its depth in face-box heights, `neck_soft` its soft edge

pad_x, pad_top, pad_bottom: the crop around the face, in face-box widths
: (each side) and heights (above, below)

upscale: matte at this whole factor (heads are small in a frame)
face_h, centre: the face box is scaled to `face_h` px high and its

> centre put on `centre`, unless the head would then leave the canvas
> (less `margin`), in which case it is scaled down to fit

view: the view the head is drawn in, one of the rig’s views (`front`,
: `three_quarter`, `side`, `back`), recorded for the step that puts
  it on a rig; `None` when unknown

The rest are [`carve()`](#cutan.carve.carve)’s (`despill` in source px: a neural matte on
a photo wants about 4). The recipe pins the face, so a replay is
reproducible whether it was given or located (`meta["located_by"]` says
which); a batch spec is `{**shared_settings, **per_item}` (the face and
the crop per image, the matte and the finish shared). The part’s anchor is `centre` (the face centre);
`meta` holds what a rig needs to hang it: the face box, the chin and the
neck point, the head’s bounding box, the landmarks, all on the canvas.

### cutan.carve.check_requirements(, verbose=True)

Which optional dependencies of carving are installed (printing how to get the rest).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`bool`](https://docs.python.org/3/builtins/functions.html#bool)]

```pycon
>>> sorted(check_requirements(verbose=False))
['cv2', 'insightface', 'rembg']
```

### cutan.carve.frame_source(url, , license, t=None, author=None, author_url=None, title=None, provider=None, attribution=None, note=None, cacheable=True, \*\*extra)

The provenance of a part carved from `url` (a video at time `t`, or an image).

`license` is required (keyword-only, no default): `None` records the
rights as UNKNOWN, which is a statement too. For footage you do not own,
`"all-rights-reserved"` (`an credits` then lists the part as NOT
PUBLISHABLE). A YouTube URL is normalised to its watch page (tracking
parameters dropped) with a `&t=` deep link; `t` defaults to the URL’s
own. Any other URL keeps its scheme, host and path only (no password, no
query: signed-URL tokens are credentials). A local file (a path, a
`file:` URL) is recorded by its name only: provider `local`, the name
in `extra.file`, no path anywhere; a `data:` URI is refused. `t`,
`title` and `note` go into `extra` beside any other keyword.

* **Return type:**
  `AssetSource`

```pycon
>>> s = frame_source("https://www.youtube.com/watch?v=AAGIi62-sAU&si=track",
...                  t=34.6, license="all-rights-reserved", author="OverSimplified")
>>> s.provider, s.id, s.url
('youtube', 'AAGIi62-sAU', 'https://www.youtube.com/watch?v=AAGIi62-sAU&t=34')
>>> s.source_page_url, s.extra["frame_time_s"]
('https://www.youtube.com/watch?v=AAGIi62-sAU', 34.6)
>>> frame_source("https://youtu.be/AAGIi62-sAU?t=1m30s", license=None).extra["frame_time_s"]
90.0
>>> local = frame_source("/home/me/private/clip.mp4", t=3, license="all-rights-reserved")
>>> local.provider, local.url, local.extra["file"], "/home" in local.attribution
('local', None, 'clip.mp4', False)
```

### cutan.carve.grab_frame(video, t, , ffmpeg='ffmpeg')

The frame of `video` at `t` seconds, as RGB (needs the `ffmpeg` binary).

* **Return type:**
  `ndarray`

### cutan.carve.load_rgb(image)

An `HxWx3` `uint8` RGB array from a path, a PIL image or an array.

* **Return type:**
  `ndarray`

```pycon
>>> load_rgb(np.zeros((4, 5, 4), np.uint8)).shape
(4, 5, 3)
```

### cutan.carve.neck_cut(shape, face, , cut='auto', neck=None, soft=0.05, offset=(0.0, 0.0), scale=1.0)

A `shape` mask, 1 above the neck cut and 0 below, with a soft edge.

`cut`: `"jaw"` follows the jaw contour (ends extended past the ears,
deeper at the chin), `"flat"` cuts straight across under the chin,
`"auto"` is `jaw` when the face has a contour and `flat` otherwise,
and `"none"` keeps everything. `neck` is the depth below the jaw (or
the chin) in face-box heights. `offset`/`scale` map the face (given in
source pixels) into the mask’s pixels.

* **Return type:**
  `ndarray`

```pycon
>>> m = neck_cut((100, 50), Face((10, 10, 40, 60)), cut="flat", neck=0.1)
>>> float(m[50, 25]), float(m[90, 25])
(1.0, 0.0)
```

### cutan.carve.pick_face(faces, pick='largest')

One face of several: `largest`, `leftmost`, `rightmost` or `best` (score).

* **Return type:**
  [`Face`](cutan.carve.head.md#cutan.carve.head.Face)

```pycon
>>> pick_face([Face((0, 0, 10, 10)), Face((50, 0, 70, 20))]).box
(50.0, 0.0, 70.0, 20.0)
```

### cutan.carve.register_matte(cls, , name=None)

Make a third-party strategy nameable (`matte="<name>"`) and its recipes
replayable: `register_matte(SamMatte)` (or as a class decorator). The name
is the class’s `name`; registering a different class under a taken name
is refused, so a recorded recipe never changes meaning.

* **Return type:**
  [`type`](https://docs.python.org/3/builtins/functions.html#type)[[`Matte`](cutan.carve.mattes.md#cutan.carve.mattes.Matte)]

### cutan.carve.split_parts(carving, parts, , paint_out=True, inpaint_radius=4, pad=2)

Lift `parts` (`{name: PartSpec}`, in draw order) off `carving`.

Each part takes the carving’s pixels under its mask. Parts are drawn in
the order listed, the last on top, and the one drawn on top owns a pixel
two masks share (a clock’s hub cap, listed after the hands, keeps the hub).
The base keeps the rest, and stays opaque under a part’s soft edge (no
seam at rest); where a part was enclosed by the base, `paint_out`
re-paints the base under it (`cv2.inpaint`) so it stays whole when the
part moves. A part’s `origin` and `pivot` are in the carving’s pixels
(where [`write_prop()`](#cutan.carve.write_prop) places it).

* **Return type:**
  [`PartSet`](cutan.carve.parts.md#cutan.carve.parts.PartSet)

### cutan.carve.write_prop(carved, folder, , name=None, unit=None, max_side=None, display_name=None, source=None, ours=False, relicense=None, overwrite=False)

Write `carved` to `folder` as `prop.json` + `parts/*.png`; return the descriptor.

* **Return type:**
  `PropDescriptor`

name: the prop’s name (default: the folder’s name)
unit: view_box units per carved pixel (default 1); or `max_side`: the

> unit that makes the longer side that many units (never above 1)

source: overrides the carving’s provenance (its recipe and quality are
: still recorded in `extra.carve`, its source in `extra.carved_from`)

ours: the pixels are the caller’s own art (a carving with no source)
relicense: `{"by": who, "reason": why}` (both non-empty), required for a

> `source` that loosens the carving’s licence class. Recorded in the
> descriptor’s `source.extra.relicensed`; `an library publish` does not
> read it, so say it again there (`relicense=`) when publishing.

A [`PartSet`](#cutan.carve.PartSet) is written with its carving’s provenance:
build one with [`split_parts()`](#cutan.carve.split_parts) (its parts are cut from
that carving), never by hand from other carvings’ parts.

The root bone sits at the carving’s anchor. A split prop gets one bone per
part, at its pivot, parented to the root, and one slot per part above the
base, in the order the parts were listed. Nothing is written unless the
whole descriptor is valid.

### cutan.carve.youtube_id(url)

The video id of a YouTube URL, else `None`.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

```pycon
>>> youtube_id("https://www.youtube.com/watch?v=AAGIi62-sAU&t=34")
'AAGIi62-sAU'
>>> youtube_id("https://youtu.be/AAGIi62-sAU?t=3"), youtube_id("https://example.org/a.png")
('AAGIi62-sAU', None)
>>> youtube_id("https://notyoutube.com/watch?v=x"), youtube_id("https://WWW.YOUTUBE.COM:443/shorts/abc")
(None, 'abc')
```

### Modules

| [`core`](cutan.carve.core.md#module-cutan.carve.core)             | The carve pipeline: an image (or a video frame) in, a matted, cleaned, provenance-carrying part out.   |
|-------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------|
| [`head`](cutan.carve.head.md#module-cutan.carve.head)             | Head mode: a face located, the neck cut under the jaw, the head normalised on a fixed canvas.          |
| [`mattes`](cutan.carve.mattes.md#module-cutan.carve.mattes)         | Matte strategies: which pixels of an image are the subject.                                            |
| [`parts`](cutan.carve.parts.md#module-cutan.carve.parts)           | Split a carved prop into moving parts, each with a declared pivot.                                     |
| [`prop`](cutan.carve.prop.md#module-cutan.carve.prop)             | Write a carving (or a carving split into parts) as a library-ready prop folder.                        |
| [`provenance`](cutan.carve.provenance.md#module-cutan.carve.provenance) | Where carved pixels came from: an `AssetSource` for a frame of a video or an image.                    |
| [`refine`](cutan.carve.refine.md#module-cutan.carve.refine)         | Clean a raw matte into a cut-out's alpha: keep the subject, close it, edge it, de-spill it.            |
