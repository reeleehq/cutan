"""Clothing prints for the factory's figures (cutan#94): an SVG ``<pattern>`` over the clothing fill.

A flat ``clothing`` colour cannot show a loud holiday shirt, a striped jumper or a
check suit. A :class:`ClothingPattern` names a print (``stripes``, ``check``,
``floral``), its colours and its scale; the factory draws it as a ``<pattern>``
definition plus one overlay rect in every clothing part — the torso (front and
each view) and the arm sleeves — on top of the base fill and under the outline.
The base fill keeps its ``clothing`` colour role, so a style pack still
recolours it; the print's own literals carry no role and are made distinct from
the part's role literals, so a swap never catches them. The swap channels and
the rig contract are untouched: a print is paint, not geometry.

``tile`` is a print you draw yourself: a small PNG (:data:`MAX_TILE_SIDE` px a side,
:data:`MAX_TILE_BYTES` bytes), one pixel per rect. It is vectors on purpose: the
core refuses an ``<image>`` inside a part's SVG (an#211: it hides its pixels from
every check), and the tile's bytes live in the recorded spec as base64, so the
factory's recipe replays it on any machine (a file path could not be replayed).
:func:`read_tile` turns a file into that base64.

A spec is one string on the command line or one mapping in the descriptor::

    floral:base=#e8735a,motif=#ffffff,leaf=#2f6b3a
    tile:image=<base64 of a small PNG>,base=#345678
    stripes
    check:scale=0.7
    none

>>> p = parse_clothing_pattern("floral:base=#e8735a,motif=#fff")
>>> p.kind, p.base, p.motif, p.leaf, p.scale
('floral', '#e8735a', '#ffffff', '#2f6b3a', 1.0)
>>> parse_clothing_pattern("none") is None and parse_clothing_pattern(None) is None
True
>>> parse_clothing_pattern({"kind": "stripes", "scale": 0.5}).as_dict()
{'kind': 'stripes', 'scale': 0.5}
"""

from __future__ import annotations

import base64
import binascii
import io
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Mapping, Optional, Union

from cutan.characters.colour_roles import distinct_literal, normalise_hex

__all__ = [
    "ClothingPattern",
    "PATTERN_KINDS",
    "PATTERN_ID",
    "parse_clothing_pattern",
    "pattern_defs",
    "pattern_overlay",
    "painted_fill",
    "distinct_pattern",
    "read_tile",
    "resolve_tile_paths",
    "MAX_TILE_SIDE",
    "MAX_TILE_BYTES",
]

#: The prints the factory draws; ``none`` is the flat default.
PATTERN_KINDS: tuple[str, ...] = ("none", "stripes", "check", "floral", "tile")
#: The print drawn from the caller's own PNG tile.
TILE_KIND = "tile"
#: A tile's limits: its PNG's bytes (they sit in the recipe, which is bounded) and its side.
MAX_TILE_BYTES: int = 3_072
MAX_TILE_SIDE: int = 32
#: The first characters of any base64 PNG: how a path is told from inline bytes.
_PNG_B64 = "iVBORw0KGgo"
#: The id of the ``<pattern>`` element in a part, referenced by its overlay.
PATTERN_ID: str = "clothing_print"
#: The tile's side in a part's own units at ``scale`` 1: about seven across the
#: regular torso, one across a sleeve, so a print reads on both.
PATTERN_TILE: float = 40.0
#: The print's default colours: an off-white motif, a leaf green.
DFLT_MOTIF: str = "#f4f1ea"
DFLT_LEAF: str = "#2f6b3a"
#: The parameters a spec may name, per kind (``base`` sets the clothing colour).
_PARAMS: dict[str, tuple[str, ...]] = {
    "stripes": ("base", "motif", "scale"),
    "check": ("base", "motif", "scale"),
    "floral": ("base", "motif", "leaf", "scale"),
    TILE_KIND: ("base", "image", "scale"),
}
_MIN_SCALE, _MAX_SCALE = 0.25, 4.0


