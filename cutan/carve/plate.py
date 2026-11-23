"""A clean backdrop plate from frames a subject moves in front of.

:func:`~cutan.carve.carve` mattes a subject *out of* a frame; :func:`plate` recovers the
*backdrop behind* one: a stage curtain someone stands in front of in every shot, a wall a
character walks past. It takes frames of the same view and:

1. **gates** them on alignment: with ``align_box`` (a region of the backdrop nothing crosses),
   a frame whose region differs from the reference frame's by more than ``align_tolerance``
   (mean absolute difference, 0..255) is rejected: the camera moved;
2. takes the **per-pixel median** over the frames where ``keep`` says the pixel is backdrop
   (a matte strategy or an ``(rgb, hint) -> alpha`` rule, e.g. "red-dominant"), with what it
   rejects grown by ``grow`` px (outlines and anti-aliased edges). Without ``keep``, every
   pixel of every frame votes, which is enough when the subject moves more than it stays;
3. **fills** what no frame shows: ``"inpaint"`` (OpenCV's Telea inpainting, the default),
   ``"columns"`` (each hole continued down its column between the pixels seen above and below
   it: vertical folds, stripes), a callable ``(plate, hole) -> rgb``, or ``None`` (left
   transparent).

The result is an ordinary :class:`~cutan.carve.Carving` (write it with
:func:`~cutan.carve.write_prop`) whose ``quality`` is a :class:`PlateQuality`: the frames used
and rejected and the **share of the plate that was filled** (derived, not seen), which its
provenance records. ``meta["_filled"]`` is the filled pixels' mask (in memory only), and
``meta["filled_box"]`` its bounding box in the plate's pixels (``None``: nothing filled).

>>> import numpy as np
>>> back = np.zeros((20, 30, 3), np.uint8); back[:, ::2] = (200, 30, 30)    # a striped wall
>>> frames = []
>>> for k in range(5):                                                      # a square walks past
...     f = back.copy(); f[5:15, 4 * k:4 * k + 8] = (0, 90, 200); frames.append(f)
>>> p = plate(frames)
>>> bool((np.asarray(p.image)[..., :3] == back).all()), p.quality.filled_share
(True, 0.0)
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, Union

import numpy as np
from PIL import Image

from cutan.carve._deps import cv2 as _cv2
from cutan.carve.core import Box, CarveQuality, Carving, ImageLike, load_rgb
from cutan.carve.mattes import Hint, as_matte

__all__ = ["FILLS", "PlateQuality", "plate"]

Fill = Union[str, Callable[[np.ndarray, np.ndarray], np.ndarray], None]
#: The named fills.
FILLS = ("inpaint", "columns")
#: OpenCV inpainting radius, in px.
INPAINT_RADIUS = 3
#: Above this share of filled (unseen) pixels, a plate is flagged.
FILLED_SHARE_WARN = 0.05


@dataclass(frozen=True)
class PlateQuality(CarveQuality):
    """A plate's signals: a :class:`~cutan.carve.CarveQuality` (its matte signals are moot
    for a plate: the whole region is kept) plus how it was made. ``frames_used``: the
    frames that voted; ``frames_rejected``: the indices the alignment gate turned away;
    ``filled_share``: the share of the plate no frame showed, filled (derived)."""

    frames_used: int = 0
    frames_rejected: tuple[int, ...] = field(default_factory=tuple)
    filled_share: float = 0.0
    fill: str | None = None

    def warnings(self) -> list[str]:
        out = []
        if self.frames_used < 3:
            out.append(
                f"a median of {self.frames_used} frame(s) cannot outvote a subject: "
                "give more frames, or a keep= rule"
            )
        if self.filled_share > FILLED_SHARE_WARN:
            how = f"by {self.fill}" if self.fill else "left transparent"
            out.append(
                f"{self.filled_share:.1%} of the plate no frame shows ({how}): derived, "
                "not carved"
            )
        if self.frames_rejected:
            out.append(
                f"{len(self.frames_rejected)} frame(s) failed the alignment gate (the "
                f"camera moved?): {list(self.frames_rejected)}"
            )
        return out

    def as_dict(self) -> dict[str, Any]:
        return {
            **super().as_dict(),
            "frames_used": self.frames_used,
            "frames_rejected": list(self.frames_rejected),
            "filled_share": round(self.filled_share, 4),
            "fill": self.fill,
        }


def _aligned(frames: list[np.ndarray], box: Box | None, reference: int, tol: float):
    """Indices of the frames whose ``box`` matches the reference frame's, and the others."""
    if box is None:
        return list(range(len(frames))), []
    x0, y0, x1, y1 = (int(round(v)) for v in box)
    ref = frames[reference][y0:y1, x0:x1].astype(np.int16)
    if ref.size == 0:
        raise ValueError(
            f"align_box {box} is empty in a {frames[0].shape[1]}x{frames[0].shape[0]} frame"
        )
    keep, reject = [], []
    for i, f in enumerate(frames):
        diff = np.abs(f[y0:y1, x0:x1].astype(np.int16) - ref).mean()
        (keep if diff <= tol else reject).append(i)
    return keep, reject


