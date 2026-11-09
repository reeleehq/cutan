"""Whole-or-nothing file writes for the carve and generate steps (cutan#188).

>>> import tempfile, pathlib
>>> from PIL import Image
>>> with tempfile.TemporaryDirectory() as d:
...     p = pathlib.Path(d) / "a.png"
...     save_png(Image.new("RGBA", (2, 2)), p)
...     Image.open(p).size
(2, 2)
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

from dol import atomic_write

__all__ = ["save_png"]


def save_png(image: Any, path: str | Path) -> None:
    """``image`` to ``path`` as PNG, whole or not at all: a killed write keeps the
    previous file, and never leaves half a PNG to be kept."""
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    atomic_write(path, buf.getvalue())
