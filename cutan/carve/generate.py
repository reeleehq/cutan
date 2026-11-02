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
  cover and centre-crop.
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
_SIZE = re.compile(r"^(\d+x\d+|auto)$")

Background = Literal["opaque", "transparent"]
#: ``generator(prompt, *, size, background, quality, model) -> PIL image``, with
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

    def __post_init__(self):
        if not self.prompt or not self.prompt.strip():
            raise ValueError(f"art {self.name!r}: the prompt is empty")
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
            w, h = (int(x) for x in self.fit)
            if w <= 0 or h <= 0:
                raise ValueError(
                    f"art {self.name!r}: fit must be positive, got {self.fit}"
                )
            object.__setattr__(self, "fit", (w, h))
        if self.key is not None:
            from cutan.carve.mattes import as_matte

            try:  # a misspelt key fails here, before anything is paid for
                as_matte(_key_recipe(self.key))
            except (TypeError, ValueError) as e:
                raise ValueError(
                    f"art {self.name!r}: key {self.key!r} is neither one of "
                    f"{sorted(KEYS)} nor a matte recipe ({e})"
                ) from None


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
    ) -> Image.Image:
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
        return Image.open(io.BytesIO(made.as_bytes()))


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


def art_source(spec: ArtSpec, generator: ImageGenerator) -> AssetSource:
    """The provenance of ``spec``'s image as ``generator`` made it.

    >>> g = AixGenerator()
    >>> s = art_source(ArtSpec(name="road", prompt="a road"), g)
    >>> s.provider, s.id, s.license, s.extra["prompt"]
    ('openai', 'gpt-image-2', 'openai-output-owned', 'a road')
    """
    model = spec.model or getattr(generator, "model", None)
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
    it again. The model's own image is written first as ``<name>.raw.png`` and
    removed once the PNG is written, unless ``keep_raw``: a key or fit that
    fails leaves the paid-for image on disk.
    """
    specs = art_specs(spec) if isinstance(spec, (str, Path, Mapping)) else list(spec)
    wanted = set(only) if only is not None else None
    if wanted is not None and (unknown := wanted - {s.name for s in specs}):
        raise ValueError(f"no such art in the spec: {sorted(unknown)}")
    specs = [s for s in specs if wanted is None or s.name in wanted]
    if any(s.key for s in specs):
        from cutan.carve._deps import cv2

        cv2()  # the key needs OpenCV: say so before anything is paid for
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    generator = generator or AixGenerator()
    recorded = _read_sources(out)
    made = []
    for s in specs:
        path = out / f"{s.name}.png"
        if path.exists() and not overwrite:
            known = recorded.get(path.name)
            made.append(
                GeneratedArt(
                    s.name,
                    path,
                    AssetSource.model_validate(known) if known else None,
                    _image_size(path),
                    kept=True,
                )
            )
            continue
        image = generator(
            s.prompt,
            size=s.size,
            background=s.background,
            quality=s.quality,
            model=s.model,
        )
        raw = out / f"{s.name}.raw.png"
        image.save(raw)
        if s.key:
            image = key_backdrop(image, s.key)
        if s.fit:
            image = cover_fit(image, s.fit)
        image.save(path)
        if not keep_raw:
            raw.unlink()
        source = art_source(s, generator).model_copy(
            update={"sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        )
        made.append(GeneratedArt(s.name, path, source, image.size))
        recorded[path.name] = source.model_dump(mode="json", exclude_none=True)
        _write_sources(out, recorded)  # each image is billed: record it at once
    return made


def _image_size(path: Path) -> tuple[int, int]:
    with Image.open(path) as im:
        return im.size


def _read_sources(out: Path) -> dict[str, Any]:
    record = out / SOURCES_FILE
    return json.loads(record.read_text(encoding="utf-8")) if record.exists() else {}


def _write_sources(out: Path, sources: Mapping[str, Any]) -> None:
    (out / SOURCES_FILE).write_text(
        json.dumps(sources, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
