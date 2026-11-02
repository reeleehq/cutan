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

import io
import json
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
DEFAULT_QUALITY: str = "high"
#: The licence code of OpenAI's image output, which its terms assign to the user.
#: ``an``'s licence classes do not know it yet (reeleehq/an#728), so ``an
#: credits`` reports it as unknown until they do.
OPENAI_OUTPUT_LICENSE: str = "openai-output-owned"
#: Where each generated image's provenance is written, beside the images.
SOURCES_FILE: str = "art_sources.json"
#: Named key colours, as the ``chroma`` matte's recipe: a hue band in degrees.
#: Magenta survives gpt-image's anti-aliasing as roughly (246, 3, 242), hue 301.
KEYS: dict[str, dict[str, Any]] = {
    "magenta": {"matte": "chroma", "hue": [270.0, 330.0]},
    "green": {"matte": "chroma", "hue": [90.0, 150.0]},
}

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
        if self.fit is not None:
            w, h = self.fit
            if int(w) <= 0 or int(h) <= 0:
                raise ValueError(f"art {self.name!r}: fit must be positive, got {self.fit}")
            object.__setattr__(self, "fit", (int(w), int(h)))


def art_specs(spec: Union[str, Path, Mapping[str, Mapping[str, Any]]]) -> list[ArtSpec]:
    """The :class:`ArtSpec` list of a spec mapping or a JSON file of one.

    ``key_magenta: true`` (the spec shape the first production wrote) means
    ``key: "magenta"``.

    >>> [(s.name, s.key, s.fit) for s in art_specs(
    ...     {"road": {"prompt": "a road", "fit": [1280, 720]},
    ...      "cabin": {"prompt": "a cabin", "key_magenta": True}})]
    [('road', None, (1280, 720)), ('cabin', 'magenta', None)]
    """
    if not isinstance(spec, Mapping):
        spec = json.loads(Path(spec).read_text(encoding="utf-8"))
    out = []
    for name, entry in spec.items():
        entry = dict(entry)
        if entry.pop("key_magenta", False):
            entry.setdefault("key", "magenta")
        fit = entry.pop("fit", None)
        try:
            out.append(ArtSpec(name=name, fit=tuple(fit) if fit else None, **entry))
        except TypeError as e:
            raise ValueError(f"art {name!r}: {e}") from None
    return out


@dataclass
class AixGenerator:
    """The default generator: :func:`aix.generate_image`, whose model names its
    provider (OpenAI's ``gpt-image`` by default). The licence is the provider's
    terms for its output: change it with the provider."""

    model: str = DEFAULT_MODEL
    quality: str = DEFAULT_QUALITY
    provider: str = "openai"
    license: Optional[str] = OPENAI_OUTPUT_LICENSE

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
            quality=quality or self.quality,
            background=background,
            # gpt-image answers in base64 and refuses the parameter
            response_format=None,
        )
        return Image.open(io.BytesIO(made.as_bytes()))


def key_backdrop(image: Image.Image, key: Union[str, Mapping[str, Any], Any]) -> Image.Image:
    """``image`` with its key colour keyed to alpha and the rim de-spilled, by
    :mod:`cutan.carve`'s matte (``key``: a :data:`KEYS` name or a matte recipe).
    An alpha the image already has is kept where it is lower.
    """
    from cutan.carve.core import DESPILL
    from cutan.carve.mattes import Hint, as_matte
    from cutan.carve.refine import despill

    matte = as_matte(KEYS.get(key, key) if isinstance(key, str) else key)
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
    return AssetSource(
        provider=getattr(generator, "provider", None) or "generated",
        id=model,
        license=getattr(generator, "license", None),
        extra={
            "prompt": spec.prompt,
            "model": model,
            "size": spec.size,
            "background": spec.background,
            **({"key": spec.key} if spec.key else {}),
        },
    )


@dataclass
class GeneratedArt:
    """One written image: its path and its provenance."""

    name: str
    path: Path
    source: AssetSource
    size: tuple[int, int] = field(default=(0, 0))


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
    maps each file to its provenance, merged with what the folder holds.
    ``only``: the names to make (default all); ``keep_raw``: also write the
    model's image as ``<name>.raw.png``; an existing ``<name>.png`` is refused
    unless ``overwrite`` (a generation is billed and not repeatable).
    """
    specs = (
        art_specs(spec)
        if isinstance(spec, (str, Path, Mapping))
        else list(spec)
    )
    wanted = set(only) if only is not None else None
    if wanted is not None and (unknown := wanted - {s.name for s in specs}):
        raise ValueError(f"no such art in the spec: {sorted(unknown)}")
    specs = [s for s in specs if wanted is None or s.name in wanted]
    out = Path(out_dir)
    if not overwrite and (
        clash := [s.name for s in specs if (out / f"{s.name}.png").exists()]
    ):
        raise FileExistsError(
            f"already in {out}: {clash} (overwrite=True to make them again)"
        )
    generator = generator or AixGenerator()
    out.mkdir(parents=True, exist_ok=True)
    made = []
    for s in specs:
        image = generator(
            s.prompt, size=s.size, background=s.background, quality=s.quality, model=s.model
        )
        if keep_raw:
            image.save(out / f"{s.name}.raw.png")
        if s.key:
            image = key_backdrop(image, s.key)
        if s.fit:
            image = cover_fit(image, s.fit)
        path = out / f"{s.name}.png"
        image.save(path)
        made.append(GeneratedArt(s.name, path, art_source(s, generator), image.size))
        _record_sources(out, made[-1:])  # each image is billed: record it at once
    return made


def _record_sources(out: Path, made: list[GeneratedArt]) -> None:
    record = out / SOURCES_FILE
    sources = json.loads(record.read_text(encoding="utf-8")) if record.exists() else {}
    for art in made:
        sources[art.path.name] = art.source.model_dump(mode="json", exclude_none=True)
    record.write_text(json.dumps(sources, indent=2, sort_keys=True) + "\n", encoding="utf-8")
