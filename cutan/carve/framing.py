"""A picture in a carved frame, the frame sized to the picture: one prop, both sources kept.

A wall of framed pictures (end cards, a frame from a video, a typeset card) wants one carved
picture frame reused around pictures of every aspect. :func:`framed` does it:

1. the frame's **opening** (a box in the frame carving's source pixels, like every coordinate
   :mod:`cutan.carve` takes) is cut out, which leaves four bands of moulding around it;
2. the frame is sized to the picture by **9-slice**: its four corners kept as carved, its top
   and bottom bands stretched across, its sides down (:func:`nine_slice`);
3. picture and frame become **two parts** of one :class:`~cutan.carve.PartSet` (picture under
   frame), each with its own ``source``: :func:`~cutan.carve.write_prop` writes the picture's on
   its attachment, so ``an credits`` lists both (the frame's is the prop's own, with the
   9-slice recorded in its recipe);
4. an optional :class:`DropShadow` is a third, lowest part, drawn from the frame's own alpha
   (derived, credited to the frame).

>>> import numpy as np
>>> from cutan.carve import carve
>>> from cutan.carve.mattes import Polygon
>>> art = np.full((60, 80, 3), 255, np.uint8)
>>> art[10:50, 10:70] = (200, 160, 40)                        # a gold frame ...
>>> art[20:40, 20:60] = (90, 90, 90)                          # ... around an old picture
>>> frame = carve(art, matte=Polygon([(10, 10), (70, 10), (70, 50), (10, 50)]), point=(40, 30),
...               keep="all", feather=0, despill=0, pad=0)
>>> pic = np.zeros((100, 30, 3), np.uint8)                    # a tall new picture
>>> out = framed(pic, frame, opening=(20, 20, 60, 40), ours=True)
>>> [p.name for p in out.parts], out.carving.size
(['picture', 'frame'], (51, 121))
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Union

import numpy as np
from PIL import Image, ImageFilter

from cutan.carve.core import Box, CarveQuality, Carving
from cutan.carve.parts import Part, PartSet

__all__ = ["DropShadow", "framed", "nine_slice", "open_frame"]

#: Left, top, right, bottom widths of a frame's moulding around its opening, in its pixels.
Bands = tuple[int, int, int, int]
PictureLike = Union[Carving, Image.Image, np.ndarray]


@dataclass(frozen=True)
class DropShadow:
    """A soft shadow of the frame on the wall: its alpha, offset, blurred, at ``opacity``."""

    offset: tuple[int, int] = (10, 10)
    blur: float = 4.0
    opacity: float = 0.35
    color: tuple[int, int, int] = (20, 24, 28)


def open_frame(frame: Carving, opening: Box) -> tuple[Image.Image, Bands]:
    """The frame's image with its opening cleared, and the moulding's band widths.

    ``opening``: ``(x0, y0, x1, y1)`` in the frame carving's SOURCE pixels (what it shows
    inside, which is not kept).

    Raises:
        ValueError: the opening is not strictly inside the carved frame.
    """
    (x0, y0), (x1, y1) = frame.to_part([opening[:2], opening[2:]])
    x0, y0, x1, y1 = (round(v) for v in (x0, y0, x1, y1))
    w, h = frame.size
    if not (0 < x0 < x1 < w and 0 < y0 < y1 < h):
        raise ValueError(
            f"the opening {tuple(opening)} (source px) is {(x0, y0, x1, y1)} in the "
            f"{w}x{h} carved frame: it must lie strictly inside it, with moulding all round"
        )
    img = np.asarray(frame.image.convert("RGBA")).copy()
    img[y0:y1, x0:x1, 3] = 0
    return Image.fromarray(img), (x0, y0, w - x1, h - y1)


def nine_slice(image: Image.Image, bands: Bands, inner: tuple[int, int]) -> Image.Image:
    """``image`` resized by 9-slice so the part inside ``bands`` is ``inner`` pixels: the corners
    as they are, the edges stretched along their length, the centre to ``inner``.

    >>> im = Image.new("RGBA", (10, 10), (255, 0, 0, 255))
    >>> nine_slice(im, (2, 3, 2, 3), (20, 4)).size
    (24, 10)
    """
    L, T, R, B = bands
    fw, fh = image.size
    iw, ih = inner
    if iw < 1 or ih < 1:
        raise ValueError(f"the inside must be at least 1x1 pixel, not {inner}")
    W, H = iw + L + R, ih + T + B
    xs_src, xs_dst = (0, L, fw - R, fw), (0, L, W - R, W)
    ys_src, ys_dst = (0, T, fh - B, fh), (0, T, H - B, H)
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    src = image.convert("RGBA")
    for i in range(3):
        for j in range(3):
            sb = (xs_src[j], ys_src[i], xs_src[j + 1], ys_src[i + 1])
            db = (xs_dst[j], ys_dst[i], xs_dst[j + 1], ys_dst[i + 1])
            if sb[2] <= sb[0] or sb[3] <= sb[1] or db[2] <= db[0] or db[3] <= db[1]:
                continue
            piece = src.crop(sb)
            size = (db[2] - db[0], db[3] - db[1])
            if piece.size != size:
                piece = piece.resize(size, Image.LANCZOS)
            out.alpha_composite(piece, db[:2])
    return out


def _picture(picture: PictureLike, source, ours: bool) -> tuple[Image.Image, Any]:
    """The picture's RGBA image and its provenance (a carving's own, else ``source``)."""
    if isinstance(picture, Carving):
        return picture.image.convert("RGBA"), source or picture.provenance()
    img = (
        Image.fromarray(np.asarray(picture))
        if isinstance(picture, np.ndarray)
        else picture
    )
    if source is None and not ours:
        raise ValueError(
            "the picture has no provenance, and a part with no source reads as art you made: "
            "pass source=frame_source(url, license=...) or ours=True if the pixels are yours"
        )
    return img.convert("RGBA"), source


def framed(
    picture: PictureLike,
    frame: Carving,
    *,
    opening: Box,
    source: Any = None,
    ours: bool = False,
    shadow: DropShadow | None = None,
    picture_part: str = "picture",
    frame_part: str = "frame",
    shadow_part: str = "shadow",
) -> PartSet:
    """``picture`` inside ``frame``, the frame 9-sliced to the picture's size, as a part set.

    Args:
        picture: a :class:`~cutan.carve.Carving` (its provenance is the picture's), or an image
            (``PIL.Image`` or array) with ``source=`` (or ``ours=True``).
        frame: the carved frame, with the picture it held still inside.
        opening: the frame's opening, in the frame carving's source pixels.
        source: the picture's provenance (overrides a carving's).
        ours: the picture's pixels are the caller's own (a typeset card).
        shadow: a :class:`DropShadow` part under the frame, or ``None``.

    The set's carving is the whole composite (the parts in place), with the frame's source as
    the prop's own: write it with :func:`~cutan.carve.write_prop`, whose ``landmarks`` are then
    in the composite's pixels (a hook at ``(width / 2, 0)``).
    """
    if frame.source is None and not ours:
        raise ValueError("the frame carving has no source: carve it with source=...")
    pic, pic_source = _picture(picture, source, ours)
    frame_img, bands = open_frame(frame, opening)
    sized = nine_slice(frame_img, bands, pic.size)
    L, T, _, _ = bands
    W, H = sized.size
    parts: list[tuple[str, Image.Image, tuple[int, int], Any]] = []
    margin = (0, 0)
    if shadow is not None:
        pad = int(np.ceil(3 * shadow.blur))
        sh = Image.new("RGBA", (W + 2 * pad, H + 2 * pad), (*shadow.color, 0))
        alpha = Image.new("L", sh.size, 0)
        alpha.paste(
            sized.getchannel("A").point(lambda v: round(v * shadow.opacity)), (pad, pad)
        )
        sh.putalpha(alpha.filter(ImageFilter.GaussianBlur(shadow.blur)))
        ox, oy = shadow.offset[0] - pad, shadow.offset[1] - pad
        margin = (max(0, -ox), max(0, -oy))
        parts.append((shadow_part, sh, (ox, oy), None))  # the prop's own source
    parts.append((picture_part, pic, (L, T), pic_source))
    parts.append(
        (frame_part, sized, (0, 0), None)
    )  # the prop's own source (the frame's)

    mx, my = margin
    cw = max(mx + x + im.width for _, im, (x, _y), _s in parts)
    ch = max(my + y + im.height for _, im, (_x, y), _s in parts)
    composite = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    out: list[Part] = []
    for order, (name, im, (x, y), src) in enumerate(parts, start=1):
        origin = (x + mx, y + my)
        composite.alpha_composite(im, origin)
        out.append(
            Part(
                name=name,
                image=im,
                pivot=(im.width / 2, im.height / 2),
                origin=origin,
                draw_order=order,
                source=src,
            )
        )
    frame_centre = (mx + W / 2, my + H / 2)
    carving = Carving(
        image=composite,
        anchor=(frame_centre[0] / cw, frame_centre[1] / ch),
        offset=(0.0, 0.0),
        scale=1.0,
        quality=frame.quality if frame.quality is not None else CarveQuality(),
        recipe={
            "framed": {
                "opening": [float(v) for v in opening],
                "picture_size": list(pic.size),
                "bands": list(bands),
                "shadow": asdict(shadow) if shadow else None,
                "frame_recipe": frame.recipe,
            }
        },
        source=frame.source,
        meta={
            "derived": "a picture in a carved frame, the frame sized by 9-slice "
            "(corners as carved, edges stretched)",
            "opening_in_part": [
                mx + L,
                my + T,
                mx + L + pic.width,
                my + T + pic.height,
            ],
        },
    )
    return PartSet(carving=carving, base=None, parts=out)
