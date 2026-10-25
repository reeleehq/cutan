"""Super-resolution strategies: more pixels for a part carved from a low-resolution frame (cutan#110).

When the only copy of a frame is small (a 360p scan), a thin part such as a
sabre's blade is 3-5 px wide. ``carve(upscale=k)`` mattes at ``k``x and comes
back to the source's resolution, so the part stays 3-5 px wide. A **super
resolution strategy** is applied to the crop *before* the matte, and the part
**keeps its resolution**: ``carve(frame, superres="realesr-animevideov3")``
returns a part 4x the source's size whose ``offset``/``scale`` (``to_part``)
still map source pixels into it, so recipes, pivots and landmarks stay in the
source's pixels.

A strategy is any callable ``rgb -> rgb`` that returns the ``HxWx3`` ``uint8``
image a whole factor larger on both sides; the shipped ones are classes with a
``factor``, a ``name`` and a ``recipe()`` (what provenance records, and what
:func:`as_superres` builds the same strategy back from).

=========================  ==================================================  ==========================================
name                       what it does                                        needs
=========================  ==================================================  ==========================================
``resample``               interpolation (no new detail): the matte's          OpenCV (``cutan[carve]``)
                           resolution is kept instead of thrown away
``realesr-animevideov3``   Real-ESRGAN for anime/cartoon video (BSD-3), x4,    ``onnxruntime`` (``cutan[superres]``);
                           in overlapping tiles: clean on flat cartoon art     the 2.5 MB model is fetched once
=========================  ==================================================  ==========================================

>>> import numpy as np
>>> rgb = np.zeros((10, 12, 3), np.uint8); rgb[2:8, 3:9] = 200
>>> sr = as_superres({"superres": "resample", "factor": 2})
>>> sr(rgb).shape, sr.recipe()
((20, 24, 3), {'superres': 'resample', 'factor': 2, 'method': 'cubic'})
"""

from __future__ import annotations

import hashlib
import os
import tempfile
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import numpy as np

from cutan.carve._deps import cv2 as _cv2
from cutan.carve._deps import require

__all__ = [
    "MODELS",
    "MODELS_DIR_ENV",
    "SUPERRES",
    "ModelFile",
    "RealESRGAN",
    "Resample",
    "SuperRes",
    "SuperResLike",
    "as_superres",
    "factor_of",
    "models_dir",
    "register_superres",
]

#: The environment variable that moves the model cache (default ``~/.cache/cutan/models``).
MODELS_DIR_ENV: str = "CUTAN_MODELS_DIR"
#: Pixels of context each tile shares with its neighbours (each side, source px):
#: a tile's output is kept only away from its border, so no seam shows.
DFLT_OVERLAP: int = 16


@runtime_checkable
class SuperResLike(Protocol):
    """Anything that super-resolves: ``rgb -> rgb``, a whole factor larger."""

    def __call__(self, rgb: np.ndarray) -> np.ndarray: ...


@dataclass(frozen=True)
class ModelFile:
    """A model file a strategy downloads once and checks by hash."""

    url: str
    sha256: str
    factor: int
    #: The fixed input size the graph was exported with (square), or ``None``.
    tile: int | None
    license: str

    @property
    def filename(self) -> str:
        return self.url.rsplit("/", 1)[-1]


#: The models the shipped strategies know, by name. A revision-pinned URL and a
#: hash: a model never changes under a recipe that names it.
MODELS: dict[str, ModelFile] = {
    "realesr-animevideov3": ModelFile(
        url=(
            "https://huggingface.co/Tomoali/realesr-animevideov3-onnx/resolve/"
            "903f497f80951d432ca187d50d4df7ccddf822bb/animevideov3_nchw_256x256_fp32.onnx"
        ),
        sha256="139f166bd2b955c7d4cd31ca2616eb97dacc4365c1c315d880735ce72a0663d9",
        factor=4,
        tile=256,
        license="BSD-3-Clause (Real-ESRGAN, xinntao)",
    ),
}


def models_dir() -> Path:
    """Where downloaded models are kept: ``$CUTAN_MODELS_DIR``, else ``~/.cache/cutan/models``."""
    return Path(
        os.environ.get(MODELS_DIR_ENV) or Path.home() / ".cache" / "cutan" / "models"
    )


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _fetch(model: ModelFile, *, folder: Path, download: bool) -> Path:
    """The model's local file, downloaded into ``folder`` (and hash-checked) if missing."""
    path = folder / model.filename
    if path.exists():
        if _sha256(path) != model.sha256:
            raise ValueError(
                f"{path} does not have the expected sha256 {model.sha256}: delete it "
                "and it is downloaded again"
            )
        return path
    if not download:
        raise FileNotFoundError(
            f"{path} is missing; download it from {model.url} (or pass download=True)"
        )
    folder.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=folder, suffix=".part")
    os.close(fd)
    try:
        urllib.request.urlretrieve(model.url, tmp)  # noqa: S310 - a pinned https URL
        got = _sha256(Path(tmp))
        if got != model.sha256:
            raise ValueError(
                f"{model.url} downloaded with sha256 {got}, not {model.sha256}: refused"
            )
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return path


