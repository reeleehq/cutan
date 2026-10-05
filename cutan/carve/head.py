"""Head mode: a face located, the neck cut under the jaw, the head normalised on a fixed canvas.

A carved head is useful only if every head from every source lands the same
way on its canvas, so a rig can take any of them: the face box is scaled to a
fixed height (:data:`HEAD_FACE_H`) and centred on a fixed point
(:data:`HEAD_CENTRE`) of a square canvas (:data:`HEAD_CANVAS`), and that point
is the part's origin (its anchor). The neck is cut just under the jaw,
following the jaw's contour when landmarks give one (a neck is narrower than
the jaw, so the cut dips at the chin), and straight across under the chin for
a profile, where landmarks fail.

The face comes from a :class:`Face` (a box, optionally a jaw contour) given by
hand, or from a locator: any ``rgb -> list[Face]`` callable. The shipped
locator wraps ``insightface`` (``pip install "cutan[faces]"``); on cartoon
frames detectors usually find nothing, and a hand box is the way.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

import numpy as np

from cutan.carve._deps import require

__all__ = [
    "HEAD_CANVAS",
    "HEAD_CENTRE",
    "HEAD_FACE_H",
    "Face",
    "FaceLocator",
    "InsightFaceLocator",
    "neck_cut",
    "pick_face",
]

#: Side of the square canvas a head is normalised onto, px.
HEAD_CANVAS: int = 512
#: Height the face box is scaled to, px.
HEAD_FACE_H: float = 270.0
#: Where the face box's centre lands on the canvas: the head part's origin.
HEAD_CENTRE: tuple[float, float] = (256.0, 300.0)

#: Neck cut defaults, in face-box heights: below the jaw contour, the extra
#: depth at the chin, below the chin for a flat cut, and the soft edge.
NECK_BELOW_JAW: float = 0.08
NECK_CHIN_EXTRA: float = 0.10
NECK_FLAT: float = 0.14
NECK_SOFT: float = 0.05


@dataclass(frozen=True)
class Face:
    """A face in an image: its box and, when known, its jaw contour.

    ``box`` is ``(x0, y0, x1, y1)``; ``jaw`` a sequence of ``(x, y)`` points
    along the jaw, ear to ear (any order, at least three); ``score`` the
    detector's confidence (1 for a hand box).

    >>> f = Face((10, 20, 50, 80))
    >>> f.width, f.height, f.centre, f.chin_y
    (40.0, 60.0, (30.0, 50.0), 80.0)
    """

    box: tuple[float, float, float, float]
    jaw: tuple[tuple[float, float], ...] | None = None
    score: float = 1.0

    def __post_init__(self) -> None:
        x0, y0, x1, y1 = self.box
        if x1 <= x0 or y1 <= y0:
            raise ValueError(
                f"a face box is (x0, y0, x1, y1) with x1 > x0 and y1 > y0, not {self.box}"
            )
        if self.jaw is not None:
            jaw = tuple((float(x), float(y)) for x, y in self.jaw)
            if len(jaw) < 3:
                raise ValueError("a jaw contour needs at least three points")
            object.__setattr__(self, "jaw", jaw)
        object.__setattr__(self, "box", tuple(float(v) for v in self.box))

    @property
    def width(self) -> float:
        return self.box[2] - self.box[0]

    @property
    def height(self) -> float:
        return self.box[3] - self.box[1]

    @property
    def centre(self) -> tuple[float, float]:
        return ((self.box[0] + self.box[2]) / 2, (self.box[1] + self.box[3]) / 2)

    @property
    def chin_y(self) -> float:
        """The lowest point of the jaw, else the box's bottom."""
        return max(y for _, y in self.jaw) if self.jaw else self.box[3]


FaceLocator = Callable[[np.ndarray], Sequence[Face]]


class InsightFaceLocator:
    """Faces and their jaw contours from ``insightface`` (106 landmarks; 0–32 are the jaw).

    ``min_score`` drops weak detections; the model (``buffalo_l``) is fetched
    by insightface on first use and kept for the process.
    """

    def __init__(
        self, *, model: str = "buffalo_l", min_score: float = 0.4, det_size: int = 960
    ):
        self.model, self.min_score, self.det_size = model, min_score, det_size
        self._app = None

    def __call__(self, rgb: np.ndarray) -> list[Face]:
        if self._app is None:
            app_mod = require("insightface").app
            self._app = app_mod.FaceAnalysis(
                name=self.model,
                providers=["CPUExecutionProvider"],
                allowed_modules=["detection", "landmark_2d_106"],
            )
            self._app.prepare(ctx_id=-1, det_size=(self.det_size, self.det_size))
        faces = []
        for f in self._app.get(np.ascontiguousarray(rgb[..., ::-1])):
            if f.det_score < self.min_score:
                continue
            lm = getattr(f, "landmark_2d_106", None)
            jaw = tuple(map(tuple, lm[0:33].tolist())) if lm is not None else None
            faces.append(
                Face(tuple(f.bbox.tolist()), jaw=jaw, score=float(f.det_score))
            )
        return faces


