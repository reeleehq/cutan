# cutan.carve.core

The carve pipeline: an image (or a video frame) in, a matted, cleaned, provenance-carrying part out.

[`carve()`](#cutan.carve.core.carve) runs crop → (upscale) → matte → keep → fill holes → detach
bridges → choke → feather → de-spill → trim, and returns a [`Carving`](#cutan.carve.core.Carving):
the RGBA part, where it came from in the source, its anchor, its quality
signals, and the recipe that cut it (recorded with its provenance).
[`carve_head()`](#cutan.carve.core.carve_head) is the same pipeline with a neck cut and the head
normalised onto a fixed canvas ([`cutan.carve.head`](cutan.carve.head.md#module-cutan.carve.head)).

**Every coordinate a caller gives is in the source image’s pixels** (crop,
box, point, a polygon’s points, a face, a part’s pivot), so a spec can be
written before anything is carved. A carving’s `recipe` holds the
arguments it was made with, under their own names, so `carve(image,
\*\*part.recipe)` (or `carve_head`) replays it: a batch of carves is data.

### Module Attributes

| [`KEEP`](#cutan.carve.core.KEEP)   | The finishing defaults [`carve()`](#cutan.carve.core.carve) and [`carve_head()`](#cutan.carve.core.carve_head) share (one place, so the two cannot drift): keep the component under the point, fill what the subject encloses, detach nothing, no choke, a 0.6 px feather, de-spill 1 px.   |
|---------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|

### Functions

| [`carve`](#cutan.carve.core.carve)(image, \*[, matte, crop, box, point, ...])   | Cut a part out of `image`; every coordinate is in the source image's pixels.   |
|-----------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------|
| [`carve_head`](#cutan.carve.core.carve_head)(image, \*[, face, locate, pick, ...])   | A head cut out at the neck and normalised onto a `canvas`-px square.           |
| [`grab_frame`](#cutan.carve.core.grab_frame)(video, t, \*[, ffmpeg])                 | The frame of `video` at `t` seconds, as RGB (needs the `ffmpeg` binary).       |
| [`load_rgb`](#cutan.carve.core.load_rgb)(image)                                    | An `HxWx3` `uint8` RGB array from a path, a PIL image or an array.             |

### Classes

| [`CarveQuality`](#cutan.carve.core.CarveQuality)(coverage, rim_backdrop_share, ...)   | Signals worth reading before a part is used (cutan#10).   |
|----------------------------------------------------------------------------------------------------|-----------------------------------------------------------|
| [`Carving`](#cutan.carve.core.Carving)(image, anchor, offset, scale, ...[, ...]) | A carved part.                                            |

### *class* cutan.carve.core.CarveQuality(coverage, rim_backdrop_share, repainted_share, soft_interior_share, detached_pieces, attached_pieces, touches_edge)

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

### *class* cutan.carve.core.Carving(image, anchor, offset, scale, quality, recipe, source=None, meta=<factory>, mode='part')

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

### cutan.carve.core.KEEP *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'point'*

The finishing defaults [`carve()`](#cutan.carve.core.carve) and [`carve_head()`](#cutan.carve.core.carve_head) share (one place,
so the two cannot drift): keep the component under the point, fill what the
subject encloses, detach nothing, no choke, a 0.6 px feather, de-spill 1 px.

### cutan.carve.core.carve(image, , matte='flat_colour', crop=None, box=None, point=None, keep='point', fill_holes=True, detach=0, choke=0, feather=0.6, despill=1, upscale=1, pad=4, source=None)

Cut a part out of `image`; every coordinate is in the source image’s pixels.

* **Return type:**
  [`Carving`](#cutan.carve.core.Carving)

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

### cutan.carve.core.carve_head(image, , face=None, locate=None, pick='largest', matte='flat_colour', cut='auto', neck=None, neck_soft=0.05, pad_x=1.05, pad_top=1.25, pad_bottom=1.0, upscale=3, keep='point', fill_holes=True, detach=0, choke=0, feather=0.6, despill=1, canvas=512, face_h=270.0, centre=(256.0, 300.0), margin=6, view=None, source=None)

A head cut out at the neck and normalised onto a `canvas`-px square.

* **Return type:**
  [`Carving`](#cutan.carve.core.Carving)

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

The rest are [`carve()`](#cutan.carve.core.carve)’s (`despill` in source px: a neural matte on
a photo wants about 4). The recipe pins the face, so a replay is
reproducible whether it was given or located (`meta["located_by"]` says
which); a batch spec is `{**shared_settings, **per_item}` (the face and
the crop per image, the matte and the finish shared). The part’s anchor is `centre` (the face centre);
`meta` holds what a rig needs to hang it: the face box, the chin and the
neck point, the head’s bounding box, the landmarks, all on the canvas.

### cutan.carve.core.grab_frame(video, t, , ffmpeg='ffmpeg')

The frame of `video` at `t` seconds, as RGB (needs the `ffmpeg` binary).

* **Return type:**
  `ndarray`

### cutan.carve.core.load_rgb(image)

An `HxWx3` `uint8` RGB array from a path, a PIL image or an array.

* **Return type:**
  `ndarray`

```pycon
>>> load_rgb(np.zeros((4, 5, 4), np.uint8)).shape
(4, 5, 3)
```