@dataclass(frozen=True)
class ClothingPattern:
    """One print: its kind, its colours and its scale."""

    kind: str
    base: Optional[str] = None
    motif: str = DFLT_MOTIF
    leaf: str = DFLT_LEAF
    scale: float = 1.0
    #: ``tile``: the PNG, base64 (what the descriptor records).
    image: Optional[str] = field(default=None, repr=False)
    #: ``tile``: drawn colour per colour of the image, set by :func:`distinct_pattern`.
    palette: tuple = field(default=(), compare=False, repr=False)

    def as_dict(self) -> dict:
        """The spec as a mapping, defaults left out: what the descriptor records."""
        out: dict = {"kind": self.kind}
        if self.base is not None:
            out["base"] = self.base
        if self.motif != DFLT_MOTIF:
            out["motif"] = self.motif
        if self.kind == "floral" and self.leaf != DFLT_LEAF:
            out["leaf"] = self.leaf
        if self.image is not None:
            out["image"] = self.image
        if self.scale != 1.0:
            out["scale"] = self.scale
        return out

    @property
    def tile(self) -> float:
        return PATTERN_TILE * self.scale


def _tile_png(data: bytes):
    """The tile's pixels as an RGBA image, or ``ValueError`` saying why not."""
    from PIL import Image

    if len(data) > MAX_TILE_BYTES:
        raise ValueError(
            f"a clothing tile is at most {MAX_TILE_BYTES} bytes; this is {len(data)}"
        )
    try:
        img = Image.open(io.BytesIO(data))
        if img.format != "PNG":
            raise ValueError("not a PNG")
        img.load()
    except Exception as e:  # noqa: BLE001 - any decoder failure is "not a usable tile"
        raise ValueError(f"a clothing tile must be a PNG: {e}") from None
    if max(img.size) > MAX_TILE_SIDE:
        raise ValueError(
            f"a clothing tile is at most {MAX_TILE_SIDE} px a side; this is {img.size[0]}x{img.size[1]}"
        )
    return img.convert("RGBA")


def read_tile(path: Union[str, Path]) -> str:
    """A tile PNG file as the base64 a ``tile`` spec carries (checked on the way).

    >>> import tempfile, pathlib
    >>> from PIL import Image
    >>> with tempfile.TemporaryDirectory() as d:
    ...     Image.new("RGBA", (2, 2), (200, 30, 30, 255)).save(pathlib.Path(d) / "t.png")
    ...     tile = read_tile(pathlib.Path(d) / "t.png")
    >>> tile.startswith("iVBORw0KGgo") and parse_clothing_pattern({"kind": "tile", "image": tile}).kind
    'tile'
    """
    try:
        data = Path(path).read_bytes()
    except OSError as e:
        raise ValueError(f"clothing tile {str(path)!r} cannot be read: {e.strerror or e}") from None
    _tile_png(data)
    return base64.b64encode(data).decode("ascii")


def resolve_tile_paths(spec: Union[str, Mapping, None]) -> Union[str, Mapping, None]:
    """``spec`` with a file given as ``image=`` read into its base64, so the spec
    that is recorded (and replayed elsewhere) holds the bytes, not a path.

    >>> resolve_tile_paths("stripes")
    'stripes'
    >>> resolve_tile_paths({"kind": "tile", "image": "iVBORw0KGgoAAAA"})["image"]
    'iVBORw0KGgoAAAA'
    """
    def one(value: object) -> object:
        text = str(value)
        return value if text.startswith(_PNG_B64) else read_tile(text)

    if isinstance(spec, Mapping):
        return {**spec, "image": one(spec["image"])} if "image" in spec else spec
    if not isinstance(spec, str) or "image=" not in spec:
        return spec
    kind, sep, rest = spec.partition(":")
    items = []
    for item in rest.split(","):
        key, eq, value = item.partition("=")
        items.append(f"{key}={one(value.strip())}" if key.strip() == "image" and eq else item)
    return kind + sep + ",".join(items)


def _image(value: object) -> str:
    try:
        data = base64.b64decode(str(value), validate=True)
    except (binascii.Error, ValueError):
        raise ValueError(
            "clothing pattern image= is the base64 of a PNG (read_tile(path) makes it)"
        ) from None
    _tile_png(data)
    return base64.b64encode(data).decode("ascii")


def _colour(name: str, value: object) -> str:
    try:
        return normalise_hex(str(value))
    except ValueError:
        raise ValueError(
            f"clothing pattern {name}={value!r} is not a #rgb or #rrggbb colour"
        ) from None


