# cutan.carve.head

Head mode: a face located, the neck cut under the jaw, the head normalised on a fixed canvas.

A carved head is useful only if every head from every source lands the same
way on its canvas, so a rig can take any of them: the face box is scaled to a
fixed height ([`HEAD_FACE_H`](#cutan.carve.head.HEAD_FACE_H)) and centred on a fixed point
([`HEAD_CENTRE`](#cutan.carve.head.HEAD_CENTRE)) of a square canvas ([`HEAD_CANVAS`](#cutan.carve.head.HEAD_CANVAS)), and that point
is the part’s origin (its anchor). The neck is cut just under the jaw,
following the jaw’s contour when landmarks give one (a neck is narrower than
the jaw, so the cut dips at the chin), and straight across under the chin for
a profile, where landmarks fail.

The face comes from a [`Face`](#cutan.carve.head.Face) (a box, optionally a jaw contour) given by
hand, or from a locator: any `rgb -> list[Face]` callable. The shipped
locator wraps `insightface` (`pip install "cutan[faces]"`); on cartoon
frames detectors usually find nothing, and a hand box is the way.

### Module Attributes

| [`HEAD_CANVAS`](#cutan.carve.head.HEAD_CANVAS)   | Side of the square canvas a head is normalised onto, px.   |
|----------------------------------------------------------------|------------------------------------------------------------|
| [`HEAD_FACE_H`](#cutan.carve.head.HEAD_FACE_H)   | Height the face box is scaled to, px.                      |
| [`HEAD_CENTRE`](#cutan.carve.head.HEAD_CENTRE)   | the head part's origin.                                    |

### Functions

| [`neck_cut`](#cutan.carve.head.neck_cut)(shape, face, \*[, cut, neck, soft, ...])   | A `shape` mask, 1 above the neck cut and 0 below, with a soft edge.        |
|------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------|
| [`pick_face`](#cutan.carve.head.pick_face)(faces[, pick])                            | One face of several: `largest`, `leftmost`, `rightmost` or `best` (score). |

### Classes

| [`Face`](#cutan.carve.head.Face)(box[, jaw, score, landmarks])              | A face in an image: its box and, when known, its jaw contour.                      |
|--------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------|
| [`InsightFaceLocator`](#cutan.carve.head.InsightFaceLocator)(\*[, model, min_score, ...]) | Faces and their jaw contours from `insightface` (106 landmarks; 0–32 are the jaw). |

### *class* cutan.carve.head.Face(box, jaw=None, score=1.0, landmarks=None)

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

JSON-ready, the inverse of [`of()`](#cutan.carve.head.Face.of).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

#### *property* chin_y *: [float](https://docs.python.org/3/builtins/functions.html#float)*

The lowest point of the jaw, else the box’s bottom.

#### *classmethod* of(face)

A face from a `Face`, a box `(x0, y0, x1, y1)`, or a mapping (`box`, `jaw`, …).

* **Return type:**
  [`Face`](#cutan.carve.head.Face)

```pycon
>>> Face.of({"box": [0, 0, 10, 12], "jaw": [[0, 6], [5, 12], [10, 6]]}).chin_y
12.0
```

### cutan.carve.head.HEAD_CANVAS *: [int](https://docs.python.org/3/builtins/functions.html#int)* *= 512*

Side of the square canvas a head is normalised onto, px.

### cutan.carve.head.HEAD_CENTRE *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[float](https://docs.python.org/3/builtins/functions.html#float), [float](https://docs.python.org/3/builtins/functions.html#float)]* *= (256.0, 300.0)*

the head part’s origin.

* **Type:**
  Where the face box’s centre lands on the canvas

### cutan.carve.head.HEAD_FACE_H *: [float](https://docs.python.org/3/builtins/functions.html#float)* *= 270.0*

Height the face box is scaled to, px.

### *class* cutan.carve.head.InsightFaceLocator(, model='buffalo_l', min_score=0.4, det_size=960)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Faces and their jaw contours from `insightface` (106 landmarks; 0–32 are the jaw).

`min_score` drops weak detections; the model (`buffalo_l`) is fetched
by insightface on first use and kept for the process.

### cutan.carve.head.neck_cut(shape, face, , cut='auto', neck=None, soft=0.05, offset=(0.0, 0.0), scale=1.0)

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

### cutan.carve.head.pick_face(faces, pick='largest')

One face of several: `largest`, `leftmost`, `rightmost` or `best` (score).

* **Return type:**
  [`Face`](#cutan.carve.head.Face)

```pycon
>>> pick_face([Face((0, 0, 10, 10)), Face((50, 0, 70, 20))]).box
(50.0, 0.0, 70.0, 20.0)
```