class SuperRes:
    """Base of the shipped strategies: a ``name``, a whole ``factor`` and a ``recipe()``."""

    name: str = "superres"
    factor: int = 1

    def __call__(self, rgb: np.ndarray) -> np.ndarray:  # pragma: no cover
        raise NotImplementedError

    def recipe(self) -> dict[str, Any]:
        """The strategy's name under ``"superres"`` and its settings, plain JSON."""
        return {"superres": self.name, **self._settings()}

    def _settings(self) -> dict[str, Any]:
        return {}


class Resample(SuperRes):
    """Interpolate ``factor``x (``cubic``, ``linear`` or ``lanczos``): no new
    detail, but the matte's resolution is what the part keeps.

    >>> Resample(3)(np.zeros((4, 5, 3), np.uint8)).shape
    (12, 15, 3)
    """

    name = "resample"
    METHODS = ("cubic", "linear", "lanczos")

    def __init__(self, factor: int = 2, *, method: str = "cubic"):
        if int(factor) != factor or factor < 1:
            raise ValueError(f"factor is a whole number >= 1, not {factor!r}")
        if method not in self.METHODS:
            raise ValueError(f"method is one of {self.METHODS}, not {method!r}")
        self.factor, self.method = int(factor), method

    def __call__(self, rgb: np.ndarray) -> np.ndarray:
        cv2 = _cv2()
        flag = {
            "cubic": cv2.INTER_CUBIC,
            "linear": cv2.INTER_LINEAR,
            "lanczos": cv2.INTER_LANCZOS4,
        }[self.method]
        h, w = rgb.shape[:2]
        return cv2.resize(rgb, (w * self.factor, h * self.factor), interpolation=flag)

    def _settings(self) -> dict[str, Any]:
        return {"factor": self.factor, "method": self.method}


