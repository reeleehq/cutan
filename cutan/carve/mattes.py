"""Matte strategies: which pixels of an image are the subject.

A **matte** is any callable ``(rgb, hint) -> alpha``: ``rgb`` an ``HxWx3``
``uint8`` array, ``hint`` a :class:`Hint` (where the subject is, in ``rgb``'s
own pixels), and ``alpha`` an ``HxW`` ``float32`` array in ``[0, 1]`` (1 is the
subject). It is the strategy seam of :func:`cutan.carve.carve`: no single
method wins (cutan#10), so each is one class here, chosen by name or passed as
an object, and two combine with ``&`` (both say subject) and ``|`` (either
does). ``Polygon(points) & FlatColour()`` is the hand outline cleaned by a
colour key, the recipe that won on flat cartoon frames.

==============  ====================================================  ==================================
name            works on                                              fails on
==============  ====================================================  ==================================
``flat_colour`` flat-colour cartoon frames: keys the backdrop colours  photos; a subject that shares the
                connected to the image border (the default)            backdrop's colour at its edge
``chroma``      footage with a saturated backdrop (a hue band)        anything without one
``grabcut``     one object with a rough box around it                 thin parts, low contrast
``polygon``     anything, given its outline by hand                   nothing; costs the outline
``focus``       a sharp object on a blurred background                flat art (no blur to read)
``rembg``       photos, front faces (``pip install "cutan[rembg]"``)  profiles, flat art, see-through
==============  ====================================================  ==================================

>>> import numpy as np
>>> rgb = np.full((40, 60, 3), 255, np.uint8)       # a white backdrop
>>> rgb[10:30, 20:40] = (200, 30, 30)              # a red square on it
>>> alpha = FlatColour()(rgb, Hint())
>>> round(float(alpha[20, 30]), 2), round(float(alpha[2, 2]), 2)
(1.0, 0.0)
>>> both = FlatColour() & Polygon([(20, 10), (30, 10), (30, 30), (20, 30)])
>>> float(both(rgb, Hint())[20, 35]) < 0.5         # inside the key, outside the outline
True
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

import numpy as np

from cutan.carve._deps import cv2 as _cv2
from cutan.carve._deps import require

__all__ = [
    "MATTES",
    "Chroma",
    "FlatColour",
    "Focus",
    "GrabCut",
    "Hint",
    "Matte",
    "MatteLike",
    "Polygon",
    "Rembg",
    "as_matte",
    "border_colours",
]

Box = tuple[float, float, float, float]
Point = tuple[float, float]


@dataclass(frozen=True)
class Hint:
    """Where the subject is, in the pixels of the image the matte is given.

    ``box`` is ``(x0, y0, x1, y1)`` around the subject, ``point`` one pixel on
    it. ``to_local`` maps a point given in the SOURCE image (before the crop
    and the upscale :func:`~cutan.carve.carve` applies) into these pixels,
    for strategies that take coordinates (a polygon, a GrabCut box).

    >>> Hint(offset=(100, 50), scale=2.0).to_local([(110, 60)])
    [(20.0, 20.0)]
    """

    box: Box | None = None
    point: Point | None = None
    offset: tuple[float, float] = (0.0, 0.0)
    scale: float = 1.0

    def to_local(self, points: Sequence[Point]) -> list[Point]:
        ox, oy = self.offset
        return [((x - ox) * self.scale, (y - oy) * self.scale) for x, y in points]


@runtime_checkable
class MatteLike(Protocol):
    """Anything that mattes: ``(rgb, hint) -> alpha``."""

    def __call__(self, rgb: np.ndarray, hint: Hint) -> np.ndarray: ...


class Matte:
    """Base of the shipped strategies: a name, a recipe, and ``&`` / ``|``.

    ``recipe()`` is what provenance records about how a part was cut: the
    strategy's name and its parameters (never the image).
    """

    name: str = "matte"

    def __call__(self, rgb: np.ndarray, hint: Hint) -> np.ndarray:  # pragma: no cover
        raise NotImplementedError

    def recipe(self) -> dict[str, Any]:
        params = {
            k: _plain(v)
            for k, v in vars(self).items()
            if not k.startswith("_") and k != "name" and v is not None
        }
        return {"matte": self.name, **params}

    def __and__(self, other: MatteLike) -> Matte:
        return _Combined("and", [self, as_matte(other)])

    def __or__(self, other: MatteLike) -> Matte:
        return _Combined("or", [self, as_matte(other)])


def _plain(v: Any) -> Any:
    """A JSON-friendly copy of a parameter (tuples to lists, arrays to lists)."""
    if isinstance(v, np.ndarray):
        return v.tolist()
    if isinstance(v, (list, tuple)):
        return [_plain(x) for x in v]
    if isinstance(v, Matte):
        return v.recipe()
    return v


class _Combined(Matte):
    """``a & b`` (pixelwise minimum) or ``a | b`` (maximum)."""

    def __init__(self, op: str, parts: list[Matte]):
        self.op, self._parts = op, parts
        self.name = op

    def __call__(self, rgb: np.ndarray, hint: Hint) -> np.ndarray:
        alphas = [_checked(p(rgb, hint), rgb, p) for p in self._parts]
        fold = np.minimum if self.op == "and" else np.maximum
        out = alphas[0]
        for a in alphas[1:]:
            out = fold(out, a)
        return out

    def recipe(self) -> dict[str, Any]:
        return {"matte": self.op, "of": [_recipe_of(p) for p in self._parts]}


class _Function(Matte):
    """A plain callable as a matte (its recipe records its qualified name)."""

    def __init__(self, fn: Callable[[np.ndarray, Hint], np.ndarray]):
        self._fn = fn
        self.name = getattr(fn, "__qualname__", type(fn).__name__)

    def __call__(self, rgb: np.ndarray, hint: Hint) -> np.ndarray:
        return self._fn(rgb, hint)

    def recipe(self) -> dict[str, Any]:
        return {"matte": self.name}


def _recipe_of(m: Any) -> dict[str, Any]:
    return m.recipe() if isinstance(m, Matte) else {"matte": type(m).__name__}


def _checked(alpha: Any, rgb: np.ndarray, who: Any) -> np.ndarray:
    a = np.asarray(alpha, dtype=np.float32)
    if a.shape != rgb.shape[:2]:
        raise ValueError(
            f"the matte {_recipe_of(who)['matte']!r} returned an alpha of shape "
            f"{a.shape}; the image is {rgb.shape[:2]}"
        )
    return np.clip(a, 0.0, 1.0)


# ---------------------------------------------------------------------------
# flat colour


def border_colours(
    rgb: np.ndarray, *, max_colours: int = 3, min_share: float = 0.08, bits: int = 4
) -> list[tuple[int, int, int]]:
    """The dominant colours of the image's border: the backdrop of a flat frame.

    Border pixels are binned at ``bits`` per channel; every bin holding at least
    ``min_share`` of the border (up to ``max_colours``, most frequent first)
    gives one colour, the median of its pixels.

    >>> img = np.zeros((20, 20, 3), np.uint8); img[:] = (250, 240, 230)
    >>> border_colours(img)
    [(250, 240, 230)]
    """
    edge = np.concatenate([rgb[0], rgb[-1], rgb[1:-1, 0], rgb[1:-1, -1]]).reshape(-1, 3)
    shift = 8 - bits
    keys = (
        (edge[:, 0].astype(np.int32) >> shift) << (2 * bits)
        | (edge[:, 1].astype(np.int32) >> shift) << bits
        | (edge[:, 2].astype(np.int32) >> shift)
    )
    uniq, counts = np.unique(keys, return_counts=True)
    order = np.argsort(-counts)
    out: list[tuple[int, int, int]] = []
    for i in order[:max_colours]:
        if counts[i] < min_share * len(keys):
            break
        px = edge[keys == uniq[i]]
        out.append(tuple(int(c) for c in np.median(px, axis=0)))
    return out


@dataclass
class FlatColour(Matte):
    """Key out the backdrop's flat colours, where they are connected to the border.

    ``colours``: the backdrop colours (RGB); ``None`` reads them off the
    image's border (:func:`border_colours`). A pixel within ``tolerance`` (the
    largest per-channel difference) of one is backdrop, with a ``softness``
    ramp beyond it for anti-aliased edges. ``connected`` keeps only backdrop
    regions that touch the image border (or the ``seeds``), so a white
    interior enclosed by an outline (an eye, a shirt) stays in the subject.
    """

    colours: Sequence[Sequence[int]] | None = None
    tolerance: float = 24.0
    softness: float = 16.0
    connected: bool = True
    seeds: Sequence[Point] | None = None
    name: str = field(default="flat_colour", init=False, repr=False)

    def __call__(self, rgb: np.ndarray, hint: Hint) -> np.ndarray:
        cv2 = _cv2()
        colours = self.colours if self.colours is not None else border_colours(rgb)
        if not colours:
            return np.ones(rgb.shape[:2], np.float32)
        img = rgb.astype(np.int16)
        dist = np.min(
            [np.abs(img - np.asarray(c, np.int16)).max(axis=2) for c in colours], axis=0
        ).astype(np.float32)
        backdrop = np.clip(
            1.0 - (dist - self.tolerance) / max(self.softness, 1e-6), 0, 1
        )
        if self.connected:
            region = (backdrop > 0.0).astype(np.uint8)
            n, labels = cv2.connectedComponents(region, connectivity=4)
            if self.seeds:
                local = hint.to_local(self.seeds)
                h, w = labels.shape
                ids = {
                    int(labels[min(max(int(y), 0), h - 1), min(max(int(x), 0), w - 1)])
                    for x, y in local
                }
            else:
                ids = set(
                    np.unique(
                        np.concatenate(
                            [labels[0], labels[-1], labels[:, 0], labels[:, -1]]
                        )
                    ).tolist()
                )
            ids.discard(0)
            backdrop = backdrop * np.isin(labels, list(ids))
        return (1.0 - backdrop).astype(np.float32)


# ---------------------------------------------------------------------------
# chroma


def _hue_deg(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    cv2 = _cv2()
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV_FULL).astype(np.float32)
    return hsv[..., 0] * (360.0 / 256.0), hsv[..., 1] / 255.0, hsv[..., 2] / 255.0


@dataclass
class Chroma(Matte):
    """Key out a saturated backdrop by its hue band (a stage drape, a green screen).

    ``hue``: ``(low, high)`` in degrees (``high < low`` wraps through red);
    ``None`` centres a band ``width`` degrees wide on the border's median hue.
    A pixel is backdrop when its hue is in the band (``ramp`` degrees soft at
    each end), its saturation above ``min_sat`` and its value above ``min_val``
    (each with a soft ramp), so dark and grey pixels of the subject stay.
    """

    hue: tuple[float, float] | None = None
    width: float = 60.0
    min_sat: float = 0.28
    min_val: float = 0.03
    ramp: float = 10.0
    name: str = field(default="chroma", init=False, repr=False)

    def band(self, rgb: np.ndarray) -> tuple[float, float]:
        """The hue band in degrees: the declared one, or the border's."""
        if self.hue is not None:
            return (float(self.hue[0]), float(self.hue[1]))
        h, s, _ = _hue_deg(rgb)
        edge = np.concatenate([h[0], h[-1], h[:, 0], h[:, -1]])
        sat = np.concatenate([s[0], s[-1], s[:, 0], s[:, -1]])
        edge = edge[sat > self.min_sat] if (sat > self.min_sat).any() else edge
        ang = np.radians(edge)
        mid = float(
            np.degrees(np.arctan2(np.sin(ang).mean(), np.cos(ang).mean())) % 360
        )
        return ((mid - self.width / 2) % 360, (mid + self.width / 2) % 360)

    def __call__(self, rgb: np.ndarray, hint: Hint) -> np.ndarray:
        lo, hi = self.band(rgb)
        h, s, v = _hue_deg(rgb)
        span = (hi - lo) % 360 or 360.0
        rel = (h - lo) % 360  # 0 at the low edge, span at the high edge
        r = max(self.ramp, 1e-6)
        in_hue = (
            np.clip(rel / r, 0, 1) * np.clip((span - rel) / r, 0, 1) * (rel <= span)
        )
        in_sv = np.clip((s - self.min_sat) / 0.12, 0, 1) * np.clip(
            (v - self.min_val) / 0.08, 0, 1
        )
        return (1.0 - in_hue * in_sv).astype(np.float32)


