"""Split a carved prop into moving parts, each with a declared pivot.

A clock's hands come off its face, a camera into tripod, body and lens: each
part is lifted out of a :class:`~cutan.carve.Carving` by a mask, gets a pivot
(the point it turns about), and the base keeps what is left. Where a part
lay *inside* the base (a hand on the face), the base is painted in under it
from the surrounding pixels, so the part can move without leaving a hole;
where it stuck *out* (a lens past the body), the base simply loses it.

Masks and pivots are in the SOURCE image's pixels, like every other
coordinate :mod:`cutan.carve` takes, so a part spec can be written before the
carve runs (the carving's trim decides its own pixels). A mask may also be an
array of the carving's size.

>>> import numpy as np
>>> from cutan.carve import carve
>>> img = np.full((40, 60, 3), 250, np.uint8); img[10:30, 10:50] = (200, 40, 40)
>>> img[18:22, 30:46] = (40, 40, 200)                        # a blue hand on a red face
>>> face = carve(img, point=(20, 20))
>>> split = split_parts(face, {"hand": PartSpec(mask=[(29, 17), (47, 17), (47, 23), (29, 23)],
...                                             pivot=(30, 20))})
>>> hand = split.parts[0]
>>> (hand.origin[0] + hand.pivot[0], hand.origin[1] + hand.pivot[1]) == face.to_part([(30, 20)])[0]
True
>>> tuple(int(v) for v in np.asarray(split.base)[10, 35])   # painted in under the hand, opaque
(200, 40, 40, 255)
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from PIL import Image

from cutan.carve import refine
from cutan.carve._deps import cv2 as _cv2
from cutan.carve.core import Carving, _trim_box
from cutan.carve.mattes import Hint, Matte, MatteLike, Polygon, as_matte

__all__ = ["Part", "PartSet", "PartSpec", "split_parts"]

Point = tuple[float, float]
MaskLike = Sequence[Point] | np.ndarray | MatteLike


@dataclass(frozen=True)
class PartSpec:
    """What to lift off a carving: a ``mask`` and the ``pivot`` it turns about.

    ``mask``: a polygon ``[(x, y), ...]`` in source pixels, a matte called on
    the carving's RGB with the carving's frame as its hint (so a matte's own
    coordinates are source pixels too; ``~FlatColour(colours=[grey],
    connected=False)`` selects the grey strokes), or an array of the carving's
    size (bool or 0..1). ``pivot``: ``(x, y)`` in source pixels. ``grow``:
    carving px the mask is widened by before lifting (anti-aliased strokes).
    ``reach``: keep only the mask's pieces that come within this many source
    px of the pivot (a colour key also matches specks elsewhere: a tick's grey
    edge).
    """

    mask: Any
    pivot: Point
    grow: int = 1
    reach: float | None = None


@dataclass
class Part:
    """One lifted part: its RGBA image, its pivot in that image, where it sits in the carving."""

    name: str
    image: Image.Image
    pivot: Point
    origin: Point
    draw_order: int

    @property
    def anchor(self) -> tuple[float, float]:
        """The pivot as an attachment anchor (0..1 of the image)."""
        return (self.pivot[0] / self.image.width, self.pivot[1] / self.image.height)


@dataclass
class PartSet:
    """A carving split into a base (``None`` when every pixel went to a part) and parts."""

    carving: Carving
    base: Image.Image | None
    parts: list[Part] = field(default_factory=list)


def _mask_of(spec: MaskLike, rgb: np.ndarray, hint: Hint) -> np.ndarray:
    h, w = rgb.shape[:2]
    if isinstance(spec, np.ndarray) and spec.ndim == 2:
        if spec.shape != (h, w):
            raise ValueError(f"a part's mask is {spec.shape}; the carving is {(h, w)}")
        return np.clip(spec.astype(np.float32), 0, 1)
    if isinstance(spec, Matte) or (
        callable(spec) and not isinstance(spec, (list, tuple))
    ):
        return np.clip(np.asarray(spec(rgb, hint), np.float32), 0, 1)
    if isinstance(spec, Mapping):
        return np.clip(np.asarray(as_matte(spec)(rgb, hint), np.float32), 0, 1)
    return Polygon(list(spec))(rgb, hint)


def _within(mask: np.ndarray, point: Point, reach: float) -> np.ndarray:
    """The components of ``mask`` with a pixel within ``reach`` px of ``point``."""
    cv2 = _cv2()
    n, labels = cv2.connectedComponents(mask.astype(np.uint8), connectivity=8)
    h, w = mask.shape
    yy, xx = np.mgrid[:h, :w]
    close = np.hypot(xx - point[0], yy - point[1]) <= reach
    ids = set(np.unique(labels[close & mask]).tolist()) - {0}
    return np.isin(labels, list(ids))


def split_parts(
    carving: Carving,
    parts: Mapping[str, PartSpec | Mapping[str, Any]],
    *,
    paint_out: bool = True,
    inpaint_radius: int = 4,
    pad: int = 2,
) -> PartSet:
    """Lift ``parts`` (``{name: PartSpec}``, in draw order) off ``carving``.

    Each part takes the carving's pixels under its mask. Parts are drawn in
    the order listed, the last on top, and the one drawn on top owns a pixel
    two masks share (a clock's hub cap, listed after the hands, keeps the hub).
    The base keeps the rest, and stays opaque under a part's soft edge (no
    seam at rest); where a part was enclosed by the base, ``paint_out``
    re-paints the base under it (``cv2.inpaint``) so it stays whole when the
    part moves. A part's ``origin`` and ``pivot`` are in the carving's pixels
    (where :func:`~cutan.carve.write_prop` places it).
    """
    cv2 = _cv2()
    rgba = np.asarray(carving.image.convert("RGBA"))
    rgb, alpha = rgba[..., :3], rgba[..., 3].astype(np.float32) / 255.0
    frame = Hint(offset=carving.offset, scale=carving.scale)
    taken = np.zeros(alpha.shape, np.float32)
    out: list[Part] = []
    items = list(parts.items())
    # the part listed last is drawn on top: it owns the pixels it shares, so
    # pixels are handed out from the top of the draw order down
    for order, (name, spec) in reversed(list(enumerate(items, start=1))):
        spec = spec if isinstance(spec, PartSpec) else PartSpec(**spec)
        m = _mask_of(spec.mask, rgb, frame)
        pivot = carving.to_part([spec.pivot])[0]
        if spec.reach is not None:
            m = m * _within(m > refine.SUBJECT, pivot, spec.reach * carving.scale)
        if spec.grow > 0:
            m = cv2.dilate(m, np.ones((2 * spec.grow + 1,) * 2, np.uint8))
        m = np.minimum(m, 1.0 - taken)
        a = alpha * m
        box = _trim_box(a, pad)
        if box is None:
            raise ValueError(
                f"the part {name!r} took no pixels of the carving: check its mask"
            )
        x0, y0, x1, y1 = box
        img = np.dstack([rgb, np.round(a * 255).astype(np.uint8)])[y0:y1, x0:x1]
        px, py = pivot
        out.append(
            Part(
                name,
                Image.fromarray(np.ascontiguousarray(img), "RGBA"),
                pivot=(float(px - x0), float(py - y0)),
                origin=(float(x0), float(y0)),
                draw_order=order,
            )
        )
        taken = np.maximum(taken, m)
    out.reverse()
    lifted = taken > 0.5
    rest = (alpha > refine.SUBJECT) & ~lifted
    base = None
    if rest.any():
        enclosed = refine.fill_holes(rest) & lifted
        # the base stays opaque under a part's soft edge (taken < 1): at rest
        # the two composite to the original instead of leaving a seam
        base_alpha = alpha * (taken < 0.99)
        base_rgb = rgb
        if paint_out and enclosed.any():
            hole = cv2.dilate(enclosed.astype(np.uint8), np.ones((3, 3), np.uint8))
            base_rgb = cv2.inpaint(
                np.ascontiguousarray(rgb), hole * 255, inpaint_radius, cv2.INPAINT_TELEA
            )
            base_alpha = np.where(hole > 0, alpha, base_alpha)
        base = Image.fromarray(
            np.dstack([base_rgb, np.round(base_alpha * 255).astype(np.uint8)]), "RGBA"
        )
    return PartSet(carving=carving, base=base, parts=out)