def pick_face(faces: Sequence[Face], pick: str = "largest") -> Face:
    """One face of several: ``largest``, ``leftmost``, ``rightmost`` or ``best`` (score).

    >>> pick_face([Face((0, 0, 10, 10)), Face((50, 0, 70, 20))]).box
    (50.0, 0.0, 70.0, 20.0)
    """
    if not faces:
        raise LookupError(
            "no face found: pass the face by hand, face=(x0, y0, x1, y1) "
            "(detectors rarely find cartoon faces)"
        )
    keys = {
        "largest": lambda f: f.width * f.height,
        "leftmost": lambda f: -f.box[0],
        "rightmost": lambda f: f.box[0],
        "best": lambda f: f.score,
    }
    if pick not in keys:
        raise ValueError(f"pick is one of {sorted(keys)}, not {pick!r}")
    return max(faces, key=keys[pick])


def neck_cut(
    shape: tuple[int, int],
    face: Face,
    *,
    cut: str = "auto",
    neck: float | None = None,
    soft: float = NECK_SOFT,
    offset: tuple[float, float] = (0.0, 0.0),
    scale: float = 1.0,
) -> np.ndarray:
    """A ``shape`` mask, 1 above the neck cut and 0 below, with a soft edge.

    ``cut``: ``"jaw"`` follows the jaw contour (ends extended past the ears,
    deeper at the chin), ``"flat"`` cuts straight across under the chin,
    ``"auto"`` is ``jaw`` when the face has a contour and ``flat`` otherwise,
    and ``"none"`` keeps everything. ``neck`` is the depth below the jaw (or
    the chin) in face-box heights. ``offset``/``scale`` map the face (given in
    source pixels) into the mask's pixels.

    >>> m = neck_cut((100, 50), Face((10, 10, 40, 60)), cut="flat", neck=0.1)
    >>> float(m[50, 25]), float(m[90, 25])
    (1.0, 0.0)
    """
    h_px, w_px = shape
    if cut == "none":
        return np.ones(shape, np.float32)
    if cut == "auto":
        cut = "jaw" if face.jaw else "flat"
    if cut not in ("jaw", "flat"):
        raise ValueError(f"cut is 'auto', 'jaw', 'flat' or 'none', not {cut!r}")
    if cut == "jaw" and not face.jaw:
        raise ValueError(
            "a jaw cut needs the face's jaw contour (a locator gives one); use cut='flat'"
        )
    ox, oy = offset
    fh, fw = face.height, face.width
    yy = np.arange(h_px, dtype=np.float32)[:, None]
    if cut == "flat":
        depth = NECK_FLAT if neck is None else neck
        line = np.full((1, w_px), (face.chin_y + depth * fh - oy) * scale, np.float32)
    else:
        depth = NECK_BELOW_JAW if neck is None else neck
        jaw = np.asarray(face.jaw, np.float64)
        jaw = jaw[np.argsort(jaw[:, 0])]
        chin_x = jaw[np.argmax(jaw[:, 1]), 0]
        # ears reach past the contour: extend its ends out and down so they keep their lobes
        jx = np.r_[jaw[0, 0] - 0.15 * fw, jaw[:, 0], jaw[-1, 0] + 0.15 * fw]
        jy = np.r_[jaw[0, 1] + 0.12 * fh, jaw[:, 1], jaw[-1, 1] + 0.12 * fh]
        xs = np.arange(w_px) / scale + ox
        envelope = np.interp(xs, jx, jy)
        dip = NECK_CHIN_EXTRA * fh * np.exp(-(((xs - chin_x) / (0.22 * fw)) ** 2))
        line = ((envelope + depth * fh + dip - oy) * scale)[None, :].astype(np.float32)
    edge = max(soft * fh * scale, 1e-6)
    return np.clip((line - yy) / edge, 0.0, 1.0).astype(np.float32)
