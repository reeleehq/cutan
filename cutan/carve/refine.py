"""Clean a raw matte into a cut-out's alpha: keep the subject, close it, edge it, de-spill it.

Each step is a function of arrays, so a caller can run any of them alone;
:func:`cutan.carve.carve` runs them in this order:

1. :func:`keep_components` — keep the part under the hint point (else the
   largest), dropping specks and the stray objects a matte also caught;
2. :func:`fill_holes` — a pale face or an eye a matte called background;
3. :func:`detach_bridges` — cut what hangs on the subject by a thin neck (a
   caption's letters touching a head);
4. :func:`choke` and :func:`feather` — pull the edge in, then soften it;
5. :func:`despill` — re-paint the rim's colour from the subject's interior, so
   no backdrop colour is left in the semi-transparent edge.
"""

from __future__ import annotations

import numpy as np

from cutan.carve._deps import cv2 as _cv2

__all__ = [
    "SUBJECT",
    "choke",
    "despill",
    "detach_bridges",
    "feather",
    "fill_holes",
    "keep_components",
]

#: The alpha above which a pixel counts as the subject's.
SUBJECT: float = 0.5


def _labels(mask: np.ndarray) -> tuple[int, np.ndarray, np.ndarray]:
    """``(n, labels, areas)`` of the 8-connected components of ``mask`` (label 0 is empty)."""
    cv2 = _cv2()
    n, labels, stats, _ = cv2.connectedComponentsWithStats(
        mask.astype(np.uint8), connectivity=8
    )
    return n, labels, stats[:, cv2.CC_STAT_AREA]


def keep_components(
    mask: np.ndarray,
    *,
    point: tuple[float, float] | None = None,
    keep: str = "point",
    min_share: float = 0.02,
    gap: int = 6,
) -> np.ndarray:
    """The components of the boolean ``mask`` to keep.

    ``keep``: ``"point"`` keeps the component under ``point`` (the largest when
    the point is off the subject or not given) and the pieces lying within
    ``gap`` px of it that are at least ``min_share`` of its area (a hand or a
    hat a matte separated by a sliver); ``"largest"`` keeps the largest only;
    ``"all"`` keeps everything.

    >>> m = np.zeros((10, 30), bool); m[1:9, 1:9] = True; m[4:6, 25:27] = True
    >>> int(keep_components(m, keep="largest").sum()), int(keep_components(m, keep="all").sum())
    (64, 68)
    >>> int(keep_components(m, point=(25, 4)).sum())        # the small piece, alone
    4
    >>> m[4:6, 11:13] = True                                 # a piece 2 px from the body
    >>> int(keep_components(m, point=(4, 4), min_share=0.05).sum())
    68
    """
    if keep not in ("point", "largest", "all"):
        raise ValueError(f"keep is 'point', 'largest' or 'all', not {keep!r}")
    n, labels, areas = _labels(mask)
    if n <= 1 or keep == "all":
        return mask.astype(bool)
    main = 0
    if keep == "point" and point is not None:
        h, w = mask.shape
        x, y = int(round(point[0])), int(round(point[1]))
        if 0 <= x < w and 0 <= y < h:
            main = int(labels[y, x])
    if main == 0:
        main = 1 + int(np.argmax(areas[1:]))
    body = labels == main
    if keep == "largest" or gap <= 0:
        return body
    cv2 = _cv2()
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * gap + 1,) * 2)
    near = cv2.dilate(body.astype(np.uint8), kernel) > 0
    close = set(np.unique(labels[near]).tolist()) - {0, main}
    big = [main] + [i for i in close if areas[i] >= min_share * areas[main]]
    return np.isin(labels, big)


def fill_holes(mask: np.ndarray) -> np.ndarray:
    """``mask`` with every enclosed hole filled.

    >>> m = np.ones((5, 5), bool); m[2, 2] = False
    >>> bool(fill_holes(m)[2, 2])
    True
    """
    from cutan.carve.mattes import _fill_holes

    return _fill_holes(mask.astype(bool))


