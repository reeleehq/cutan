"""The carve pipeline: an image (or a video frame) in, a matted, cleaned, provenance-carrying part out.

:func:`carve` runs crop → (upscale) → matte → keep → fill holes → detach
bridges → choke → feather → de-spill → trim, and returns a :class:`Carving`:
the RGBA part, where it came from in the source, its anchor, its quality
signals, and the recipe that cut it (recorded with its provenance).
:func:`carve_head` is the same pipeline with a neck cut and the head
normalised onto a fixed canvas (:mod:`cutan.carve.head`).
"""

from __future__ import annotations

import io
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from an.ir.assets import AssetSource
from cutan.carve import refine
from cutan.carve._deps import cv2 as _cv2
from cutan.carve.head import (
    HEAD_CANVAS,
    HEAD_CENTRE,
    HEAD_FACE_H,
    NECK_SOFT,
    Face,
    FaceLocator,
    InsightFaceLocator,
    neck_cut,
    pick_face,
)
from cutan.carve.mattes import Hint, MatteLike, as_matte

__all__ = [
    "CarveQuality",
    "Carving",
    "ImageLike",
    "carve",
    "carve_head",
    "grab_frame",
    "load_rgb",
]

ImageLike = str | Path | Image.Image | np.ndarray
Box = tuple[float, float, float, float]

#: The alpha below which a pixel is empty (trim, bounding boxes, rim tests).
_EMPTY = 8 / 255


@dataclass(frozen=True)
class CarveQuality:
    """Signals worth reading before a part is used (cutan#10).

    ``coverage``: the subject's share of the carved region (near 0 or 1 means
    the matte took nothing or everything). ``rim_backdrop_share``: the share
    of the rim pixels (partly transparent edge) whose colour is still close to
    the backdrop's — a halo de-spill should remove. ``detached_pieces``: how
    many sizeable pieces were hanging on the subject by a thin neck (a
    caption's letters touching a head; cut off by ``detach``, or still
    attached when ``detach`` was 0 — see ``attached_pieces``).
    ``attached_pieces``: thin-necked pieces still attached in the result.
    ``touches_edge``: the subject runs into the carved region's border, so it
    was probably cut off by the crop.
    """

    coverage: float
    rim_backdrop_share: float
    detached_pieces: int
    attached_pieces: int
    touches_edge: bool

    def warnings(self) -> list[str]:
        """The signals that look wrong, in words."""
        out = []
        if self.coverage < 0.02:
            out.append(
                f"the matte kept almost nothing ({self.coverage:.1%} of the region)"
            )
        if self.coverage > 0.97:
            out.append(
                f"the matte kept almost everything ({self.coverage:.1%}): no backdrop found"
            )
        if self.rim_backdrop_share > 0.25:
            out.append(
                f"{self.rim_backdrop_share:.0%} of the rim is backdrop-coloured: raise despill or choke"
            )
        if self.attached_pieces:
            out.append(
                f"{self.attached_pieces} piece(s) hang on the subject by a thin neck "
                "(caption glyphs?): pass detach=<px>"
            )
        if self.touches_edge:
            out.append("the subject touches the crop's edge: widen the crop")
        return out

    def as_dict(self) -> dict[str, Any]:
        return {
            "coverage": round(self.coverage, 4),
            "rim_backdrop_share": round(self.rim_backdrop_share, 4),
            "detached_pieces": self.detached_pieces,
            "attached_pieces": self.attached_pieces,
            "touches_edge": self.touches_edge,
        }


