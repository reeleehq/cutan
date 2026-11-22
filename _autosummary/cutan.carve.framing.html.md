# cutan.carve.framing

A picture in a carved frame, the frame sized to the picture: one prop, both sources kept.

A wall of framed pictures (end cards, a frame from a video, a typeset card) wants one carved
picture frame reused around pictures of every aspect. [`framed()`](#cutan.carve.framing.framed) does it:

1. the frame’s **opening** (a box in the frame carving’s source pixels, like every coordinate
   [`cutan.carve`](cutan.carve.html.md#module-cutan.carve) takes) is cut out, which leaves four bands of moulding around it;
2. the frame is sized to the picture by **9-slice**: its four corners kept as carved, its top
   and bottom bands stretched across, its sides down ([`nine_slice()`](#cutan.carve.framing.nine_slice));
3. picture and frame become **two parts** of one [`PartSet`](cutan.carve.html.md#cutan.carve.PartSet) (picture under
   frame), each with its own `source`: [`write_prop()`](cutan.carve.html.md#cutan.carve.write_prop) writes the picture’s on
   its attachment, so `an credits` lists both (the frame’s is the prop’s own, with the
   9-slice recorded in its recipe);
4. an optional [`DropShadow`](#cutan.carve.framing.DropShadow) is a third, lowest part, drawn from the frame’s own alpha
   (derived, credited to the frame).

```pycon
>>> import numpy as np
>>> from cutan.carve import carve
>>> from cutan.carve.mattes import Polygon
>>> art = np.full((60, 80, 3), 255, np.uint8)
>>> art[10:50, 10:70] = (200, 160, 40)                        # a gold frame ...
>>> art[20:40, 20:60] = (90, 90, 90)                          # ... around an old picture
>>> frame = carve(art, matte=Polygon([(10, 10), (70, 10), (70, 50), (10, 50)]), point=(40, 30),
...               keep="all", feather=0, despill=0, pad=0)
>>> pic = np.zeros((100, 30, 3), np.uint8)                    # a tall new picture
>>> out = framed(pic, frame, opening=(20, 20, 60, 40), ours=True, frame_ours=True)
>>> [p.name for p in out.parts], out.carving.size
(['picture', 'frame'], (51, 121))
```

### Functions

| [`framed`](#cutan.carve.framing.framed)(picture, frame, \*, opening[, source, ...])   | `picture` inside `frame`, the frame 9-sliced to the picture's size, as a part set.                                                                               |
|-------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`nine_slice`](#cutan.carve.framing.nine_slice)(image, bands, inner)                      | `image` resized by 9-slice so the part inside `bands` is `inner` pixels: the corners as they are, the edges stretched along their length, the centre to `inner`. |
| [`open_frame`](#cutan.carve.framing.open_frame)(frame, opening)                           | The frame's image with its opening cleared, and the moulding's band widths.                                                                                      |

### Classes

| [`DropShadow`](#cutan.carve.framing.DropShadow)([offset, blur, opacity, color])   | A soft shadow of the frame on the wall: its alpha, offset, blurred, at `opacity`.   |
|-----------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------|

### *class* cutan.carve.framing.DropShadow(offset=(10, 10), blur=4.0, opacity=0.35, color=(20, 24, 28))

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A soft shadow of the frame on the wall: its alpha, offset, blurred, at `opacity`.

### cutan.carve.framing.framed(picture, frame, , opening, source=None, ours=False, frame_ours=False, moulding_scale=1.0, shadow=None, picture_part='picture', frame_part='frame', shadow_part='shadow')

`picture` inside `frame`, the frame 9-sliced to the picture’s size, as a part set.

* **Parameters:**
  * **picture** ([`Union`](https://docs.python.org/3/library/typing.html#typing.Union)[[`Carving`](cutan.carve.core.html.md#cutan.carve.core.Carving), `Image`, `ndarray`]) – a [`Carving`](cutan.carve.html.md#cutan.carve.Carving) (its provenance is the picture’s), or an image
    (`PIL.Image` or array) with `source=` (or `ours=True`).
  * **frame** ([`Carving`](cutan.carve.core.html.md#cutan.carve.core.Carving)) – the carved frame, with the picture it held still inside.
  * **opening** ([`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`float`](https://docs.python.org/3/builtins/functions.html#float), [`float`](https://docs.python.org/3/builtins/functions.html#float), [`float`](https://docs.python.org/3/builtins/functions.html#float), [`float`](https://docs.python.org/3/builtins/functions.html#float)]) – the frame’s opening, in the frame carving’s source pixels.
  * **source** ([`Any`](https://docs.python.org/3/library/typing.html#typing.Any)) – the picture’s provenance (overrides a carving’s).
  * **ours** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – the picture’s pixels are the caller’s own (a typeset card).
  * **frame_ours** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – the frame’s pixels are the caller’s own (a frame with no source).
  * **moulding_scale** ([`float`](https://docs.python.org/3/builtins/functions.html#float)) – the moulding’s size against the frame carving’s pixels (a superres
    frame is carved at 4x; a 1920 px picture wants a thicker frame than a 300 px one):
    the opened frame is resized by it before the 9-slice.
  * **shadow** ([`DropShadow`](#cutan.carve.framing.DropShadow) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – a [`DropShadow`](#cutan.carve.framing.DropShadow) part under the frame and the picture, or `None`; its
    offset and blur are in the composite’s pixels.
* **Return type:**
  [`PartSet`](cutan.carve.parts.html.md#cutan.carve.parts.PartSet)

The set’s carving is the whole composite (the parts in place), with the frame’s source as
the prop’s own: write it with [`write_prop()`](cutan.carve.html.md#cutan.carve.write_prop), whose `landmarks` are then
in the **composite’s** pixels, not a source’s (a hook at `(width / 2, 0)`).

### cutan.carve.framing.nine_slice(image, bands, inner)

`image` resized by 9-slice so the part inside `bands` is `inner` pixels: the corners
as they are, the edges stretched along their length, the centre to `inner`.

```pycon
>>> im = Image.new("RGBA", (10, 10), (255, 0, 0, 255))
>>> nine_slice(im, (2, 3, 2, 3), (20, 4)).size
(24, 10)
```

* **Return type:**
  `Image`

### cutan.carve.framing.open_frame(frame, opening)

The frame’s image with its opening cleared, and the moulding’s band widths.

`opening`: `(x0, y0, x1, y1)` in the frame carving’s SOURCE pixels (what it shows
inside, which is not kept).

* **Raises:**
  [**ValueError**](https://docs.python.org/3/builtins/exceptions.html#ValueError) – the opening is not strictly inside the carved frame.
* **Return type:**
  [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[`Image`, [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`int`](https://docs.python.org/3/builtins/functions.html#int), [`int`](https://docs.python.org/3/builtins/functions.html#int), [`int`](https://docs.python.org/3/builtins/functions.html#int), [`int`](https://docs.python.org/3/builtins/functions.html#int)]]
