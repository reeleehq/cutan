"""Generated art: a prompt in, a keyed, fitted, provenance-carrying plate or part out (cutan#100).

An image model draws a plate (a landscape, a car's cabin) or a part; where the
art must be see-through (a car's windows) the prompt asks for a flat key colour,
and that colour is keyed to alpha by :mod:`cutan.carve`'s own matte (the
``chroma`` strategy), its rim de-spilled, then the image is cover-fitted to the
stage canvas and written as a PNG beside a record of where it came from.

>>> from PIL import Image
>>> def painter(prompt, *, size, background, quality=None, model=None):
...     im = Image.new("RGB", (64, 48), (246, 3, 242))      # the magenta key
...     im.paste((40, 110, 200), (16, 12, 48, 36))          # the subject
...     return im
>>> painter.provider, painter.model, painter.license = "test", "toy", "cc0-1.0"
>>> import tempfile
>>> made = generate_art({"box": {"prompt": "a blue box", "key": "magenta", "fit": [32, 24]}},
...                     out_dir=tempfile.mkdtemp(), generator=painter)
>>> made[0].path.name, made[0].size, made[0].source.license
('box.png', (32, 24), 'cc0-1.0')

- **The spec** (:func:`art_specs`): ``{name: {prompt, size, background, key,
  fit, model, quality}}``, a mapping or a JSON file. ``background``:
  ``"opaque"`` or ``"transparent"`` (the model's own alpha, where it has one);
  ``key``: a named key colour (:data:`KEYS`, ``"magenta"``) or any matte recipe
  :func:`~cutan.carve.mattes.as_matte` reads; ``fit``: ``[w, h]``, scale to
  cover and centre-crop; ``prop``: carve the image into a prop folder
  (``<name>/prop.json`` + ``parts/``, through :func:`~cutan.carve.carve` and
  :func:`~cutan.carve.write_prop`, with its quality warnings) instead of a plate.
- **The generator** is the seam: ``generator(prompt, *, size, background,
  quality, model) -> PIL image``, carrying ``provider``, ``model`` and
  ``license`` for the provenance. The default, :class:`AixGenerator`, calls
  the fleet's :func:`aix.generate_image` (OpenAI's ``gpt-image`` models by
  default; ``pip install "cutan[generate]"``).
- **The record**: each image's :class:`~an.ir.assets.AssetSource` (provider,
  model, prompt, licence) goes into ``art_sources.json`` beside the PNGs, to be
  set as the plane's or the prop's ``source`` so ``an credits`` can say where
  the picture came from.

Needs OpenCV for the key (``cutan[carve]``) and ``aix`` for the default
generator; nothing here is imported by ``import cutan``.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Optional, Union

import numpy as np
from PIL import Image

from an.ir.assets import AssetSource

#: The model :class:`AixGenerator` asks for when the spec names none.
DEFAULT_MODEL: str = "gpt-image-2"
DEFAULT_SIZE: str = "1536x1024"
#: ``None``: the provider's own default quality (``"high"`` is the dearest tier,
#: and not every model has it).
DEFAULT_QUALITY: Optional[str] = None
#: The licence code of OpenAI's image output, which its terms assign to the user.
#: ``an``'s licence classes do not know it yet (reeleehq/an#728), so ``an
#: credits`` reports it as unknown until they do.
OPENAI_OUTPUT_LICENSE: str = "openai-output-owned"
#: Where each generated image's provenance is written, beside the images.
SOURCES_FILE: str = "art_sources.json"
#: Named key colours, as the ``chroma`` matte's recipe: a hue band in degrees,
#: and only saturated, bright pixels in it. Magenta survives gpt-image's
#: anti-aliasing as roughly (246, 3, 242), hue 301; the band is narrow and the
#: floors high so orchid, lavender, deep pink and violet in the subject stay.
#: A subject in strong purple or magenta itself is keyed: keep those colours
#: out of art that uses the key (or key ``"green"``).
KEYS: dict[str, dict[str, Any]] = {
    "magenta": {
        "matte": "chroma",
        "hue": [280.0, 322.0],
        "min_sat": 0.5,
        "min_val": 0.4,
    },
    "green": {"matte": "chroma", "hue": [90.0, 150.0], "min_sat": 0.5, "min_val": 0.4},
}
#: What an art spec's ``prop`` may say: carve's ``point`` (the anchor: where a
#: hand holds it), ``keep``, ``detach`` and ``despill``, and ``write_prop``'s
#: ``landmarks`` (``{"grip": [x, y]}`` in the image's pixels) and ``max_side``.
_CARVE_KEYS: tuple[str, ...] = ("point", "keep", "detach", "despill")
_WRITE_KEYS: tuple[str, ...] = ("landmarks", "max_side")
PROP_KEYS: tuple[str, ...] = _CARVE_KEYS + _WRITE_KEYS
#: carve's ``keep`` values.
_KEEPS: tuple[str, ...] = ("point", "largest", "all")
_SIZE = re.compile(r"^([1-9]\d*x[1-9]\d*|auto)$")
#: An art name is a file name: no folder, no hidden file.
_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

Background = Literal["opaque", "transparent"]
#: ``generator(prompt, *, size, background, quality, model) -> PIL image`` (or a
#: :class:`Generated`: the image and what the provider said about it), with
#: ``provider``, ``model`` and ``license`` attributes for the provenance.
ImageGenerator = Callable[..., Image.Image]


@dataclass(frozen=True)
class ArtSpec:
    """One image to generate. ``key``: a :data:`KEYS` name or a matte recipe."""

    name: str
    prompt: str
    size: str = DEFAULT_SIZE
    background: Background = "opaque"
    key: Union[str, Mapping[str, Any], None] = None
    fit: Optional[tuple[int, int]] = None
    model: Optional[str] = None
    quality: Optional[str] = None
    #: Make a prop, not a plate (cutan#162): the image is carved
    #: (:func:`cutan.carve.carve`, its matte the ``key``, else carve's flat-colour
    #: default) and written as ``<name>/prop.json`` + ``parts/`` (``write_prop``),
    #: the source in the descriptor. Keys: :data:`PROP_KEYS`.
    prop: Optional[Mapping[str, Any]] = None

    def __post_init__(self):
        if not isinstance(self.name, str) or not _NAME.match(self.name):
            raise ValueError(
                f"art {self.name!r}: a name is a file name (letters, digits, . _ -)"
            )
        if not isinstance(self.prompt, str) or not self.prompt.strip():
            raise ValueError(f"art {self.name!r}: the prompt is empty (or not text)")
        if self.background not in ("opaque", "transparent"):
            raise ValueError(
                f"art {self.name!r}: background is 'opaque' or 'transparent', "
                f"not {self.background!r}"
            )
        if not isinstance(self.size, str) or not _SIZE.match(self.size):
            raise ValueError(
                f"art {self.name!r}: size is 'WxH' or 'auto', not {self.size!r}"
            )
        if self.fit is not None:
            if isinstance(self.fit, str) or len(self.fit) != 2:
                raise ValueError(f"art {self.name!r}: fit is [w, h], not {self.fit!r}")
            if not all(
                isinstance(x, int) and not isinstance(x, bool) for x in self.fit
            ):
                raise ValueError(
                    f"art {self.name!r}: fit is two whole numbers, not {self.fit!r}"
                )
            w, h = self.fit
            if w <= 0 or h <= 0:
                raise ValueError(
                    f"art {self.name!r}: fit must be positive, got {self.fit}"
                )
            object.__setattr__(self, "fit", (w, h))
        if self.prop is not None:
            if not isinstance(self.prop, Mapping) or set(self.prop) - set(PROP_KEYS):
                raise ValueError(
                    f"art {self.name!r}: prop is a mapping of {list(PROP_KEYS)}, not {self.prop!r}"
                )
            if self.fit is not None or self.background == "transparent":
                raise ValueError(
                    f"art {self.name!r}: a prop is carved from an opaque image by its key; "
                    "`fit` and `background: transparent` are for plates"
                )
            if problem := _prop_problem(self.prop, self.size):
                raise ValueError(f"art {self.name!r}: prop {problem}")
        if self.key is not None:
            from cutan.carve.mattes import as_matte

            try:  # a misspelt key fails here, before anything is paid for
                as_matte(_key_recipe(self.key))
            except (TypeError, ValueError) as e:
                raise ValueError(
                    f"art {self.name!r}: key {self.key!r} is neither one of "
                    f"{sorted(KEYS)} nor a matte recipe ({e})"
                ) from None


def _xy(value: Any) -> tuple[float, float] | None:
    """``value`` as two finite numbers, or ``None``."""
    if isinstance(value, (str, bytes, Mapping)) or not hasattr(value, "__len__") or len(value) != 2:
        return None
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in value):
        return None
    x, y = (float(v) for v in value)
    return (x, y) if np.isfinite(x) and np.isfinite(y) else None


def _prop_problem(prop: Mapping[str, Any], size: str) -> str | None:
    """Why a spec's ``prop`` would fail after the image is paid for, or ``None``.

    >>> _prop_problem({"point": [40, 48], "landmarks": {"grip": [1, 2]}}, "160x96") is None
    True
    >>> _prop_problem({"point": [900, 900]}, "160x96")
    'point (900.0, 900.0) is outside the 160x96 image'
    """
    from cutan.carve.prop import _LANDMARK_NAME

    w, h = (float(v) for v in size.split("x")) if "x" in size else (None, None)
    points = {}
    if "point" in prop:
        points["point"] = prop["point"]
    landmarks = prop.get("landmarks") or {}
    if not isinstance(landmarks, Mapping):
        return f"landmarks is {{name: [x, y]}}, not {landmarks!r}"
    for name, xy in landmarks.items():
        if not isinstance(name, str) or not _LANDMARK_NAME.fullmatch(name):
            return f"landmark name {name!r} is not a name (letters, digits, _ . -)"
        points[f"landmark {name!r}"] = xy
    for label, value in points.items():
        xy = _xy(value)
        if xy is None:
            return f"{label} is [x, y] in the image's pixels, not {value!r}"
        if w is not None and not (0 <= xy[0] <= w and 0 <= xy[1] <= h):
            return f"{label} {xy} is outside the {size} image"
    if "keep" in prop and prop["keep"] not in _KEEPS:
        return f"keep is one of {list(_KEEPS)}, not {prop['keep']!r}"
    for key in ("detach", "despill", "max_side"):
        value = prop.get(key)
        if value is not None and (
            isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0
            or (key == "max_side" and value == 0)
        ):
            return f"{key} is a number >= 0 (max_side > 0), not {value!r}"
    return None


def _key_recipe(key: Union[str, Mapping[str, Any], Any]) -> Any:
    return KEYS.get(key, key) if isinstance(key, str) else key


def art_specs(spec: Union[str, Path, Mapping[str, Mapping[str, Any]]]) -> list[ArtSpec]:
    """The :class:`ArtSpec` list of a spec mapping or a JSON file of one.

    ``key_magenta: true`` (the spec shape the first production wrote) means
    ``key: "magenta"``.

    >>> [(s.name, s.key, s.fit) for s in art_specs(
    ...     {"road": {"prompt": "a road", "fit": [1280, 720]},
    ...      "cabin": {"prompt": "a cabin", "key_magenta": True}})]
    [('road', None, (1280, 720)), ('cabin', 'magenta', None)]
    """
    if isinstance(spec, (str, Path)):
        spec = json.loads(Path(spec).read_text(encoding="utf-8"))
    if not isinstance(spec, Mapping):
        raise ValueError(
            f"an art spec is a mapping {{name: {{prompt, ...}}}}, not {type(spec).__name__}"
        )
    out = []
    for name, entry in spec.items():
        if not isinstance(entry, Mapping):
            raise ValueError(
                f"art {name!r}: an entry is a mapping {{prompt, ...}}, not {entry!r}"
            )
        entry = dict(entry)
        if entry.pop("key_magenta", False):
            entry.setdefault("key", "magenta")
        try:
            out.append(ArtSpec(name=name, **entry))
        except TypeError as e:
            raise ValueError(f"art {name!r}: {e}") from None
    return out


#: Bare model names (no ``provider/`` prefix) that LiteLLM routes to OpenAI.
OPENAI_IMAGE_MODELS: tuple[str, ...] = ("gpt-image", "dall-e")


def provider_of(model: str) -> Optional[str]:
    """The provider of a LiteLLM model name, by LiteLLM's own convention (a
    ``provider/`` prefix; OpenAI's image models go bare), without the network
    lookup LiteLLM's resolver makes; ``None`` when the name does not say.

    >>> provider_of("gpt-image-2"), provider_of("gemini/imagen-4"), provider_of("flux")
    ('openai', 'gemini', None)
    """
    if "/" in model:
        return model.split("/", 1)[0]
    return "openai" if model.startswith(OPENAI_IMAGE_MODELS) else None


#: The licence code of each provider's terms for its image output, by the
#: provider ``aix`` infers from the model. A provider not listed is recorded
#: with no licence: unknown, which ``an credits`` says aloud.
PROVIDER_LICENSES: dict[str, str] = {"openai": OPENAI_OUTPUT_LICENSE}


@dataclass
class Generated:
    """What a generator may return instead of a bare image: the image, and what
    the provider said about making it (``model`` it resolved to,
    ``revised_prompt`` it actually drew), recorded in the image's source."""

    image: Image.Image
    facts: Mapping[str, Any] = field(default_factory=dict)


