# cutan.characters.silhouette

Silhouette rendering and comparison for the silhouette test.

The silhouette test (Disney/AnimSchool, see research §6.4) is a quick
read-test for character distinctiveness: fill the character with solid
black, and if you can still tell who’s who, the design is strong.

This module renders an SVG to a binary silhouette PNG (Playwright is the
underlying rasterizer — already a project dep) and computes an IoU score
between two silhouettes after centering and scaling them to a common
canvas. A score near 1.0 means the silhouettes are nearly identical
(BAD — the characters are indistinguishable). A score below ~0.5 is
typically the sweet spot for visually-distinct characters.

```pycon
>>> from cutan.characters import generate_default_mouths
>>> import tempfile, pathlib
>>> # Skip the doctest body — it requires Playwright with Chromium installed.
```

### Module Attributes

| [`DFLT_SILHOUETTE_SIZE`](#cutan.characters.silhouette.DFLT_SILHOUETTE_SIZE)   | Square frame the stage draws each figure in, and the output size, in px.   |
|-------------------------------------------------------------------------|----------------------------------------------------------------------------|
| [`SILHOUETTE_THRESHOLD`](#cutan.characters.silhouette.SILHOUETTE_THRESHOLD)   | Luminance below which a pixel of the tinted render is the figure.          |

### Functions

| [`compare_silhouettes`](#cutan.characters.silhouette.compare_silhouettes)(a, b, \*[, size])             | Return IoU between two silhouette PNGs (0..1; lower = more distinct).   |
|----------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------|
| [`render_character_silhouettes`](#cutan.characters.silhouette.render_character_silhouettes)(char_dirs, ...)      | Silhouettes of characters AS THE STAGE DRAWS THEM: `{name: png}`.       |
| [`render_silhouette`](#cutan.characters.silhouette.render_silhouette)(svg_source, out_png, \*[, ...]) | Render an SVG to a binary silhouette PNG (black on white).              |

### cutan.characters.silhouette.DFLT_SILHOUETTE_SIZE *: [int](https://docs.python.org/3/builtins/functions.html#int)* *= 512*

Square frame the stage draws each figure in, and the output size, in px.

### cutan.characters.silhouette.SILHOUETTE_THRESHOLD *: [int](https://docs.python.org/3/builtins/functions.html#int)* *= 128*

Luminance below which a pixel of the tinted render is the figure.

### cutan.characters.silhouette.compare_silhouettes(a, b, , size=(256, 256))

Return IoU between two silhouette PNGs (0..1; lower = more distinct).

Both images are resized to `size`, converted to grayscale, thresholded
at the midpoint, and the intersection-over-union of the foreground (dark)
pixels is computed.

* **Return type:**
  [`float`](https://docs.python.org/3/builtins/functions.html#float)

```pycon
>>> # Two identical silhouettes → IoU = 1.0; two empty → 0.0 (no overlap).
>>> # Tested via test suite, not doctest, since it requires Playwright.
```

### cutan.characters.silhouette.render_character_silhouettes(char_dirs, out_dir, , size=512)

Silhouettes of characters AS THE STAGE DRAWS THEM: `{name: png}`.

Each character (a folder holding `character.json`) is rendered by the
cut-out renderer in a throwaway project, alone in the frame, its root
tinted black over a white backdrop, so the silhouette is the figure a
viewer sees: its build, head scale, hat and pose (an#272). The old path
rasterised the factory’s composite `<name>.svg`, which draws none of
those, so two different figures compared as identical. One render for all,
one shot each, every figure placed the same way, so IoUs compare shapes.

Needs the stage renderer (Playwright Chromium) and ffmpeg. Writes only
under `out_dir`, never into a character’s folder.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)]

### cutan.characters.silhouette.render_silhouette(svg_source, out_png, , size=(256, 256), background='#ffffff')

Render an SVG to a binary silhouette PNG (black on white).

Uses Playwright/Chromium to rasterize, then PIL to threshold by alpha
or luminance. Returns the output path.

The output is RGB; the silhouette is filled with black (#000) and the
background with the given color.

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)