def detach_bridges(
    mask: np.ndarray, radius: int, *, point=None
) -> tuple[np.ndarray, int]:
    """Cut away what hangs on the main body by a neck narrower than ``2 * radius`` px.

    Erodes by ``radius``, keeps the eroded component under ``point`` (else the
    largest), grows it back by ``radius + 1`` inside the original mask. Returns
    ``(mask, pieces)``: the cleaned mask and how many sizeable pieces were cut
    off (the quality signal for glyphs left attached).

    >>> m = np.zeros((20, 40), bool); m[2:18, 2:18] = True   # a body
    >>> m[9:11, 18:24] = True; m[6:14, 24:32] = True          # a glyph on a 2-px neck
    >>> out, pieces = detach_bridges(m, 2)
    >>> pieces, bool(out[10, 28]), bool(out[10, 10])
    (1, False, True)
    """
    if radius <= 0:
        return mask.astype(bool), 0
    cv2 = _cv2()
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * radius + 1,) * 2)
    core = cv2.erode(mask.astype(np.uint8), kernel) > 0
    n, labels, areas = _labels(core)
    if n <= 1:
        return mask.astype(bool), 0
    main = 0
    if point is not None:
        x, y = int(round(point[0])), int(round(point[1]))
        if 0 <= y < core.shape[0] and 0 <= x < core.shape[1]:
            main = int(labels[y, x])
    if main == 0:
        main = 1 + int(np.argmax(areas[1:]))
    pieces = sum(1 for i in range(1, n) if i != main and areas[i] >= 4)
    grown = cv2.dilate((labels == main).astype(np.uint8), kernel, iterations=1)
    grown = cv2.dilate(grown, np.ones((3, 3), np.uint8)) > 0
    return grown & mask.astype(bool), pieces


def choke(alpha: np.ndarray, px: float) -> np.ndarray:
    """Pull the matte's edge in by ``px`` pixels (a smooth, distance-based erosion).

    >>> a = np.zeros((9, 9), np.float32); a[1:8, 1:8] = 1
    >>> float(choke(a, 2)[1, 4]), float(choke(a, 2)[4, 4])
    (0.0, 1.0)
    """
    if px <= 0:
        return alpha
    cv2 = _cv2()
    inside = (alpha > SUBJECT).astype(np.uint8)
    dist = cv2.distanceTransform(inside, cv2.DIST_L2, 3)
    return (alpha * np.clip(dist - px, 0.0, 1.0)).astype(np.float32)


def feather(alpha: np.ndarray, sigma: float) -> np.ndarray:
    """Soften the edge with a Gaussian of ``sigma`` px (0 leaves it as it is)."""
    if sigma <= 0:
        return alpha
    cv2 = _cv2()
    return cv2.GaussianBlur(alpha.astype(np.float32), (0, 0), sigma)


def despill(
    rgb: np.ndarray, alpha: np.ndarray, rim: int, *, solid: np.ndarray | None = None
) -> np.ndarray:
    """Re-paint the edge's colours from the subject's trusted pixels.

    Trusted: the pixels that were solid in the matte (``solid``, the alpha
    BEFORE any feathering; default ``alpha``) and at least ``rim`` px inside
    its edge. Every other pixel with some alpha (the anti-aliased band, a
    neural matte's fuzzy fringe, what feathering spread outward over the
    backdrop) takes its colour from the nearest trusted ones: colours flow
    outward one pixel per pass, each the mean of its known neighbours, never
    from the backdrop. An outline stays an outline: it is solid, so it is
    trusted. Returns a new array; pixels with no alpha keep theirs.

    >>> rgb = np.zeros((7, 7, 3), np.uint8); rgb[:] = (0, 0, 255)  # a blue backdrop
    >>> rgb[1:6, 1:6] = (200, 0, 0); rgb[1, 1:6] = (100, 0, 160)   # a red subject, a spilt top row
    >>> a = np.zeros((7, 7), np.float32); a[1:6, 1:6] = 1
    >>> tuple(int(c) for c in despill(rgb, a, 1)[1, 3])
    (200, 0, 0)
    """
    if rim <= 0:
        return rgb
    cv2 = _cv2()
    base = alpha if solid is None else solid
    trusted = (
        cv2.erode(
            (base > 0.99).astype(np.uint8), np.ones((3, 3), np.uint8), iterations=rim
        )
        > 0
    )
    target = (alpha > 0.01) & ~trusted
    if not trusted.any() or not target.any():
        return rgb
    col = rgb.astype(np.float32) * trusted[..., None]
    known = trusted.astype(np.float32)
    todo = target.copy()
    k = np.ones((3, 3), np.float32)
    while todo.any():
        num = cv2.filter2D(col, -1, k, borderType=cv2.BORDER_CONSTANT)
        den = cv2.filter2D(known, -1, k, borderType=cv2.BORDER_CONSTANT)
        front = todo & (den > 0)
        if not front.any():
            break  # pixels cut off from every trusted one keep their colour
        col[front] = num[front] / den[front, None]
        known[front] = 1.0
        todo &= ~front
    out = rgb.copy()
    painted = target & (known > 0)
    out[painted] = np.clip(np.round(col[painted]), 0, 255).astype(np.uint8)
    return out
