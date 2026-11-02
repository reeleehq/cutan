# cutan.verify.regions

Mouth and body cadence apart: “mouths on ones, bodies on twos” made measurable (cutan#80).

The style lint ([`cutan.verify.style`](cutan.verify.style.html.md#module-cutan.verify.style)) measures the whole frame, so a
lip-synced line on a still body reads as body motion. For an `an` render the
mouth is known at every frame, from the compiled shots:

- **mouth**: a step changes the mouth when a mouth’s swap channel (`viseme`,
  and its `viseme@<form>` variants) changes value between the two frames:
  exactly the lip-sync’s own steps, whatever the head does around it;
- **body**: the lint’s own change rule (`changes_from_stats()`)
  on the picture with the mouths’ boxes left out. A mouth’s art can draw past
  its box (an open viseme), so each box is grown by [`MOUTH_GROW`](#cutan.verify.regions.MOUTH_GROW) of its
  size before it is left out.

The mouths are found by their channel, not by a node’s name: any node a
`viseme` set swaps. [`mouth_track()`](#cutan.verify.regions.mouth_track) compiles the shots and reads the
channel and the boxes (from the IR shots, not yet exactly the render’s
preparation: reeleehq/an#733); [`split_cadence()`](#cutan.verify.regions.split_cadence) measures, streaming the frames
(no per-pixel mask of the whole film is held). Reference footage has no rig,
so this measures our renders only (a face locator for footage is research).

### Module Attributes

| [`MOUTH_CHANNEL`](#cutan.verify.regions.MOUTH_CHANNEL)     | The swap channel that draws a mouth (and its `viseme@<form>` variants).                                                                                                         |
|--------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`MOUTH_GROW`](#cutan.verify.regions.MOUTH_GROW)        | Each mouth box is grown by this share of its own width and height on every side before the body is measured without it: an open viseme draws past the box the closed one sizes. |
| [`MOUTH_GROW_MAX_PX`](#cutan.verify.regions.MOUTH_GROW_MAX_PX) | a close-up's mouth (88x33 decode px on the corpus expressions scene) grown by its own size would hide the brows and the blinks from the body.                                   |
| [`CHUNK_FRAMES`](#cutan.verify.regions.CHUNK_FRAMES)      | Frames are read this many at a time when the body is measured.                                                                                                                  |

### Functions

| [`mouth_track`](#cutan.verify.regions.mouth_track)(project, \*, n, fps, size, ...[, ...])   | Where the mouths are, and what they show, in each of the film's `n` frames, at the decode `size` (w, h) of a render at `render_size` (w, h).   |
|-------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------|
| [`region_findings`](#cutan.verify.regions.region_findings)(regions)                             | One line for the lint's report: the mouth's and the body's cadence.                                                                            |
| [`split_cadence`](#cutan.verify.regions.split_cadence)(frames, track, \*, fps[, ...])         | `{"mouth": cadence, "body": cadence}` of `frames` (`(n, h, w, 3)`), in the lint's own statistics (`cutan.verify.style.cadence_of()`).          |

### Classes

| [`MouthTrack`](#cutan.verify.regions.MouthTrack)([boxes, states])   | Per film frame: the mouths' boxes (decode pixels, grown) and the values of their swap channels (a change of value is a mouth step).   |
|--------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------|

### cutan.verify.regions.CHUNK_FRAMES *: [int](https://docs.python.org/3/builtins/functions.html#int)* *= 256*

Frames are read this many at a time when the body is measured.

### cutan.verify.regions.MOUTH_CHANNEL *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'viseme'*

The swap channel that draws a mouth (and its `viseme@<form>` variants).

### cutan.verify.regions.MOUTH_GROW *: [float](https://docs.python.org/3/builtins/functions.html#float)* *= 1.0*

Each mouth box is grown by this share of its own width and height on every
side before the body is measured without it: an open viseme draws past the
box the closed one sizes. Measured on the corpus dialogue render (a mouth box
4 render px tall): at 0.5 two lip-sync steps still leaked into the body, at
1.0 none did, and only the head’s real move remained.

### cutan.verify.regions.MOUTH_GROW_MAX_PX *: [int](https://docs.python.org/3/builtins/functions.html#int)* *= 8*

a close-up’s mouth
(88x33 decode px on the corpus expressions scene) grown by its own size would
hide the brows and the blinks from the body.

* **Type:**
  …but by no more than this many decode pixels a side

### *class* cutan.verify.regions.MouthTrack(boxes=list(), states=list())

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Per film frame: the mouths’ boxes (decode pixels, grown) and the values of
their swap channels (a change of value is a mouth step).

#### states *: [list](https://docs.python.org/3/builtins/stdtypes.html#list)[[dict](https://docs.python.org/3/builtins/stdtypes.html#dict)]*

per frame, `{mouth node path: its swap channels' values}` for each mouth
drawn in the frame (an off-screen mouth is not drawn)

### cutan.verify.regions.mouth_track(project, , n, fps, size, render_size, grow=1.0, grow_max_px=8)

Where the mouths are, and what they show, in each of the film’s `n`
frames, at the decode `size` (w, h) of a render at `render_size` (w, h).
Each shot is compiled (a world lowered first), placed at its film start
(`an.assemble.film_timeline`) and read over its whole length, so during a
dissolve both shots’ mouths count.

* **Return type:**
  [`MouthTrack`](#cutan.verify.regions.MouthTrack)

### cutan.verify.regions.region_findings(regions)

One line for the lint’s report: the mouth’s and the body’s cadence.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### cutan.verify.regions.split_cadence(frames, track, , fps, cut_steps=(), min_changed_pixels=8)

`{"mouth": cadence, "body": cadence}` of `frames` (`(n, h, w, 3)`),
in the lint’s own statistics (`cutan.verify.style.cadence_of()`). A mouth
step is a change of a mouth channel’s value; a body step is the lint’s rule
on the picture with the boxes of both frames of the step left out.
`cut_steps`: steps into a cut, left out of cadence as the lint does.

```pycon
>>> f = np.zeros((5, 20, 20, 3), np.uint8)
>>> f[1:3, 2:4, 2:4] = 255                       # the mouth opens at 1, shuts at 3
>>> t = MouthTrack([[(1, 1, 5, 5)]] * 5, [{"m": v} for v in "XAAXX"])
>>> out = split_cadence(f, t, fps=12.0, min_changed_pixels=1)
>>> out["mouth"]["pose_changes_per_s"] > 0, out["body"]["pose_changes_per_s"]
(True, 0.0)
```

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`float`](https://docs.python.org/3/builtins/functions.html#float)]]
