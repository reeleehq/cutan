# cutan.carve.refine

Clean a raw matte into a cut-out’s alpha: keep the subject, close it, edge it, de-spill it.

Each step is a function of arrays, so a caller can run any of them alone;
[`cutan.carve.carve()`](cutan.carve.html.md#cutan.carve.carve) runs them in this order:

1. [`keep_components()`](#cutan.carve.refine.keep_components) — keep the part under the hint point (else the
   largest), dropping specks and the stray objects a matte also caught;
2. [`fill_holes()`](#cutan.carve.refine.fill_holes) — a pale face or an eye a matte called background;
3. [`detach_bridges()`](#cutan.carve.refine.detach_bridges) — cut what hangs on the subject by a thin neck (a
   caption’s letters touching a head);
4. [`choke()`](#cutan.carve.refine.choke) and [`feather()`](#cutan.carve.refine.feather) — pull the edge in, then soften it;
5. [`despill()`](#cutan.carve.refine.despill) — re-paint the rim’s colour from the subject’s interior, so
   no backdrop colour is left in the semi-transparent edge.

### Module Attributes

| [`SUBJECT`](#cutan.carve.refine.SUBJECT)   | The alpha above which a pixel counts as the subject's.   |
|------------------------------------------------------------|----------------------------------------------------------|

### Functions

| [`choke`](#cutan.carve.refine.choke)(alpha, px)                              | Pull the matte's edge in by `px` pixels (a smooth, distance-based erosion).        |
|------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------|
| [`despill`](#cutan.carve.refine.despill)(rgb, alpha, rim, \*[, solid])         | Re-paint the edge's colours from the subject's interior; `(rgb, repainted share)`. |
| [`detach_bridges`](#cutan.carve.refine.detach_bridges)(mask, radius, \*[, point])     | Cut away what hangs on the main body by a neck narrower than `2 * radius` px.      |
| [`feather`](#cutan.carve.refine.feather)(alpha, sigma)                         | Soften the edge with a Gaussian of `sigma` px (0 leaves it as it is).              |
| [`fill_holes`](#cutan.carve.refine.fill_holes)(mask)                              | `mask` with every enclosed hole filled.                                            |
| [`keep_components`](#cutan.carve.refine.keep_components)(mask, \*[, point, keep, ...]) | The components of the boolean `mask` to keep.                                      |

### cutan.carve.refine.SUBJECT *: [float](https://docs.python.org/3/builtins/functions.html#float)* *= 0.5*

The alpha above which a pixel counts as the subject’s.

### cutan.carve.refine.choke(alpha, px)

Pull the matte’s edge in by `px` pixels (a smooth, distance-based erosion).

* **Return type:**
  `ndarray`

```pycon
>>> a = np.zeros((9, 9), np.float32); a[1:8, 1:8] = 1
>>> float(choke(a, 2)[1, 4]), float(choke(a, 2)[4, 4])
(0.0, 1.0)
```

### cutan.carve.refine.despill(rgb, alpha, rim, , solid=None)

Re-paint the edge’s colours from the subject’s interior; `(rgb, repainted share)`.

The subject is `solid` (the alpha BEFORE any feathering; default
`alpha`) above [`SUBJECT`](#cutan.carve.refine.SUBJECT). Trusted pixels are those at least
`rim` px inside its edge (a distance, not an alpha: a soft interior is
still interior). Repainted: every other pixel with some alpha — the
anti-aliased band, a neural matte’s fuzzy fringe, what feathering spread
over the backdrop — which is never more than `rim` px plus the fringe
from the edge. Colours flow outward from the trusted pixels one pixel per
pass, each the mean of its known neighbours, never from the backdrop. An
outline stays an outline: it is solid, so its inner part is trusted. The
share is of the subject’s pixels, the quality signal for a de-spill that
repainted real content.

* **Return type:**
  [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[`ndarray`, [`float`](https://docs.python.org/3/builtins/functions.html#float)]

```pycon
>>> rgb = np.zeros((7, 7, 3), np.uint8); rgb[:] = (0, 0, 255)  # a blue backdrop
>>> rgb[1:6, 1:6] = (200, 0, 0); rgb[1, 1:6] = (100, 0, 160)   # a red subject, a spilt top row
>>> a = np.zeros((7, 7), np.float32); a[1:6, 1:6] = 1
>>> out, share = despill(rgb, a, 1)
>>> tuple(int(c) for c in out[1, 3]), round(share, 2)
((200, 0, 0), 0.64)
```

### cutan.carve.refine.detach_bridges(mask, radius, , point=None)

Cut away what hangs on the main body by a neck narrower than `2 * radius` px.

Erodes by `radius`, keeps the eroded component under `point` (else the
largest), grows it back by `radius + 1` inside the original mask. Returns
`(mask, pieces)`: the cleaned mask and how many pieces it lost (connected
parts of what was removed, at least `radius²` px: a caption glyph, and also
a thin part thinner than `2 * radius` px, which erosion cannot tell apart).

* **Return type:**
  [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[`ndarray`, [`int`](https://docs.python.org/3/builtins/functions.html#int)]

```pycon
>>> m = np.zeros((20, 40), bool); m[2:18, 2:18] = True   # a body
>>> m[9:11, 18:24] = True; m[6:14, 24:32] = True          # a glyph on a 2-px neck
>>> out, pieces = detach_bridges(m, 2)
>>> pieces, bool(out[10, 28]), bool(out[10, 10])
(1, False, True)
```

### cutan.carve.refine.feather(alpha, sigma)

Soften the edge with a Gaussian of `sigma` px (0 leaves it as it is).

* **Return type:**
  `ndarray`

### cutan.carve.refine.fill_holes(mask)

`mask` with every enclosed hole filled.

* **Return type:**
  `ndarray`

```pycon
>>> m = np.ones((5, 5), bool); m[2, 2] = False
>>> bool(fill_holes(m)[2, 2])
True
```

### cutan.carve.refine.keep_components(mask, , point=None, keep='point', min_share=0.02, gap=6)

The components of the boolean `mask` to keep.

`keep`: `"point"` keeps the component under `point` (the largest when
the point is off the subject or not given) and the pieces lying within
`gap` px of it that are at least `min_share` of its area (a hand or a
hat a matte separated by a sliver); `"largest"` keeps the largest only;
`"all"` keeps everything.

* **Return type:**
  `ndarray`

```pycon
>>> m = np.zeros((10, 30), bool); m[1:9, 1:9] = True; m[4:6, 25:27] = True
>>> int(keep_components(m, keep="largest").sum()), int(keep_components(m, keep="all").sum())
(64, 68)
>>> int(keep_components(m, point=(25, 4)).sum())        # the small piece, alone
4
>>> m[4:6, 11:13] = True                                 # a piece 2 px from the body
>>> int(keep_components(m, point=(4, 4), min_share=0.05).sum())
68
```