@dataclass
class Carving:
    """A carved part.

    ``image``: the RGBA part. ``anchor``: its origin as ``(u, v)`` in 0..1 of
    the image (Pixi's convention, an ``Attachment.anchor``): the hint point for
    a plain carve, the face centre for a head. ``to_part`` maps a source pixel
    into the part's pixels (``part = (source - offset) * scale``).
    ``source`` is the provenance, ``recipe`` how it was cut, ``quality`` the
    signals, ``meta`` mode-specific facts (a head's face box on its canvas).
    """

    image: Image.Image
    anchor: tuple[float, float]
    offset: tuple[float, float]
    scale: float
    quality: CarveQuality
    recipe: dict[str, Any]
    source: AssetSource | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def size(self) -> tuple[int, int]:
        return self.image.size

    @property
    def alpha(self) -> np.ndarray:
        """The alpha channel as floats in 0..1."""
        return np.asarray(self.image.getchannel("A"), np.float32) / 255.0

    def to_part(
        self, points: Sequence[tuple[float, float]]
    ) -> list[tuple[float, float]]:
        """Source pixels to this part's pixels."""
        ox, oy = self.offset
        return [((x - ox) * self.scale, (y - oy) * self.scale) for x, y in points]

    def provenance(self) -> AssetSource | None:
        """The source with the recipe and the quality recorded in its ``extra``."""
        if self.source is None:
            return None
        extra = dict(self.source.extra or {})
        extra["carve"] = {
            **self.recipe,
            "quality": self.quality.as_dict(),
            "region_in_source": list(self.meta.get("region_in_source", [])) or None,
        }
        return self.source.model_copy(update={"extra": extra})


# ---------------------------------------------------------------------------
# inputs


def load_rgb(image: ImageLike) -> np.ndarray:
    """An ``HxWx3`` ``uint8`` RGB array from a path, a PIL image or an array.

    >>> load_rgb(np.zeros((4, 5, 4), np.uint8)).shape
    (4, 5, 3)
    """
    if isinstance(image, (str, Path)):
        with Image.open(image) as im:
            return np.asarray(im.convert("RGB")).copy()
    if isinstance(image, Image.Image):
        return np.asarray(image.convert("RGB")).copy()
    arr = np.asarray(image)
    if arr.ndim == 2:
        arr = np.repeat(arr[..., None], 3, axis=2)
    if arr.ndim != 3 or arr.shape[2] not in (3, 4):
        raise ValueError(f"an image is HxWx3 or HxWx4, not {arr.shape}")
    if arr.dtype != np.uint8:
        raise ValueError(f"an image array is uint8, not {arr.dtype}")
    return np.ascontiguousarray(arr[..., :3])


def grab_frame(video: str | Path, t: float, *, ffmpeg: str = "ffmpeg") -> np.ndarray:
    """The frame of ``video`` at ``t`` seconds, as RGB (needs the ``ffmpeg`` binary)."""
    cmd = [
        ffmpeg,
        "-v",
        "error",
        "-ss",
        f"{t:.3f}",
        "-i",
        str(video),
        "-frames:v",
        "1",
        "-f",
        "image2pipe",
        "-vcodec",
        "png",
        "-",
    ]
    try:
        out = subprocess.run(cmd, check=True, capture_output=True).stdout
    except FileNotFoundError as e:
        raise RuntimeError(
            "grab_frame needs ffmpeg on the PATH (https://ffmpeg.org/download.html)"
        ) from e
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"ffmpeg could not read {video} at {t} s: {e.stderr.decode(errors='replace').strip()}"
        ) from e
    if not out:
        raise RuntimeError(f"no frame in {video} at {t} s (past its end?)")
    return load_rgb(Image.open(io.BytesIO(out)))


# ---------------------------------------------------------------------------
# the pipeline


def _clip_box(box: Box, w: int, h: int) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = box
    x0, y0 = max(int(np.floor(x0)), 0), max(int(np.floor(y0)), 0)
    x1, y1 = min(int(np.ceil(x1)), w), min(int(np.ceil(y1)), h)
    if x1 - x0 < 2 or y1 - y0 < 2:
        raise ValueError(f"the region {box} is empty in a {w}x{h} image")
    return x0, y0, x1, y1


def _resize(arr: np.ndarray, size: tuple[int, int], *, up: bool) -> np.ndarray:
    cv2 = _cv2()
    return cv2.resize(
        arr, size, interpolation=cv2.INTER_LANCZOS4 if up else cv2.INTER_AREA
    )