def parse_clothing_pattern(
    spec: Union[str, Mapping, None],
) -> Optional[ClothingPattern]:
    """A :class:`ClothingPattern` from a spec string or mapping; ``None`` for no print.

    >>> parse_clothing_pattern("stripes:motif=#000")
    ClothingPattern(kind='stripes', base=None, motif='#000000', leaf='#2f6b3a', scale=1.0)
    >>> parse_clothing_pattern("plaid")
    Traceback (most recent call last):
    ...
    ValueError: unknown clothing pattern 'plaid'; known: none, stripes, check, floral, tile
    >>> parse_clothing_pattern("stripes:leaf=#000")
    Traceback (most recent call last):
    ...
    ValueError: clothing pattern 'stripes' takes base, motif, scale; not 'leaf'
    """
    if spec is None:
        return None
    if isinstance(spec, Mapping):
        params = {str(k): v for k, v in spec.items()}
        kind = str(params.pop("kind", "") or "none")
    else:
        text = str(spec).strip()
        if not text:
            return None
        kind, _, rest = text.partition(":")
        kind = kind.strip()
        params = {}
        for item in rest.split(","):
            if not item.strip():
                continue
            key, eq, value = item.partition("=")
            if not eq:
                raise ValueError(
                    f"clothing pattern parameter {item.strip()!r} is not key=value"
                )
            params[key.strip()] = value.strip()
    if kind not in PATTERN_KINDS:
        raise ValueError(
            f"unknown clothing pattern {kind!r}; known: {', '.join(PATTERN_KINDS)}"
        )
    if kind == "none":
        if params:
            raise ValueError("clothing pattern 'none' takes no parameter")
        return None
    allowed = _PARAMS[kind]
    for key in params:
        if key not in allowed:
            raise ValueError(
                f"clothing pattern {kind!r} takes {', '.join(allowed)}; not {key!r}"
            )
    if kind == TILE_KIND and "image" not in params:
        raise ValueError("clothing pattern 'tile' needs image= (a small PNG, base64)")
    scale = params.get("scale", 1.0)
    try:
        scale = float(scale)
    except (TypeError, ValueError):
        raise ValueError(f"clothing pattern scale={scale!r} is not a number") from None
    if not _MIN_SCALE <= scale <= _MAX_SCALE:
        raise ValueError(
            f"clothing pattern scale must be in [{_MIN_SCALE:g}, {_MAX_SCALE:g}]; got {scale:g}"
        )
    return ClothingPattern(
        kind=kind,
        base=_colour("base", params["base"]) if "base" in params else None,
        motif=_colour("motif", params["motif"]) if "motif" in params else DFLT_MOTIF,
        leaf=_colour("leaf", params["leaf"]) if "leaf" in params else DFLT_LEAF,
        scale=scale,
        image=_image(params["image"]) if kind == TILE_KIND else None,
    )


def _tile_runs(pattern: ClothingPattern):
    """``(x, y, run, hex, alpha)`` for each horizontal run of one colour in the tile."""
    img = _tile_png(base64.b64decode(pattern.image))
    w, h = img.size
    px = img.load()
    for y in range(h):
        x = 0
        while x < w:
            r, g, b, a = px[x, y]
            run = 1
            while x + run < w and px[x + run, y] == (r, g, b, a):
                run += 1
            if a:
                yield x, y, run, f"#{r:02x}{g:02x}{b:02x}", a
            x += run


def distinct_pattern(pattern: ClothingPattern, taken: set[str]) -> ClothingPattern:
    """The print with its literals nudged clear of ``taken`` (the part's role
    literals and its ink), so a role swap never rewrites the print.

    >>> distinct_pattern(ClothingPattern("stripes", motif="#ffffff"), {"#ffffff"}).motif
    '#fffffe'
    """
    if pattern.kind == TILE_KIND:
        used = set(taken)
        palette = {}
        for colour in sorted({c for *_, c, _ in _tile_runs(pattern)}):
            palette[colour] = distinct_literal(colour, used)
            used.add(palette[colour])
        return replace(pattern, palette=tuple(sorted(palette.items())))
    motif = distinct_literal(pattern.motif, taken)
    leaf = distinct_literal(pattern.leaf, taken | {motif})
    return replace(pattern, motif=motif, leaf=leaf)


