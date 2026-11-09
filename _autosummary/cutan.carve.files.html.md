# cutan.carve.files

Whole-or-nothing file writes for the carve and generate steps (cutan#188).

```pycon
>>> import tempfile, pathlib
>>> from PIL import Image
>>> with tempfile.TemporaryDirectory() as d:
...     p = pathlib.Path(d) / "a.png"
...     save_png(Image.new("RGBA", (2, 2)), p)
...     Image.open(p).size
(2, 2)
```

### Functions

| [`save_png`](#cutan.carve.files.save_png)(image, path)   | `image` to `path` as PNG, whole or not at all: a killed write keeps the previous file, and never leaves half a PNG to be kept.   |
|--------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------|

### cutan.carve.files.save_png(image, path)

`image` to `path` as PNG, whole or not at all: a killed write keeps the
previous file, and never leaves half a PNG to be kept.

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)