def _quality(
    rgb: np.ndarray,
    alpha: np.ndarray,
    raw: np.ndarray,
    *,
    detached: int,
    neck_px: int,
    point: tuple[float, float] | None,
) -> CarveQuality:
    subject = alpha > refine.SUBJECT
    coverage = float(subject.mean())
    # the backdrop's colour: the median of what the matte called backdrop
    back = raw < 0.05
    rim = (alpha > 0.05) & (alpha < 0.95)
    rim_share = 0.0
    if back.sum() >= 16 and rim.any():
        bg = np.median(rgb[back], axis=0)
        near = np.abs(rgb[rim].astype(np.float32) - bg).max(axis=1) < 24
        rim_share = float(near.mean())
    attached = 0
    if neck_px > 0 and subject.any():
        _, attached = refine.detach_bridges(subject, neck_px, point=point)
    edge = np.concatenate([subject[0], subject[-1], subject[:, 0], subject[:, -1]])
    return CarveQuality(
        coverage=coverage,
        rim_backdrop_share=rim_share,
        detached_pieces=detached,
        attached_pieces=attached,
        touches_edge=bool(edge.mean() > 0.02),
    )


@dataclass
class _Cut:
    """The carve's working state, in the (cropped, upscaled) region's pixels."""

    rgb: np.ndarray
    raw: np.ndarray
    alpha: np.ndarray
    hint: Hint
    region: tuple[int, int, int, int]
    detached: int
    recipe: dict[str, Any]