def _tile_content(pattern: ClothingPattern) -> str:
    t = pattern.tile
    m = pattern.motif
    if pattern.kind == TILE_KIND:
        w, h = _tile_png(base64.b64decode(pattern.image)).size
        k = t / max(w, h)
        colours = dict(pattern.palette)
        return "".join(
            f'<rect x="{x * k:g}" y="{y * k:g}" width="{run * k:g}" height="{k:g}" '
            f'fill="{colours.get(c, c)}"'
            + (f' fill-opacity="{a / 255:.3f}"' if a < 255 else "")
            + ' shape-rendering="crispEdges"/>'
            for x, y, run, c, a in _tile_runs(pattern)
        )
    if pattern.kind == "stripes":
        return f'<rect x="0" y="0" width="{t:g}" height="{t / 2:g}" fill="{m}"/>'
    if pattern.kind == "check":
        h = t / 2
        return (
            f'<rect x="0" y="0" width="{h:g}" height="{h:g}" fill="{m}"/>'
            f'<rect x="{h:g}" y="{h:g}" width="{h:g}" height="{h:g}" fill="{m}"/>'
        )
    # floral: five petals round a centre, a leaf to its lower left
    cx = cy = t / 2
    petal, reach = t * 0.11, t * 0.16
    petals = "".join(
        f'<circle cx="{cx + reach * dx:g}" cy="{cy + reach * dy:g}" r="{petal:g}" fill="{m}"/>'
        for dx, dy in (
            (0, -1),
            (0.951, -0.309),
            (0.588, 0.809),
            (-0.588, 0.809),
            (-0.951, -0.309),
        )
    )
    centre = f'<circle cx="{cx:g}" cy="{cy:g}" r="{t * 0.06:g}" fill="{pattern.leaf}"/>'
    leaf = (
        f'<ellipse cx="{t * 0.18:g}" cy="{t * 0.82:g}" rx="{t * 0.13:g}" ry="{t * 0.055:g}" '
        f'fill="{pattern.leaf}" transform="rotate(-40 {t * 0.18:g} {t * 0.82:g})"/>'
    )
    return petals + centre + leaf


def pattern_defs(pattern: ClothingPattern) -> str:
    """The ``<defs><pattern>`` text a clothing part carries, in its own units.

    >>> 'patternUnits="userSpaceOnUse"' in pattern_defs(ClothingPattern("check"))
    True
    """
    t = pattern.tile
    return (
        f'<defs><pattern id="{PATTERN_ID}" patternUnits="userSpaceOnUse" '
        f'x="0" y="0" width="{t:g}" height="{t:g}">{_tile_content(pattern)}</pattern></defs>'
    )


def painted_fill(
    shape_attrs: str, *, fill: str, pattern: Optional[ClothingPattern]
) -> str:
    """A clothing shape's paint, without its outline: the base ``fill``, then the
    print over it (the definition, the fill, the overlay), the one order every
    clothing drawer shares; the caller adds its own ink on top.

    >>> painted_fill('x="0"', fill="#fff", pattern=None)
    '<rect x="0" fill="#fff"/>'
    >>> out = painted_fill('x="0"', fill="#fff", pattern=ClothingPattern("check"))
    >>> out.startswith("<defs>") and out.endswith('<rect x="0" fill="url(#clothing_print)"/>')
    True
    """
    base = f'<rect {shape_attrs} fill="{fill}"/>'
    if pattern is None:
        return base
    return pattern_defs(pattern) + base + pattern_overlay(shape_attrs)


def pattern_overlay(shape_attrs: str) -> str:
    """The overlay that paints the print over a clothing shape's base fill.

    ``shape_attrs`` is the shape's own geometry (a rect's ``x y width height rx ry``),
    so the print is clipped to the clothing exactly as the fill is.

    >>> pattern_overlay('x="0" y="0" width="4" height="4"')
    '<rect x="0" y="0" width="4" height="4" fill="url(#clothing_print)"/>'
    """
    return f'<rect {shape_attrs} fill="url(#{PATTERN_ID})"/>'