def _generated(result: Any) -> Generated:
    """A generator's return value as :class:`Generated` (a bare image has no facts)."""
    return result if isinstance(result, Generated) else Generated(result)


@dataclass
class AixGenerator:
    """The default generator: :func:`aix.generate_image`, whose model names its
    provider (OpenAI's ``gpt-image`` by default). :meth:`describe` says which
    provider made an image and under what licence (:data:`PROVIDER_LICENSES`)."""

    model: str = DEFAULT_MODEL
    quality: Optional[str] = DEFAULT_QUALITY
    licenses: Mapping[str, str] = field(default_factory=lambda: dict(PROVIDER_LICENSES))

    def describe(self, model: Optional[str] = None) -> dict[str, Any]:
        """``{"provider", "license"}`` of an image made with ``model``.

        >>> AixGenerator().describe("gpt-image-2")
        {'provider': 'openai', 'license': 'openai-output-owned'}
        >>> AixGenerator().describe("gemini/imagen-4.0-generate-001")
        {'provider': 'gemini', 'license': None}
        """
        provider = provider_of(model or self.model)
        provider = provider or "unknown"
        return {"provider": provider, "license": self.licenses.get(provider)}

    def __call__(
        self,
        prompt: str,
        *,
        size: str,
        background: Background,
        quality: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Generated:
        try:
            import aix
        except ImportError as e:  # pragma: no cover - depends on the install
            raise ImportError(
                'the default art generator needs aix: pip install "cutan[generate]"'
            ) from e
        made = aix.generate_image(
            prompt,
            model=model or self.model,
            size=size,
            background=background,
            # gpt-image answers in base64 and refuses the parameter (thorwhalen/aix#66)
            response_format=None,
            **({"quality": q} if (q := quality or self.quality) else {}),
        )
        facts = {
            "model": getattr(made, "model", None),
            "revised_prompt": getattr(made, "revised_prompt", None),
        }
        return Generated(
            Image.open(io.BytesIO(made.as_bytes())),
            {k: v for k, v in facts.items() if v},
        )


def key_backdrop(
    image: Image.Image, key: Union[str, Mapping[str, Any], Any]
) -> Image.Image:
    """``image`` with its key colour keyed to alpha and the rim de-spilled, by
    :mod:`cutan.carve`'s matte (``key``: a :data:`KEYS` name or a matte recipe).
    An alpha the image already has is kept where it is lower.
    """
    from cutan.carve.core import DESPILL
    from cutan.carve.mattes import Hint, as_matte
    from cutan.carve.refine import despill

    matte = as_matte(_key_recipe(key))
    rgba = np.asarray(image.convert("RGBA"))
    rgb = np.ascontiguousarray(rgba[..., :3])
    alpha = np.minimum(
        np.clip(matte(rgb, Hint()), 0.0, 1.0), rgba[..., 3].astype(np.float32) / 255
    )
    rgb, _ = despill(rgb, alpha, DESPILL)
    a8 = np.round(alpha * 255).astype(np.uint8)
    return Image.fromarray(np.dstack([rgb, a8]), "RGBA")


def cover_fit(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Scale ``image`` to cover ``size`` (w, h), then centre-crop to it.

    >>> cover_fit(Image.new("RGB", (300, 100)), (100, 100)).size
    (100, 100)
    """
    w, h = size
    if image.mode not in ("RGB", "RGBA"):  # a palette image would resize by nearest
        image = image.convert("RGBA")
    s = max(w / image.width, h / image.height)
    scaled = image.resize(
        (max(w, round(image.width * s)), max(h, round(image.height * s))),
        Image.LANCZOS,
    )
    left, top = (scaled.width - w) // 2, (scaled.height - h) // 2
    return scaled.crop((left, top, left + w, top + h))


def art_source(
    spec: ArtSpec, generator: ImageGenerator, facts: Optional[Mapping[str, Any]] = None
) -> AssetSource:
    """The provenance of ``spec``'s image as ``generator`` made it; ``facts`` are
    what the provider said about this image (:class:`Generated`): the model it
    resolved to wins over the one asked for, and a ``revised_prompt`` is kept.

    >>> g = AixGenerator()
    >>> s = art_source(ArtSpec(name="road", prompt="a road"), g)
    >>> s.provider, s.id, s.license, s.extra["prompt"]
    ('openai', 'gpt-image-2', 'openai-output-owned', 'a road')
    """
    facts = dict(facts or {})
    model = facts.get("model") or spec.model or getattr(generator, "model", None)
    describe = getattr(generator, "describe", None)
    who = (
        describe(model)
        if describe
        else {
            "provider": getattr(generator, "provider", None),
            "license": getattr(generator, "license", None),
        }
    )
    quality = spec.quality or getattr(generator, "quality", None)
    return AssetSource(
        provider=who.get("provider") or "generated",
        id=model,
        license=who.get("license"),
        extra={
            "prompt": spec.prompt,
            "model": model,
            "size": spec.size,
            "background": spec.background,
            **({"quality": quality} if quality else {}),
            **({"key": spec.key} if spec.key else {}),
            **({"revised_prompt": facts["revised_prompt"]} if facts.get("revised_prompt") else {}),
        },
    )


@dataclass
class GeneratedArt:
    """One image of the spec: its path and provenance; ``kept`` when it was
    already there and not made again (its provenance read from the record)."""

    name: str
    path: Path
    source: Optional[AssetSource]
    size: tuple[int, int] = (0, 0)
    kept: bool = False
    #: A carved prop's quality warnings (:class:`cutan.carve.CarveQuality`).
    warnings: tuple[str, ...] = ()


def generate_art(
    spec: Union[str, Path, Mapping[str, Mapping[str, Any]], Iterable[ArtSpec]],
    *,
    out_dir: Union[str, Path],
    generator: Optional[ImageGenerator] = None,
    only: Optional[Iterable[str]] = None,
    keep_raw: bool = False,
    overwrite: bool = False,
) -> list[GeneratedArt]:
    """Generate, key, fit and write each image of ``spec`` into ``out_dir``.

    Each image is ``<name>.png``; ``art_sources.json`` (:data:`SOURCES_FILE`)
    maps each file to its provenance (with the PNG's sha256), merged with what
    the folder holds and written after every image. ``only``: the names to make
    (default all). An existing ``<name>.png`` is kept, not paid for again,
    unless ``overwrite``, so a batch that failed half way is resumed by running
    it again. The model's own image is written first as ``<name>.raw.png``, with
    its record, and removed once the PNG and its record are written, unless
    ``keep_raw``: a key or fit that fails leaves the paid-for image, and the
    next run keys that image instead of paying for a new one. Every file is
    written whole or not at all (a prop's files by ``write_prop``, in place: a
    ``prop.json`` a crash cut off is not taken as made, and is made again).
    """
    specs = art_specs(spec) if isinstance(spec, (str, Path, Mapping)) else list(spec)
    wanted = set(only) if only is not None else None
    if wanted is not None and (unknown := wanted - {s.name for s in specs}):
        raise ValueError(f"no such art in the spec: {sorted(unknown)}")
    specs = [s for s in specs if wanted is None or s.name in wanted]
    if any(s.key for s in specs):
        from cutan.carve._deps import cv2

        cv2()  # the key needs OpenCV: say so before anything is paid for
        probe = Image.new("RGB", (2, 2), (246, 3, 242))
        for s in specs:
            if s.key:
                try:  # a malformed recipe fails here, not after the payment
                    key_backdrop(probe, s.key)
                except Exception as e:  # noqa: BLE001 - any failure of the key is the spec's
                    raise ValueError(
                        f"art {s.name!r}: key {s.key!r} does not key: {e}"
                    ) from None
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    generator = generator or AixGenerator()
    recorded = _read_sources(out)
    made = []
    for s in specs:
        raw = out / f"{s.name}.raw.png"
        path = out / s.name / "prop.json" if s.prop is not None else out / f"{s.name}.png"
        entry = path.relative_to(out).as_posix()
        if _made(path, prop=s.prop is not None) and not overwrite:
            known = recorded.get(entry)
            made.append(
                GeneratedArt(
                    s.name,
                    path,
                    _source(known),
                    _image_size(path) if s.prop is None else _prop_size(path),
                    kept=True,
                )
            )
            continue
        if raw.exists() and not overwrite:
            image = Image.open(raw)  # paid for by a run that failed after it
            image.load()
        else:
            drawn = _generated(
                generator(
                    s.prompt,
                    size=s.size,
                    background=s.background,
                    quality=s.quality,
                    model=s.model,
                )
            )
            image = drawn.image
            _save(image, raw)
            # record it now: the paid image has its provenance even if what follows fails
            recorded[entry] = art_source(s, generator, drawn.facts).model_dump(
                mode="json", exclude_none=True
            )
            _write_sources(out, recorded)
        source = _source(recorded.get(entry)) or art_source(s, generator)
        if s.prop is not None:
            made.append(_write_generated_prop(s, image, out, source))
            source = source.model_copy(
                update={"sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            )
            recorded[entry] = source.model_dump(mode="json", exclude_none=True)
            _write_sources(out, recorded)
            if not keep_raw:
                raw.unlink()
            continue
        if s.key:
            image = key_backdrop(image, s.key)
        if s.fit:
            image = cover_fit(image, s.fit)
        _save(image, path)
        source = source.model_copy(
            update={"sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        )
        recorded[entry] = source.model_dump(mode="json", exclude_none=True)
        _write_sources(out, recorded)  # the record first, then the raw goes
        if not keep_raw:
            raw.unlink()
        made.append(GeneratedArt(s.name, path, source, image.size))
    return made


def _save(image: Image.Image, path: Path) -> None:
    """Write ``path`` whole or not at all: a crash never leaves half a PNG to be kept."""
    tmp = path.with_name(path.name + ".part")
    image.save(tmp, format="PNG")
    os.replace(tmp, path)


def _source(entry: Any) -> Optional[AssetSource]:
    if not isinstance(entry, Mapping):
        return None
    try:
        return AssetSource.model_validate(entry)
    except ValueError:
        return None


def _made(path: Path, *, prop: bool) -> bool:
    """Whether ``path`` is a finished image or prop: a ``prop.json`` cut off by a
    crash (``write_prop`` writes it in place) is not, and is made again."""
    if not path.exists():
        return False
    if not prop:
        return True
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("kind") == "PropDescriptor"
    except (OSError, ValueError, AttributeError):
        return False


def _prop_size(path: Path) -> tuple[int, int]:
    """A written prop's size, from its descriptor's ``view_box``."""
    try:
        box = json.loads(path.read_text(encoding="utf-8")).get("view_box") or (0, 0, 0, 0)
        return (int(round(box[2])), int(round(box[3])))
    except (OSError, ValueError, TypeError, IndexError, AttributeError):
        return (0, 0)


def _write_generated_prop(
    spec: ArtSpec, image: Image.Image, out: Path, source: AssetSource
) -> GeneratedArt:
    """Carve ``image`` by the spec's key and write it as a prop (cutan#162),
    over a prop a crash left unfinished."""
    import warnings

    from cutan.carve import carve, write_prop

    prop = dict(spec.prop or {})
    carving = carve(
        np.asarray(image.convert("RGB")),
        matte=_key_recipe(spec.key) if spec.key else "flat_colour",
        source=source,
        **{k: (tuple(v) if k == "point" else v) for k, v in prop.items() if k in _CARVE_KEYS},
    )
    folder = out / spec.name
    with warnings.catch_warnings(record=True) as said:  # write_prop warns on a far landmark
        warnings.simplefilter("always")
        write_prop(
            carving,
            folder,
            name=spec.name,
            landmarks={k: tuple(v) for k, v in (prop.get("landmarks") or {}).items()} or None,
            max_side=prop.get("max_side"),
            overwrite=True,  # generate_art decided: nothing finished is there
        )
    return GeneratedArt(
        spec.name,
        folder / "prop.json",
        source,
        carving.size,
        warnings=tuple(carving.quality.warnings()) + tuple(str(w.message) for w in said),
    )


def _image_size(path: Path) -> tuple[int, int]:
    with Image.open(path) as im:
        return im.size


def _read_sources(out: Path) -> dict[str, Any]:
    record = out / SOURCES_FILE
    if not record.exists():
        return {}
    try:
        sources = json.loads(record.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise ValueError(
            f"{record} cannot be read as JSON ({e}): fix or move it"
        ) from None
    if not isinstance(sources, dict):
        raise ValueError(
            f"{record} holds {type(sources).__name__}, not {{file: source}}"
        )
    return sources


def _write_sources(out: Path, sources: Mapping[str, Any]) -> None:
    record = out / SOURCES_FILE
    tmp = record.with_name(record.name + ".part")
    tmp.write_text(
        json.dumps(sources, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(tmp, record)