# ---------------------------------------------------------------------------
# GrabCut


@dataclass
class GrabCut(Matte):
    """OpenCV's GrabCut inside a box around one object.

    ``box``: ``(x0, y0, x1, y1)`` in the SOURCE image; ``None`` takes the
    hint's box, else the whole image less a ``margin`` share on each side.
    """

    box: Box | None = None
    iterations: int = 8
    margin: float = 0.02
    name: str = field(default="grabcut", init=False, repr=False)

    def __call__(self, rgb: np.ndarray, hint: Hint) -> np.ndarray:
        cv2 = _cv2()
        h, w = rgb.shape[:2]
        if self.box is not None:
            (x0, y0), (x1, y1) = hint.to_local([self.box[:2], self.box[2:]])
        elif hint.box is not None:
            x0, y0, x1, y1 = hint.box
        else:
            mx, my = self.margin * w, self.margin * h
            x0, y0, x1, y1 = mx, my, w - mx, h - my
        x0, y0 = max(int(x0), 0), max(int(y0), 0)
        x1, y1 = min(int(np.ceil(x1)), w), min(int(np.ceil(y1)), h)
        if x1 - x0 < 2 or y1 - y0 < 2:
            raise ValueError(
                f"the GrabCut box {(x0, y0, x1, y1)} is empty in a {w}x{h} image"
            )
        mask = np.zeros((h, w), np.uint8)
        bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
        cv2.grabCut(
            np.ascontiguousarray(rgb[..., ::-1]),
            mask,
            (x0, y0, x1 - x0, y1 - y0),
            bgd,
            fgd,
            self.iterations,
            cv2.GC_INIT_WITH_RECT,
        )
        return ((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD)).astype(np.float32)