def _cut(
    rgb: np.ndarray,
    *,
    matte: str | MatteLike,
    crop: Box | None,
    box: Box | None,
    point: tuple[float, float] | None,
    upscale: float,
    keep: str,
    holes: bool,
    detach: int,
    gate: Any = None,
) -> _Cut:
    h, w = rgb.shape[:2]
    region = _clip_box(crop, w, h) if crop is not None else (0, 0, w, h)
    x0, y0, x1, y1 = region
    sub = rgb[y0:y1, x0:x1]
    if upscale != 1.0:
        size = (max(1, round((x1 - x0) * upscale)), max(1, round((y1 - y0) * upscale)))
        sub = _resize(sub, size, up=upscale > 1)
    s = sub.shape[1] / (x1 - x0)
    hint = Hint(offset=(float(x0), float(y0)), scale=s)
    hint = replace(
        hint,
        box=tuple(np.ravel(hint.to_local([box[:2], box[2:]])))
        if box is not None
        else None,
        point=hint.to_local([point])[0] if point is not None else None,
    )
    m = as_matte(matte)
    raw = m(sub, hint)
    raw = np.clip(np.asarray(raw, np.float32), 0, 1)
    if raw.shape != sub.shape[:2]:
        raise ValueError(
            f"the matte returned {raw.shape}; the region is {sub.shape[:2]}"
        )
    if gate is not None:
        raw = raw * gate(sub.shape[:2], hint)
    mask = refine.keep_components(raw > refine.SUBJECT, point=hint.point, keep=keep)
    if holes:
        filled = refine.fill_holes(mask)
    else:
        filled = mask
    detached = 0
    if detach > 0:
        filled, detached = refine.detach_bridges(
            filled, round(detach * s), point=hint.point
        )
    cv2 = _cv2()
    # the subject: its kept pixels at the matte's alpha, filled holes solid, and
    # only the soft (sub-threshold) fringe of the matte within 2 px of it, so a
    # dropped neighbour's pixels never come back through the edge
    support = cv2.dilate(filled.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    fringe = support & ~filled & (raw <= refine.SUBJECT)
    alpha = np.where(filled, np.where(mask, raw, 1.0), np.where(fringe, raw, 0.0))
    alpha = alpha.astype(np.float32)
    recipe = {
        **m.recipe(),
        "keep": keep,
        "fill_holes": holes,
        "detach_px": detach,
        "upscale": upscale,
    }
    return _Cut(sub, raw, alpha, hint, region, detached, recipe)


def _finish_alpha(
    alpha: np.ndarray, *, choke: float, feather: float, s: float
) -> np.ndarray:
    alpha = refine.choke(alpha, choke * s)
    return np.clip(refine.feather(alpha, feather * s), 0, 1).astype(np.float32)


def carve(
    image: ImageLike,
    *,
    matte: str | MatteLike = "flat_colour",
    crop: Box | None = None,
    box: Box | None = None,
    point: tuple[float, float] | None = None,
    keep: str = "point",
    fill_holes: bool = True,
    detach: float = 0,
    choke: float = 0,
    feather: float = 0.6,
    despill: int = 1,
    upscale: float = 1.0,
    pad: int = 4,
    source: AssetSource | None = None,
) -> Carving:
    """Cut a part out of ``image``; every coordinate is in the source image's pixels.

    image: a path, a PIL image or an RGB(A) array (``grab_frame`` for video)
    matte: the strategy (:mod:`cutan.carve.mattes`): a name, a ``Matte``
        (``Polygon(pts) & FlatColour()``) or any ``(rgb, hint) -> alpha``
    crop: ``(x0, y0, x1, y1)``, the region carved (default: the whole image)
    box: a box around the subject (GrabCut's default rectangle)
    point: a pixel on the subject; ``keep="point"`` keeps its component, and it
        becomes the part's anchor (default: the part's centre)
    keep: ``"point"``, ``"largest"`` or ``"all"`` components
    fill_holes: fill what the subject encloses (a pale face the matte missed)
    detach: cut off pieces hanging on the subject by a neck narrower than
        ``2 * detach`` px (caption letters); 0 keeps them and reports them
    choke: pull the edge in by this many px, then ``feather`` softens it (px)
    despill: re-paint the edge from the subject's solid pixels at least this
        many px inside it (1: the anti-aliased band; more for a neural matte's
        fuzzy fringe; 0: off)
    upscale: matte at this factor of the source resolution (Lanczos), then
        come back: smoother edges on small or low-resolution subjects
    pad: transparent px left around the trimmed part
    source: provenance (:func:`~cutan.carve.provenance.frame_source`), kept
        with the recipe and the quality in ``Carving.provenance()``

    >>> img = np.full((60, 80, 3), 250, np.uint8); img[15:45, 20:60] = (30, 90, 200)
    >>> part = carve(img)
    >>> part.size, round(part.quality.coverage, 2), part.quality.warnings()
    ((50, 40), 0.25, [])

    Without de-spill the feathered edge keeps the backdrop's colour, and the
    quality says so:

    >>> carve(img, despill=0).quality.warnings()
    ['51% of the rim is backdrop-coloured: raise despill or choke']
    """
    rgb = load_rgb(image)
    c = _cut(
        rgb,
        matte=matte,
        crop=crop,
        box=box,
        point=point,
        upscale=upscale,
        keep=keep,
        holes=fill_holes,
        detach=detach,
    )
    s = c.hint.scale
    solid = refine.choke(c.alpha, choke * s)
    alpha = _finish_alpha(c.alpha, choke=choke, feather=feather, s=s)
    region_rgb = c.rgb
    raw = c.raw
    if upscale != 1.0:  # back to the source resolution: the source's own pixels
        x0, y0, x1, y1 = c.region
        size = (x1 - x0, y1 - y0)
        alpha, raw, solid = (
            np.clip(_resize(x, size, up=False), 0, 1) for x in (alpha, raw, solid)
        )
        region_rgb = rgb[y0:y1, x0:x1]
        s = 1.0
    colours = (
        refine.despill(region_rgb, alpha, despill, solid=solid)
        if despill
        else region_rgb
    )
    quality = _quality(
        colours,
        alpha,
        raw,
        detached=c.detached,
        neck_px=max(int(detach * s), 2),
        point=None
        if point is None
        else ((point[0] - c.region[0]) * s, (point[1] - c.region[1]) * s),
    )
    rgba = np.dstack([colours, np.round(alpha * 255).astype(np.uint8)])
    trim = _trim_box(alpha, pad)
    if trim is None:
        raise ValueError(
            f"the matte {c.recipe['matte']!r} left nothing of the region {c.region}: "
            "check the crop, the point, or try another strategy"
        )
    tx0, ty0, tx1, ty1 = trim
    part = Image.fromarray(rgba[ty0:ty1, tx0:tx1], "RGBA")
    offset = (c.region[0] + tx0 / s, c.region[1] + ty0 / s)
    if point is not None:
        ax, ay = (point[0] - offset[0]) * s, (point[1] - offset[1]) * s
        anchor = (ax / part.width, ay / part.height)
    else:
        anchor = (0.5, 0.5)
    recipe = {
        **c.recipe,
        "choke_px": choke,
        "feather_px": feather,
        "despill_px": despill,
    }
    return Carving(
        image=part,
        anchor=(float(anchor[0]), float(anchor[1])),
        offset=(float(offset[0]), float(offset[1])),
        scale=float(s),
        quality=quality,
        recipe=recipe,
        source=source,
        meta={"region_in_source": list(c.region)},
    )


def _trim_box(alpha: np.ndarray, pad: int) -> tuple[int, int, int, int] | None:
    ys, xs = np.nonzero(alpha > _EMPTY)
    if not len(ys):
        return None
    h, w = alpha.shape
    return (
        max(int(xs.min()) - pad, 0),
        max(int(ys.min()) - pad, 0),
        min(int(xs.max()) + 1 + pad, w),
        min(int(ys.max()) + 1 + pad, h),
    )


# ---------------------------------------------------------------------------
# head mode


def carve_head(
    image: ImageLike,
    *,
    face: Face | Box | None = None,
    locate: FaceLocator | None = None,
    pick: str = "largest",
    matte: str | MatteLike = "flat_colour",
    cut: str = "auto",
    neck: float | None = None,
    neck_soft: float = NECK_SOFT,
    pad_x: float = 1.05,
    pad_top: float = 1.25,
    pad_bottom: float = 1.0,
    upscale: float = 3.0,
    keep: str = "point",
    fill_holes: bool = True,
    detach: float = 0,
    choke: float = 0,
    feather: float = 0.6,
    despill: int = 1,
    canvas: int = HEAD_CANVAS,
    face_h: float = HEAD_FACE_H,
    centre: tuple[float, float] = HEAD_CENTRE,
    margin: int = 6,
    source: AssetSource | None = None,
) -> Carving:
    """A head cut out at the neck and normalised onto a ``canvas``-px square.

    face: the face, a :class:`~cutan.carve.head.Face` (box and, when known, a
        jaw contour) or a box ``(x0, y0, x1, y1)``; ``None`` runs ``locate``
    locate: a face locator ``rgb -> [Face]`` (default
        :class:`~cutan.carve.head.InsightFaceLocator`, ``cutan[faces]``);
        ``pick`` chooses among several faces
    cut: the neck cut, ``"auto"`` (along the jaw when the face has a contour,
        else flat under the chin), ``"jaw"``, ``"flat"`` or ``"none"``;
        ``neck`` its depth in face-box heights, ``neck_soft`` its soft edge
    pad_x, pad_top, pad_bottom: the crop around the face, in face-box widths
        (each side) and heights (above, below)
    upscale: matte at this factor (heads are small in a frame)
    face_h, centre: the face box is scaled to ``face_h`` px high and its
        centre put on ``centre``, unless the head would then leave the canvas
        (less ``margin``), in which case it is scaled down to fit

    The rest are :func:`carve`'s; ``despill`` is in source px (a neural matte
    on a photo wants about 4: the starter used 12 at 3x). The part's anchor is ``centre`` (the face
    centre); ``meta`` holds the face box and the chin on the canvas.
    """
    rgb = load_rgb(image)
    if face is None:
        faces = (locate or InsightFaceLocator())(rgb)
        face = pick_face(faces, pick)
    elif not isinstance(face, Face):
        face = Face(tuple(face))
    fx, fy = face.centre
    crop = (
        fx - pad_x * face.width,
        face.box[1] - pad_top * face.height,
        fx + pad_x * face.width,
        face.box[3] + pad_bottom * face.height,
    )

    def gate(shape, hint):
        return neck_cut(
            shape,
            face,
            cut=cut,
            neck=neck,
            soft=neck_soft,
            offset=hint.offset,
            scale=hint.scale,
        )

    c = _cut(
        rgb,
        matte=matte,
        crop=crop,
        box=face.box,
        point=face.centre,
        upscale=upscale,
        keep=keep,
        holes=fill_holes,
        detach=detach,
        gate=gate,
    )
    s = c.hint.scale
    # the neck cut stays soft: re-apply it after the holes were filled
    gated = c.alpha * gate(c.alpha.shape, c.hint)
    solid = refine.choke(gated, choke * s)
    alpha = _finish_alpha(gated, choke=choke, feather=feather, s=s)
    colours = (
        refine.despill(c.rgb, alpha, round(despill * s), solid=solid)
        if despill
        else c.rgb
    )
    quality = _quality(
        colours,
        alpha,
        c.raw,
        detached=c.detached,
        neck_px=max(int(detach * s), 2),
        point=c.hint.point,
    )
    rgba = np.dstack([colours, np.round(alpha * 255).astype(np.uint8)])

    # normalise: face box to face_h, its centre on `centre`, the head inside the canvas
    ys, xs = np.nonzero(alpha > _EMPTY)
    if not len(ys):
        raise ValueError(f"the matte {c.recipe['matte']!r} left nothing of the head")
    pcx, pcy = c.hint.point
    cx, cy = centre
    k = face_h / (face.height * s)
    room = [
        (cy - margin) / max(pcy - ys.min(), 1e-6),
        (canvas - margin - cy) / max(ys.max() + 1 - pcy, 1e-6),
        (cx - margin) / max(pcx - xs.min(), 1e-6),
        (canvas - margin - cx) / max(xs.max() + 1 - pcx, 1e-6),
    ]
    k = min(k, *room)
    cv2 = _cv2()
    m = np.float32([[k, 0, cx - pcx * k], [0, k, cy - pcy * k]])
    premult = rgba.astype(np.float32)
    premult[..., :3] *= premult[..., 3:4] / 255.0
    warped = cv2.warpAffine(
        premult,
        m,
        (canvas, canvas),
        flags=cv2.INTER_AREA if k < 1 else cv2.INTER_LANCZOS4,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0, 0),
    )
    a = np.clip(warped[..., 3], 0, 255)
    col = np.where(
        a[..., None] > 0.5, warped[..., :3] * 255.0 / np.maximum(a[..., None], 1e-6), 0
    )
    out = np.dstack([np.clip(col, 0, 255), a]).round().astype(np.uint8)
    total = s * k  # source px -> canvas px
    x0, y0 = c.region[:2]
    offset = (x0 + (0 - (cx - pcx * k)) / total, y0 + (0 - (cy - pcy * k)) / total)
    recipe = {
        **c.recipe,
        "mode": "head",
        "cut": cut if cut != "auto" else ("jaw" if face.jaw else "flat"),
        "neck": neck,
        "choke_px": choke,
        "feather_px": feather,
        "despill_px": despill,
        "canvas": canvas,
        "face_h": face_h,
        "centre": list(centre),
    }
    meta = {
        "region_in_source": list(c.region),
        "face_box_in_source": list(face.box),
        "face_box_h_on_canvas": float(face.height * total),
        "face_centre_on_canvas": [float(cx), float(cy)],
        "chin_y_on_canvas": float((face.chin_y - offset[1]) * total),
        "scaled_to_fit": bool(k < face_h / (face.height * s) - 1e-9),
        "face_score": face.score,
    }
    return Carving(
        image=Image.fromarray(out, "RGBA"),
        anchor=(cx / canvas, cy / canvas),
        offset=(float(offset[0]), float(offset[1])),
        scale=float(total),
        quality=quality,
        recipe=recipe,
        source=source,
        meta=meta,
    )
