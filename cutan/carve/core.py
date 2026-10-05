"""The carve pipeline: an image (or a video frame) in, a matted, cleaned, provenance-carrying part out.

:func:`carve` runs crop → (upscale) → matte → keep → fill holes → detach
bridges → choke → feather → de-spill → trim, and returns a :class:`Carving`:
the RGBA part, where it came from in the source, its anchor, its quality
signals, and the recipe that cut it (recorded with its provenance).
:func:`carve_head` is the same pipeline with a neck cut and the head
normalised onto a fixed canvas (:mod:`cutan.carve.head`).

**Every coordinate a caller gives is in the source image's pixels** (crop,
box, point, a polygon's points, a face, a part's pivot), so a spec can be
written before anything is carved. A carving's ``recipe`` holds the
arguments it was made with, under their own names, so ``carve(image,
**part.recipe)`` (or ``carve_head``) replays it: a batch of carves is data.
"""

from __future__ import annotations

import io
import subprocess
from collections.abc import Mapping, Sequence
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
from cutan.carve.mattes import Hint, MatteLike, _plain, as_matte

__all__ = [
    "CHOKE",
    "DESPILL",
    "DETACH",
    "FEATHER",
    "FILL_HOLES",
    "KEEP",
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

#: The finishing defaults :func:`carve` and :func:`carve_head` share (one place,
#: so the two cannot drift): keep the component under the point, fill what the
#: subject encloses, detach nothing, no choke, a 0.6 px feather, de-spill 1 px.
KEEP: str = "point"
FILL_HOLES: bool = True
DETACH: float = 0
CHOKE: float = 0
FEATHER: float = 0.6
DESPILL: int = 1
#: How far (source px) a separate piece may lie from the subject and still be
#: kept with it under ``keep="point"`` (a hat a matte split off by a sliver).
GAP: float = 6
#: The neck below which a piece counts as hanging by a thread (quality only).
_NECK_PX: int = 2

#: The alpha below which a pixel is empty (trim, bounding boxes, rim tests).
_EMPTY = 8 / 255


@dataclass(frozen=True)
class CarveQuality:
    """Signals worth reading before a part is used (cutan#10).

    ``coverage``: the subject's share of the carved region (near 0 or 1 means
    the matte took nothing or everything). ``rim_backdrop_share``: the share
    of the part's partly transparent edge whose colour is still close to the
    backdrop's (a halo). ``repainted_share``: the share of the subject whose
    colour de-spill replaced (high means it repainted real content: lower
    ``despill``). ``soft_interior_share``: the share of the subject's interior
    (3 px or more inside its edge) that is see-through. ``detached_pieces``:
    pieces ``detach`` cut off; ``attached_pieces``: pieces still hanging on
    the subject by a neck under 4 px (caption glyphs, or a genuinely thin
    part). ``touches_edge``: the subject runs into the carved region's border,
    so the crop probably cut it off.
    """

    coverage: float
    rim_backdrop_share: float
    repainted_share: float
    soft_interior_share: float
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
        if self.repainted_share > 0.25:
            out.append(
                f"de-spill repainted {self.repainted_share:.0%} of the part: lower despill"
            )
        if self.soft_interior_share > 0.05:
            out.append(
                f"{self.soft_interior_share:.0%} of the part's interior is see-through: "
                "the matte is unsure there (another strategy, or Levels)"
            )
        if self.attached_pieces:
            out.append(
                f"{self.attached_pieces} piece(s) hang on the subject by a neck under 4 px "
                "(caption glyphs, or a thin part): detach=2 cuts them off"
            )
        if self.detached_pieces:
            out.append(
                f"detach cut off {self.detached_pieces} piece(s): check none was the subject's"
            )
        if self.touches_edge:
            out.append("the subject touches the crop's edge: widen the crop")
        return out

    def as_dict(self) -> dict[str, Any]:
        return {
            "coverage": round(self.coverage, 4),
            "rim_backdrop_share": round(self.rim_backdrop_share, 4),
            "repainted_share": round(self.repainted_share, 4),
            "soft_interior_share": round(self.soft_interior_share, 4),
            "detached_pieces": self.detached_pieces,
            "attached_pieces": self.attached_pieces,
            "touches_edge": self.touches_edge,
        }


@dataclass
class Carving:
    """A carved part.

    ``image``: the RGBA part. ``anchor``: its origin as ``(u, v)`` in 0..1 of
    the image (Pixi's convention, an ``Attachment.anchor``): the point for a
    plain carve, the face centre for a head. ``to_part`` maps a source pixel
    into the part's pixels (``part = (source - offset) * scale``; the 2×3
    matrix is ``meta["source_to_part"]``). ``mode`` is ``"part"`` or
    ``"head"``; ``recipe`` the arguments it was made with (replayable:
    ``carve(image, **recipe)`` or ``carve_head``); ``source`` the provenance;
    ``quality`` the signals; ``meta`` mode-specific facts.
    """

    image: Image.Image
    anchor: tuple[float, float]
    offset: tuple[float, float]
    scale: float
    quality: CarveQuality
    recipe: dict[str, Any]
    source: AssetSource | None = None
    meta: dict[str, Any] = field(default_factory=dict)
    mode: str = "part"

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
        """The source with how it was carved in its ``extra.carve``: the mode, the
        recipe, the quality and where the part sits in the source."""
        if self.source is None:
            return None
        extra = dict(self.source.extra or {})
        extra["carve"] = {
            "mode": self.mode,
            "recipe": self.recipe,
            "quality": self.quality.as_dict(),
            "region_in_source": self.meta.get("region_in_source"),
            "source_to_part": self.meta.get("source_to_part"),
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
        err = e.stderr.decode(errors="replace").strip()
        raise RuntimeError(f"ffmpeg could not read {video} at {t} s: {err}") from e
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


def _callable_name(fn: Any) -> str:
    """``module:qualname`` of a function or of a callable object's class (with its model, if it says)."""
    target = fn if hasattr(fn, "__qualname__") else type(fn)
    name = (
        f"{getattr(target, '__module__', '?')}:{getattr(target, '__qualname__', '?')}"
    )
    model = getattr(fn, "model", None)
    return f"{name}({model})" if isinstance(model, str) else name


def _upscale_factor(upscale: Any) -> int:
    u = float(upscale)
    if u < 1 or u != int(u):
        raise ValueError(f"upscale is a whole factor (1, 2, 3, ...), not {upscale!r}")
    return int(u)


def _quality(
    rgb: np.ndarray,
    alpha: np.ndarray,
    raw: np.ndarray,
    *,
    repainted: float,
    detached: int,
    point: tuple[float, float] | None,
    neck_px: int = _NECK_PX,
) -> CarveQuality:
    cv2 = _cv2()
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
    soft = 0.0
    if subject.any():
        inside = cv2.distanceTransform(
            np.pad(subject.astype(np.uint8), 1), cv2.DIST_L2, 3
        )
        interior = inside[1:-1, 1:-1] >= 3
        if interior.any():
            soft = float((alpha[interior] < 0.95).mean())
    attached = 0
    if subject.any():
        _, attached = refine.detach_bridges(subject, neck_px, point=point)
    edge = np.concatenate([subject[0], subject[-1], subject[:, 0], subject[:, -1]])
    return CarveQuality(
        coverage=coverage,
        rim_backdrop_share=rim_share,
        repainted_share=repainted,
        soft_interior_share=soft,
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
    matte_recipe: dict[str, Any]


def _cut(
    rgb: np.ndarray,
    *,
    matte: Any,
    crop: Box | None,
    box: Box | None,
    point: tuple[float, float] | None,
    upscale: int,
    keep: str,
    holes: bool,
    detach: float,
    gate: Any = None,
) -> _Cut:
    cv2 = _cv2()
    h, w = rgb.shape[:2]
    region = _clip_box(crop, w, h) if crop is not None else (0, 0, w, h)
    x0, y0, x1, y1 = region
    sub = rgb[y0:y1, x0:x1]
    if upscale != 1:  # linear: Lanczos rings, and the ringing darkens a rim
        sub = cv2.resize(
            sub,
            ((x1 - x0) * upscale, (y1 - y0) * upscale),
            interpolation=cv2.INTER_LINEAR,
        )
    s = float(upscale)
    hint = Hint(offset=(float(x0), float(y0)), scale=s)
    hint = replace(
        hint,
        box=tuple(np.ravel(hint.to_local([box[:2], box[2:]])))
        if box is not None
        else None,
        point=hint.to_local([point])[0] if point is not None else None,
    )
    m = as_matte(matte)
    raw = np.clip(np.asarray(m(sub, hint), np.float32), 0, 1)
    if raw.shape != sub.shape[:2]:
        raise ValueError(
            f"the matte returned {raw.shape}; the region is {sub.shape[:2]}"
        )
    if gate is not None:
        raw = raw * gate(sub.shape[:2], hint)
    mask = refine.keep_components(
        raw > refine.SUBJECT, point=hint.point, keep=keep, gap=round(GAP * s)
    )
    filled = refine.fill_holes(mask) if holes else mask
    detached = 0
    if detach > 0:
        filled, detached = refine.detach_bridges(
            filled, round(detach * s), point=hint.point
        )
    # the subject: its kept pixels at the matte's alpha, filled holes solid, and
    # only the soft (sub-threshold) fringe of the matte within 2 px of it, so a
    # dropped neighbour's pixels never come back through the edge
    reach = 2 * round(2 * s) + 1
    support = cv2.dilate(filled.astype(np.uint8), np.ones((reach, reach), np.uint8)) > 0
    fringe = support & ~filled & (raw <= refine.SUBJECT)
    alpha = np.where(filled, np.where(mask, raw, 1.0), np.where(fringe, raw, 0.0))
    return _Cut(sub, raw, alpha.astype(np.float32), hint, region, detached, m.recipe())


def _finish_alpha(
    alpha: np.ndarray, *, choke: float, feather: float, s: float
) -> np.ndarray:
    alpha = refine.choke(alpha, choke * s)
    return np.clip(refine.feather(alpha, feather * s), 0, 1).astype(np.float32)


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


def _affine(offset: tuple[float, float], scale: float) -> list[list[float]]:
    ox, oy = offset
    return [[scale, 0.0, -ox * scale], [0.0, scale, -oy * scale]]


def _nothing_left(recipe: dict, region) -> ValueError:
    return ValueError(
        f"the matte {recipe['matte']!r} left nothing of the region {tuple(region)}: "
        "check the crop, the point, or try another strategy"
    )


def carve(
    image: ImageLike,
    *,
    matte: str | Mapping[str, Any] | MatteLike = "flat_colour",
    crop: Box | None = None,
    box: Box | None = None,
    point: tuple[float, float] | None = None,
    keep: str = KEEP,
    fill_holes: bool = FILL_HOLES,
    detach: float = DETACH,
    choke: float = CHOKE,
    feather: float = FEATHER,
    despill: int = DESPILL,
    upscale: int = 1,
    pad: int = 4,
    source: AssetSource | None = None,
) -> Carving:
    """Cut a part out of ``image``; every coordinate is in the source image's pixels.

    image: a path, a PIL image or an RGB(A) array (``grab_frame`` for video)
    matte: the strategy (:mod:`cutan.carve.mattes`): a name, a recipe mapping,
        a ``Matte`` (``Polygon(pts) & FlatColour()``) or any ``(rgb, hint) -> alpha``
    crop: ``(x0, y0, x1, y1)``, the region carved (default: the whole image)
    box: a box around the subject (GrabCut's default rectangle)
    point: a pixel on the subject; ``keep="point"`` keeps its component, and it
        becomes the part's anchor (default: the part's centre)
    keep: ``"point"`` (its component and pieces within a few px), ``"largest"``
        or ``"all"`` components
    fill_holes: fill what the subject encloses (a pale face the matte missed)
    detach: cut off pieces hanging on the subject by a neck narrower than
        ``2 * detach`` px (caption letters; also any part that thin); 0 keeps
        them and reports them
    choke: pull the edge in by this many px, then ``feather`` softens it (px)
    despill: re-paint the edge from the subject's pixels at least this many px
        inside it (1: the anti-aliased band; about 4 for a neural matte's
        fuzzy fringe; 0: off)
    upscale: matte at this whole factor of the source resolution, then come
        back: smoother edges on small or low-resolution subjects
    pad: transparent px left around the trimmed part
    source: provenance (:func:`~cutan.carve.provenance.frame_source`), kept
        with the recipe and the quality in ``Carving.provenance()``

    >>> img = np.full((60, 80, 3), 250, np.uint8); img[15:45, 20:60] = (30, 90, 200)
    >>> part = carve(img)
    >>> part.size, round(part.quality.coverage, 2), part.quality.warnings()
    ((50, 40), 0.25, [])
    >>> carve(img, **part.recipe).recipe == part.recipe     # the recipe replays the carve
    True
    """
    rgb = load_rgb(image)
    up = _upscale_factor(upscale)
    c = _cut(
        rgb,
        matte=matte,
        crop=crop,
        box=box,
        point=point,
        upscale=up,
        keep=keep,
        holes=fill_holes,
        detach=detach,
    )
    s = c.hint.scale
    solid = refine.choke(c.alpha, choke * s)
    alpha = _finish_alpha(c.alpha, choke=choke, feather=feather, s=s)
    raw = c.raw
    x0, y0, x1, y1 = c.region
    region_rgb = rgb[y0:y1, x0:x1]
    if up != 1:  # back to the source resolution: the source's own pixels
        size = (x1 - x0, y1 - y0)
        alpha, raw, solid = (
            np.clip(_cv2().resize(a, size, interpolation=_cv2().INTER_AREA), 0, 1)
            for a in (alpha, raw, solid)
        )
    colours, repainted = (
        refine.despill(region_rgb, alpha, despill, solid=solid)
        if despill
        else (region_rgb, 0.0)
    )
    quality = _quality(
        colours,
        alpha,
        raw,
        repainted=repainted,
        detached=c.detached,
        point=None if point is None else (point[0] - x0, point[1] - y0),
    )
    rgba = np.dstack([colours, np.round(alpha * 255).astype(np.uint8)])
    trim = _trim_box(alpha, pad)
    if trim is None:
        raise _nothing_left(c.matte_recipe, c.region)
    tx0, ty0, tx1, ty1 = trim
    part = Image.fromarray(np.ascontiguousarray(rgba[ty0:ty1, tx0:tx1]), "RGBA")
    offset = (float(x0 + tx0), float(y0 + ty0))
    if point is not None:
        anchor = (
            (point[0] - offset[0]) / part.width,
            (point[1] - offset[1]) / part.height,
        )
    else:
        anchor = (0.5, 0.5)
    recipe = {
        "matte": c.matte_recipe,
        "crop": _plain(crop),
        "box": _plain(box),
        "point": _plain(point),
        "keep": keep,
        "fill_holes": fill_holes,
        "detach": detach,
        "choke": choke,
        "feather": feather,
        "despill": despill,
        "upscale": up,
        "pad": pad,
    }
    return Carving(
        image=part,
        anchor=(float(anchor[0]), float(anchor[1])),
        offset=offset,
        scale=1.0,
        quality=quality,
        recipe=recipe,
        source=source,
        meta={
            "region_in_source": list(c.region),
            "source_to_part": _affine(offset, 1.0),
        },
        mode="part",
    )


# ---------------------------------------------------------------------------
# head mode


def carve_head(
    image: ImageLike,
    *,
    face: Face | Box | Mapping[str, Any] | None = None,
    locate: FaceLocator | None = None,
    pick: str = "largest",
    matte: str | Mapping[str, Any] | MatteLike = "flat_colour",
    cut: str = "auto",
    neck: float | None = None,
    neck_soft: float = NECK_SOFT,
    pad_x: float = 1.05,
    pad_top: float = 1.25,
    pad_bottom: float = 1.0,
    upscale: int = 3,
    keep: str = KEEP,
    fill_holes: bool = FILL_HOLES,
    detach: float = DETACH,
    choke: float = CHOKE,
    feather: float = FEATHER,
    despill: int = DESPILL,
    canvas: int = HEAD_CANVAS,
    face_h: float = HEAD_FACE_H,
    centre: tuple[float, float] = HEAD_CENTRE,
    margin: int = 6,
    view: str | None = None,
    source: AssetSource | None = None,
) -> Carving:
    """A head cut out at the neck and normalised onto a ``canvas``-px square.

    face: the face, a :class:`~cutan.carve.head.Face` (box and, when known, a
        jaw contour and landmarks), a box ``(x0, y0, x1, y1)`` or a mapping
        (``Face.as_dict()``); ``None`` runs ``locate``
    locate: a face locator ``rgb -> [Face]`` (default
        :class:`~cutan.carve.head.InsightFaceLocator`, ``cutan[faces]``);
        ``pick`` chooses among several faces
    cut: the neck cut, ``"auto"`` (along the jaw when the face has a contour,
        else flat under the chin), ``"jaw"``, ``"flat"`` or ``"none"``;
        ``neck`` its depth in face-box heights, ``neck_soft`` its soft edge
    pad_x, pad_top, pad_bottom: the crop around the face, in face-box widths
        (each side) and heights (above, below)
    upscale: matte at this whole factor (heads are small in a frame)
    face_h, centre: the face box is scaled to ``face_h`` px high and its
        centre put on ``centre``, unless the head would then leave the canvas
        (less ``margin``), in which case it is scaled down to fit
    view: the view the head is drawn in, one of the rig's views (``front``,
        ``three_quarter``, ``side``, ``back``), recorded for the step that puts
        it on a rig; ``None`` when unknown

    The rest are :func:`carve`'s (``despill`` in source px: a neural matte on
    a photo wants about 4). The recipe pins the face, so a replay is
    reproducible whether it was given or located (``meta["located_by"]`` says
    which); a batch spec is ``{**shared_settings, **per_item}`` (the face and
    the crop per image, the matte and the finish shared). The part's anchor is ``centre`` (the face centre);
    ``meta`` holds what a rig needs to hang it: the face box, the chin and the
    neck point, the head's bounding box, the landmarks, all on the canvas.
    """
    from cutan.characters.schema import VIEWS

    if view is not None and view not in VIEWS:
        raise ValueError(
            f"view is one of the rig's views {VIEWS} (or None), not {view!r}"
        )
    cv2 = _cv2()
    rgb = load_rgb(image)
    up = _upscale_factor(upscale)
    located_by = None
    if face is None:
        locator = locate or InsightFaceLocator()
        face = pick_face(locator(rgb), pick)
        located_by = {"locator": _callable_name(locator), "pick": pick}
    face = Face.of(face)
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
        upscale=up,
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
    colours, repainted = (
        refine.despill(c.rgb, alpha, round(despill * s), solid=solid)
        if despill
        else (c.rgb, 0.0)
    )
    quality = _quality(
        colours,
        alpha,
        c.raw,
        repainted=repainted,
        detached=c.detached,
        point=c.hint.point,
        neck_px=round(_NECK_PX * s),  # the head is measured at the upscaled size
    )
    rgba = np.dstack([colours, np.round(alpha * 255).astype(np.uint8)])

    # normalise: face box to face_h, its centre on `centre`, the head inside the canvas
    ys, xs = np.nonzero(alpha > _EMPTY)
    if not len(ys):
        raise _nothing_left(c.matte_recipe, c.region)
    pcx, pcy = c.hint.point
    cx, cy = centre
    wanted = face_h / (face.height * s)
    k = min(
        wanted,
        (cy - margin) / max(pcy - ys.min(), 1e-6),
        (canvas - margin - cy) / max(ys.max() + 1 - pcy, 1e-6),
        (cx - margin) / max(pcx - xs.min(), 1e-6),
        (canvas - margin - cx) / max(xs.max() + 1 - pcx, 1e-6),
    )
    premult = rgba.astype(np.float32)
    premult[..., :3] *= premult[..., 3:4] / 255.0
    # scale first with a filter that suits the direction (INTER_AREA is only
    # honoured by resize), then place by a sub-pixel translation
    h0, w0 = premult.shape[:2]
    sw, sh = max(1, round(w0 * k)), max(1, round(h0 * k))
    scaled = cv2.resize(
        premult, (sw, sh), interpolation=cv2.INTER_AREA if k < 1 else cv2.INTER_CUBIC
    )
    kx, ky = sw / w0, sh / h0
    tx, ty = cx - pcx * kx, cy - pcy * ky
    warped = cv2.warpAffine(
        scaled,
        np.float32([[1, 0, tx], [0, 1, ty]]),
        (canvas, canvas),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0, 0),
    )
    a = np.clip(warped[..., 3], 0, 255)
    col = np.where(
        a[..., None] > 0.5, warped[..., :3] * 255.0 / np.maximum(a[..., None], 1e-6), 0
    )
    out = np.dstack([np.clip(col, 0, 255), a]).round().astype(np.uint8)
    total = s * kx  # source px -> canvas px
    x0, y0 = c.region[:2]
    offset = (x0 - tx / total, y0 - ty / total)

    def on_canvas(pts):
        return [
            [float((x - offset[0]) * total), float((y - offset[1]) * total)]
            for x, y in pts
        ]

    chin_x = max(face.jaw, key=lambda p: p[1])[0] if face.jaw else face.centre[0]
    neck_line = gate((c.alpha.shape[0], c.alpha.shape[1]), c.hint)
    col_x = int(min(max(round((chin_x - x0) * s), 0), neck_line.shape[1] - 1))
    below = np.nonzero(neck_line[:, col_x] < 0.5)[0]
    neck_y_src = (y0 + below[0] / s) if len(below) else face.box[3]
    bbox = Image.fromarray(out[..., 3]).point(lambda v: 255 if v > 8 else 0).getbbox()
    recipe = {
        "face": face.as_dict(),
        "matte": c.matte_recipe,
        "cut": cut,
        "neck": neck,
        "neck_soft": neck_soft,
        "pad_x": pad_x,
        "pad_top": pad_top,
        "pad_bottom": pad_bottom,
        "upscale": up,
        "keep": keep,
        "fill_holes": fill_holes,
        "detach": detach,
        "choke": choke,
        "feather": feather,
        "despill": despill,
        "canvas": canvas,
        "face_h": face_h,
        "centre": list(centre),
        "margin": margin,
        "view": view,
    }
    meta = {
        "region_in_source": list(c.region),
        "source_to_part": _affine(offset, total),
        "cut": cut if cut != "auto" else ("jaw" if face.jaw else "flat"),
        "view": view,
        "face_box_in_source": list(face.box),
        "face_box_h_on_canvas": float(face.height * total),
        "face_centre_on_canvas": [float(cx), float(cy)],
        "chin_y_on_canvas": float((face.chin_y - offset[1]) * total),
        "neck_on_canvas": on_canvas([(chin_x, neck_y_src)])[0],
        "head_bbox_on_canvas": list(bbox) if bbox else None,
        "landmarks_on_canvas": on_canvas(face.landmarks) if face.landmarks else None,
        "scaled_to_fit": bool(k < wanted - 1e-9),
        "face_score": face.score,
        # None: the face was given by hand; else how it was found (the recipe
        # pins the face either way, so a replay never re-runs a detector)
        "located_by": located_by,
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
        mode="head",
    )