# ---------------------------------------------------------------------------
# polygon


@dataclass
class Polygon(Matte):
    """A hand-given outline, ``[(x, y), ...]`` in the SOURCE image, anti-aliased."""

    points: Sequence[Point] = ()
    supersample: int = 4
    name: str = field(default="polygon", init=False, repr=False)

    def __post_init__(self) -> None:
        if len(self.points) < 3:
            raise ValueError("a polygon matte needs at least three points")

    def __call__(self, rgb: np.ndarray, hint: Hint) -> np.ndarray:
        cv2 = _cv2()
        h, w = rgb.shape[:2]
        k = max(int(self.supersample), 1)
        pts = np.asarray(hint.to_local(self.points), np.float64) * k
        big = np.zeros((h * k, w * k), np.uint8)
        cv2.fillPoly(big, [np.round(pts).astype(np.int32)], 255)
        small = cv2.resize(big, (w, h), interpolation=cv2.INTER_AREA)
        return small.astype(np.float32) / 255.0


# ---------------------------------------------------------------------------
# focus


@dataclass
class Focus(Matte):
    """The sharp region of an image whose background is out of focus.

    Local detail (the Laplacian's magnitude, averaged over ``window`` px) is
    thresholded by Otsu's method, closed, and its holes filled.
    """

    window: int = 15
    name: str = field(default="focus", init=False, repr=False)

    def __call__(self, rgb: np.ndarray, hint: Hint) -> np.ndarray:
        cv2 = _cv2()
        grey = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
        energy = cv2.blur(
            np.abs(cv2.Laplacian(grey, cv2.CV_32F, ksize=3)), (self.window,) * 2
        )
        norm = cv2.normalize(energy, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        _, sharp = cv2.threshold(norm, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        k = np.ones((self.window, self.window), np.uint8)
        sharp = cv2.morphologyEx(sharp, cv2.MORPH_CLOSE, k)
        return _fill_holes(sharp > 0).astype(np.float32)


def _fill_holes(mask: np.ndarray) -> np.ndarray:
    """``mask`` with every region not connected to the border filled."""
    cv2 = _cv2()
    inv = (~mask).astype(np.uint8)
    n, labels = cv2.connectedComponents(inv, connectivity=4)
    border = set(
        np.unique(
            np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]])
        ).tolist()
    )
    holes = (inv > 0) & ~np.isin(labels, list(border))
    return mask | holes