def _columns(plate_: np.ndarray, hole: np.ndarray) -> np.ndarray:
    """Each column's holes, linearly between the pixels seen above and below them (the
    nearest seen one, where only one side is)."""
    out = plate_.copy()
    rows = np.arange(plate_.shape[0])
    for x in np.nonzero(hole.any(axis=0))[0]:
        seen = ~hole[:, x]
        if not seen.any():
            continue
        for c in range(plate_.shape[2]):
            out[hole[:, x], x, c] = np.interp(
                rows[hole[:, x]], rows[seen], plate_[seen, x, c]
            )
    return out


def _inpaint(plate_: np.ndarray, hole: np.ndarray) -> np.ndarray:
    cv2 = _cv2()
    img = np.clip(np.nan_to_num(plate_), 0, 255).astype(np.uint8)
    return cv2.inpaint(
        img, hole.astype(np.uint8) * 255, INPAINT_RADIUS, cv2.INPAINT_TELEA
    )


def _box_of(mask: np.ndarray) -> list[int] | None:
    """``[x0, y0, x1, y1]`` around ``mask``'s true pixels, or ``None``."""
    ys, xs = np.nonzero(mask)
    if not len(ys):
        return None
    return [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]


def _fill_name(fill: Fill) -> str | None:
    if fill is None or isinstance(fill, str):
        return fill
    return getattr(fill, "__name__", repr(fill))