class RealESRGAN(SuperRes):
    """Real-ESRGAN through ONNX Runtime, run in overlapping tiles.

    model: a name in :data:`MODELS` (its file is downloaded once into
        :func:`models_dir` and checked by hash); ``path``: a local copy of that
        same file (checked by hash too; never written to the recipe)
    overlap: source px each tile shares with its neighbours (each side)
    session: an already-built ``onnxruntime.InferenceSession`` (or anything
        with its ``run(names, feeds)``), instead of loading the model
    download: fetch the model when it is not in the cache

    The model sees ``[0, 1]`` RGB in ``NCHW`` and returns the same ``factor``x.
    The image is mirrored at its border, so the edge tiles see context too.
    """

    def __init__(
        self,
        model: str = "realesr-animevideov3",
        *,
        path: str | Path | None = None,
        overlap: int = DFLT_OVERLAP,
        session: Any = None,
        download: bool = True,
    ):
        if model not in MODELS:
            raise ValueError(
                f"no super-resolution model {model!r}; the models are: {', '.join(sorted(MODELS))}"
            )
        spec = MODELS[model]
        if spec.tile is not None and not 0 <= 2 * overlap < spec.tile:
            raise ValueError(
                f"overlap is 0 to {spec.tile // 2 - 1} px for {model!r}, not {overlap!r}"
            )
        self.name, self.model, self.factor = model, model, spec.factor
        self.overlap, self.path, self.download = int(overlap), path, download
        self._spec, self._session = spec, session

    def _settings(self) -> dict[str, Any]:
        # never the local ``path``: a recipe is provenance, published with the art
        return {"overlap": self.overlap}

    def model_file(self) -> Path:
        """The model's local file (downloading it if allowed and missing), hash-checked."""
        if self.path is None:
            return _fetch(self._spec, folder=models_dir(), download=self.download)
        path = Path(self.path)
        if _sha256(path) != self._spec.sha256:
            raise ValueError(
                f"{path} is not the {self.model!r} model (sha256 {self._spec.sha256}): "
                "a recipe names the model by its hash"
            )
        return path

    def recipe(self) -> dict[str, Any]:
        """The name, the settings and the model's hash (what made these pixels)."""
        return {**super().recipe(), "sha256": self._spec.sha256}

    def session(self) -> Any:
        if self._session is None:
            ort = require("onnxruntime")
            self._session = ort.InferenceSession(
                str(self.model_file()), providers=["CPUExecutionProvider"]
            )
        return self._session

    def __call__(self, rgb: np.ndarray) -> np.ndarray:
        session = self.session()
        inputs = getattr(session, "get_inputs", None)
        feed = inputs()[0].name if inputs else "input"
        f, o = self.factor, self.overlap
        tile = self._spec.tile or 256
        step = tile - 2 * o
        h, w = rgb.shape[:2]
        ny, nx = -(-h // step), -(-w // step)
        pad = ((o, ny * step - h + o), (o, nx * step - w + o), (0, 0))
        mode = "reflect" if min(h, w) > 1 else "edge"
        src = np.pad(rgb, pad, mode=mode).astype(np.float32) / 255.0
        out = np.zeros((ny * step * f, nx * step * f, 3), np.float32)
        for j in range(ny):
            for i in range(nx):
                y, x = j * step, i * step
                patch = src[y : y + tile, x : x + tile].transpose(2, 0, 1)[None]
                up = session.run(None, {feed: np.ascontiguousarray(patch)})[0][0]
                core = up.transpose(1, 2, 0)[
                    o * f : (o + step) * f, o * f : (o + step) * f
                ]
                out[y * f : (y + step) * f, x * f : (x + step) * f] = core
        return np.clip(out[: h * f, : w * f] * 255.0 + 0.5, 0, 255).astype(np.uint8)


class _Function(SuperRes):
    """A plain callable as a strategy; its factor is read from what it returns."""

    def __init__(self, fn: Callable[[np.ndarray], np.ndarray]):
        target = fn if hasattr(fn, "__qualname__") else type(fn)
        self.name = f"{getattr(target, '__module__', '?')}:{getattr(target, '__qualname__', '?')}"
        self._fn, self.factor = fn, 0  # 0: known after the first call

    def __call__(self, rgb: np.ndarray) -> np.ndarray:
        out = np.asarray(self._fn(rgb))
        self.factor = factor_of(rgb.shape, out.shape)
        return out


#: The strategies by name: ``{name: (factory, accepted settings)}``. A model name
#: is a strategy of its own (``"realesr-animevideov3"``), so a recipe stays one word.
SUPERRES: dict[str, Callable[..., SuperRes]] = {
    "resample": Resample,
    **{name: (lambda name=name, **kw: RealESRGAN(name, **kw)) for name in MODELS},
}


def register_superres(name: str, factory: Callable[..., SuperRes]) -> None:
    """Make ``factory(**settings)`` the strategy ``name`` (what its recipes replay by)."""
    SUPERRES[name] = factory


def as_superres(spec: str | Mapping[str, Any] | SuperResLike | None) -> SuperRes | None:
    """A strategy from its name, its recipe, a :class:`SuperRes`, or any ``rgb -> rgb``
    callable; ``None`` stays ``None`` (no super resolution).

    >>> as_superres("resample").factor, as_superres(None) is None
    (2, True)
    >>> as_superres("magic")  # doctest: +ELLIPSIS
    Traceback (most recent call last):
      ...
    ValueError: no super-resolution strategy 'magic'; the strategies are: realesr-animevideov3, resample...
    """
    if spec is None or isinstance(spec, SuperRes):
        return spec
    if isinstance(spec, str):
        spec = {"superres": spec}
    if isinstance(spec, Mapping):
        params = dict(spec)
        name = params.pop("superres", None)
        params.pop("sha256", None)  # recorded, not a setting: the model's name pins it
        if name not in SUPERRES:
            raise ValueError(
                f"no super-resolution strategy {name!r}; the strategies are: "
                f"{', '.join(sorted(SUPERRES))}"
            )
        return SUPERRES[name](**params)
    if callable(spec):
        return _Function(spec)
    raise TypeError(
        f"superres is a strategy name, a recipe or a callable rgb -> rgb, not {spec!r}"
    )


def factor_of(before: tuple[int, ...], after: tuple[int, ...]) -> int:
    """The whole factor an image grew by, or a ``ValueError`` saying why it is not one.

    >>> factor_of((10, 12, 3), (40, 48, 3))
    4
    >>> factor_of((10, 12, 3), (40, 47, 3))
    Traceback (most recent call last):
      ...
    ValueError: a super-resolution strategy returned (40, 47, 3) for (10, 12, 3): not one whole factor on both sides
    """
    h, w = before[:2]
    fh, fw = after[0] / h, after[1] / w
    if fh != fw or fh != int(fh) or fh < 1 or tuple(after[2:]) != tuple(before[2:]):
        raise ValueError(
            f"a super-resolution strategy returned {tuple(after)} for {tuple(before)}: "
            "not one whole factor on both sides"
        )
    return int(fh)