# ---------------------------------------------------------------------------
# rembg

_REMBG_SESSIONS: dict[str, Any] = {}


@dataclass
class Rembg(Matte):
    """``rembg``'s neural background removal (``pip install "cutan[rembg]"``).

    ``model``: a rembg model name (``isnet-general-use`` for photos and faces,
    ``isnet-anime`` for drawn figures, ``u2net_human_seg`` for people). The
    model is downloaded by rembg on first use and its session kept for the
    process.
    """

    model: str = "isnet-general-use"
    post_process: bool = True
    name: str = field(default="rembg", init=False, repr=False)

    def __call__(self, rgb: np.ndarray, hint: Hint) -> np.ndarray:
        rembg = require("rembg")
        session = _REMBG_SESSIONS.get(self.model)
        if session is None:
            session = _REMBG_SESSIONS[self.model] = rembg.new_session(self.model)
        out = rembg.remove(
            np.ascontiguousarray(rgb),
            session=session,
            post_process_mask=self.post_process,
        )
        out = np.asarray(out)
        return (
            (out[..., 3].astype(np.float32) / 255.0) if out.ndim == 3 else out / 255.0
        )


#: The strategies by name, for ``matte="<name>"``.
MATTES: dict[str, type[Matte]] = {
    "flat_colour": FlatColour,
    "chroma": Chroma,
    "grabcut": GrabCut,
    "polygon": Polygon,
    "focus": Focus,
    "rembg": Rembg,
}


def as_matte(matte: str | MatteLike) -> Matte:
    """A :class:`Matte` from a strategy's name, a ``Matte``, or any ``(rgb, hint) -> alpha`` callable.

    >>> as_matte("chroma").name
    'chroma'
    >>> as_matte("rainbow")  # doctest: +ELLIPSIS
    Traceback (most recent call last):
      ...
    ValueError: no matte strategy 'rainbow'; the strategies are: chroma, flat_colour, ...
    """
    if isinstance(matte, Matte):
        return matte
    if isinstance(matte, str):
        if matte not in MATTES:
            raise ValueError(
                f"no matte strategy {matte!r}; the strategies are: {', '.join(sorted(MATTES))}"
            )
        if matte == "polygon":
            raise ValueError(
                "the polygon matte needs its points: Polygon([(x, y), ...])"
            )
        return MATTES[matte]()
    if callable(matte):
        return _Function(matte)
    raise TypeError(
        f"a matte is a strategy name or a callable (rgb, hint) -> alpha, not {matte!r}"
    )