def plate(
    frames: Sequence[ImageLike],
    *,
    keep: Any = None,
    align_box: Box | None = None,
    align_tolerance: float = 9.0,
    reference: int = 0,
    grow: int = 7,
    fill: Fill = "inpaint",
    crop: Box | None = None,
    point: tuple[float, float] | None = None,
    min_frames: int = 1,
    source: Any = None,
) -> Carving:
    """The backdrop behind whatever moves in front of it in ``frames`` (see the module docstring).

    Args:
        frames: images of one view (paths, arrays or PIL images), all the same size.
        keep: where a frame shows the backdrop: a matte (a strategy's name, a recipe, a
            :class:`~cutan.carve.Matte`) or an ``(rgb, hint) -> alpha`` rule; ``None``, everywhere.
        align_box: a region of the backdrop nothing crosses, in source px, checked against
            frame ``reference``; ``None``: no gate.
        align_tolerance: the largest mean absolute difference (0..255) a frame's region may have.
        grow: px by which what ``keep`` rejects is widened (outlines, anti-aliasing).
        fill: ``"inpaint"``, ``"columns"``, a callable ``(plate, hole) -> rgb`` (``plate`` holds
            NaN in the hole), or ``None`` to leave the unseen pixels transparent.
        crop: the plate's region, in source px (default: the whole frame).
        point: the plate's anchor, in source px (default: the crop's centre).
        min_frames: refuse a plate from fewer frames than this (after the gate).
        source: the frames' provenance (:func:`~cutan.carve.frame_source`).

    Raises:
        ValueError: frames of different sizes, an unknown fill, or too few frames.
    """
    if not frames:
        raise ValueError("plate() needs at least one frame")
    rgbs = [load_rgb(f) for f in frames]
    shape = rgbs[0].shape
    if any(r.shape != shape for r in rgbs):
        raise ValueError(f"frames differ in size: {sorted({r.shape for r in rgbs})}")
    if isinstance(fill, str) and fill not in FILLS:
        raise ValueError(f"unknown fill {fill!r}; one of {FILLS}, a callable, or None")
    used, rejected = _aligned(rgbs, align_box, reference, align_tolerance)
    if len(used) < max(1, min_frames):
        raise ValueError(
            f"{len(used)} frame(s) passed the alignment gate (min_frames={min_frames}); "
            f"rejected: {rejected}"
        )
    h, w = shape[:2]
    x0, y0, x1, y1 = (0, 0, w, h) if crop is None else (int(round(v)) for v in crop)
    stack = np.stack([rgbs[i][y0:y1, x0:x1] for i in used]).astype(np.float32)

    matte = as_matte(keep) if keep is not None else None
    if matte is not None:
        cv2 = _cv2()
        kernel = np.ones((2 * grow + 1, 2 * grow + 1), np.uint8) if grow > 0 else None
        valid = []
        for frame in stack.astype(np.uint8):
            ok = np.asarray(matte(frame, Hint()), np.float32) > 0.5
            if kernel is not None:
                ok = ~cv2.dilate((~ok).astype(np.uint8), kernel).astype(bool)
            valid.append(ok)
        votes = np.where(np.stack(valid)[..., None], stack, np.nan)
    else:
        votes = stack
    with np.errstate(all="ignore"):
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN pixels: the hole
            med = np.nanmedian(votes, axis=0)
    hole = np.isnan(med[..., 0])

    alpha = np.full(hole.shape, 255, np.uint8)
    if hole.any():
        if fill is None:
            med = np.nan_to_num(med)
            alpha[hole] = 0
        elif fill == "inpaint":
            med = _inpaint(med, hole)
        elif fill == "columns":
            med = _columns(med, hole)
        else:
            med = np.asarray(fill(med, hole), np.float32)
    rgb = np.clip(np.rint(np.nan_to_num(med)), 0, 255).astype(np.uint8)
    image = Image.fromarray(np.dstack([rgb, alpha]), "RGBA")

    filled_share = float(hole.mean())
    quality = PlateQuality(
        coverage=1.0 - filled_share if fill is None else 1.0,
        rim_backdrop_share=0.0,
        repainted_share=0.0,
        soft_interior_share=0.0,
        detached_pieces=0,
        attached_pieces=0,
        touches_edge=False,
        frames_used=len(used),
        frames_rejected=tuple(rejected),
        filled_share=filled_share,
        fill=_fill_name(fill) if hole.any() else None,
    )
    px, py = point if point is not None else ((x0 + x1) / 2, (y0 + y1) / 2)
    return Carving(
        image=image,
        anchor=((px - x0) / (x1 - x0), (py - y0) / (y1 - y0)),
        offset=(float(x0), float(y0)),
        scale=1.0,
        quality=quality,
        recipe={
            "plate": {
                "frames": len(rgbs),
                "keep": matte.recipe() if matte is not None else None,
                "align_box": list(align_box) if align_box is not None else None,
                "align_tolerance": align_tolerance,
                "reference": reference,
                "grow": grow,
                "fill": _fill_name(fill),
                "crop": [x0, y0, x1, y1],
            }
        },
        source=source,
        meta={
            "region_in_source": [x0, y0, x1, y1],
            "source_to_part": [[1.0, 0.0, -float(x0)], [0.0, 1.0, -float(y0)]],
            # the unseen pixels' box (written) and mask (in memory only: "_")
            "filled_box": _box_of(hole),
            "_filled": hole,
        },
        mode="plate",
    )
