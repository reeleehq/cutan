"""A reference sheet becomes an art package: carve each region, set it on the rig (cutan#128).

A character delivered as a reference sheet (front, three-quarter, side and back
views; a face sheet of mouth shapes) used to become a rig only by hand: carve each
view, cut the parts at the joints, point the descriptor at them, read every
quality warning. This is that recipe, as data over two components that exist:
:func:`~cutan.carve.carve` cuts a region of the sheet, and
:func:`~cutan.characters.set_part.set_part` draws a factory attachment with the
result. The rig (bones, slots, swap sets, the contract) is a factory character's
(``an character new``); the sheet supplies its drawings.

A recipe is a list of :class:`SheetPart`: an attachment's name, the region of the
sheet that holds it, and the ``carve`` arguments for it (the matte as its recipe,
so a recipe is JSON). Cutting at a joint is a polygon matte over the same sheet:
``{"matte": {"name": "polygon", ...}}`` composed with a key. A part whose carve
gives a ``point`` (a pixel on the subject) takes that point as the attachment's
anchor, so the joint a neck or a shoulder turns about is where the rig puts it.

>>> from cutan.carve.sheet import SheetPart
>>> SheetPart("head", crop=(0, 0, 100, 120), carve={"point": (50, 90)}).attachment
'head'

Every part is carved, and every attachment named, BEFORE the character is
touched, and a failure while setting the parts puts the character back as it
was, so a bad recipe changes nothing. Provenance is required, as for
:func:`~cutan.carve.write_prop`: the sheet's ``source`` (``frame_source``), or
``ours=True`` for pixels that are the caller's. The report carries each part's
quality warnings in words, for the writer to read before anything renders.

Moving parts that share one carving (a torso and its arms, a clock face and its
hands) are one :class:`SheetPart` with a ``split``: the region is carved once,
:func:`~cutan.carve.split_parts` lifts each named part at its mask with its pivot
as the attachment's anchor, and the part's own attachment draws what is left.

A picture is drawn at the width of the factory drawing it replaces, so parts from
one sheet would lose their relative scale. The recipe's ``unit`` (view-box units
per sheet pixel) declares each picture's width from its carved size instead: one
unit for the whole sheet, so a hand stays as long next to a body as on the sheet.
A part with no ``point`` keeps the factory's anchor, which belongs to a different
picture's framing (the report says so).

The recipe as a document is :func:`load_recipe` (``schema_version`` 1).

Needs OpenCV: ``pip install "cutan[carve]"``.
"""

from __future__ import annotations

import math
import shutil
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, NamedTuple

from an.ir.assets import AssetSource

from cutan.carve.core import Box, Carving, ImageLike, carve, carve_head, load_rgb
from cutan.carve.parts import PartSpec, split_parts
from cutan.carve.provenance import frame_source
from cutan.characters.set_part import PartReplacement, part_path, set_part

__all__ = [
    "RECIPE_SCHEMA_VERSION",
    "PartResult",
    "SheetPart",
    "Recipe",
    "SheetReport",
    "load_recipe",
    "sheet_to_package",
]

#: The recipe document's version, written as ``schema_version``.
RECIPE_SCHEMA_VERSION = 1
#: How a part is carved: ``carve`` (a region) or ``carve_head`` (a head on its fixed canvas).
_CARVERS = {"part": carve, "head": carve_head}
#: ``split_parts``' pad and inpaint radius, in carving px at scale 1 (it counts the carving's px).
_SPLIT_PAD, _SPLIT_INPAINT_RADIUS = 2, 4
#: carve arguments the function owns.
_OWNED = frozenset({"crop", "source"})
_NO_ANCHOR = (
    "no `point`: the attachment keeps the factory's anchor, which belongs to "
    "another picture's framing"
)


@dataclass(frozen=True)
class SheetPart:
    """One attachment and where on the sheet it is drawn.

    attachment: the attachment's name (``head``, ``mouth_a``), or ``slot/name``
    crop: ``(x0, y0, x1, y1)`` in the sheet's pixels, the region carved
        (``mode="part"``; a head is located by ``carve["face"]`` instead)
    carve: the other arguments of the carver (``matte``, ``point``, ``keep``,
        ``superres``...), JSON-able; a ``point`` anchors the part
    mode: ``"part"`` (:func:`~cutan.carve.carve`) or ``"head"``
        (:func:`~cutan.carve.carve_head`: neck cut, fixed canvas, face centre as anchor)
    split: ``{attachment: PartSpec or its dict}``: moving parts lifted off this
        carving (:func:`~cutan.carve.split_parts`; masks and pivots in the
        sheet's pixels). Each is drawn by its own attachment, anchored at its
        pivot; ``attachment`` above draws the base, what is left
    """

    attachment: str
    crop: Box | None = None
    carve: Mapping[str, Any] = field(default_factory=dict)
    mode: str = "part"
    split: Mapping[str, PartSpec | Mapping[str, Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.mode not in _CARVERS:
            raise ValueError(f"{self.attachment!r}: mode is one of {sorted(_CARVERS)}")
        if self.mode == "part" and self.crop is None:
            raise ValueError(f"{self.attachment!r}: a part needs its `crop`")
        if self.mode == "head" and self.crop is not None:
            raise ValueError(
                f"{self.attachment!r}: a head is found by carve['face'], not a crop"
            )
        if self.mode == "head" and "face" not in self.carve:
            raise ValueError(
                f"{self.attachment!r}: a head needs carve['face'] (a sheet has several faces)"
            )
        object.__setattr__(  # a typo in a spec fails here, before anything is carved
            self,
            "split",
            {
                n: sp if isinstance(sp, PartSpec) else PartSpec(**sp)
                for n, sp in self.split.items()
            },
        )
        if self.attachment in self.split:
            raise ValueError(
                f"{self.attachment!r}: the base and a split part cannot share a name"
            )
        if clash := _OWNED & set(self.carve):
            raise ValueError(
                f"{self.attachment!r}: {sorted(clash)} are not recipe arguments "
                "(the region is `crop`; the provenance is the sheet's)"
            )

    @property
    def anchored(self) -> bool:
        """Does the carve fix the anchor (a ``point``, or a head's face centre)?"""
        return self.mode == "head" or "point" in self.carve


@dataclass(frozen=True)
class PartResult:
    """What became of one part: the descriptor change and the quality warnings."""

    attachment: str
    warnings: list[str]
    replacement: PartReplacement


@dataclass(frozen=True)
class SheetReport:
    """The package built: one :class:`PartResult` per part, in recipe order."""

    parts: list[PartResult]

    @property
    def warnings(self) -> list[str]:
        """Every part's warnings, each led by its attachment's name."""
        return [f"{r.attachment}: {w}" for r in self.parts for w in r.warnings]

    @property
    def derived(self) -> list[str]:
        """Factory drawings derived from a replaced part (its views, lid states,
        mouth variants) still in use: they will not match the new picture."""
        return sorted({d for r in self.parts for d in r.replacement.derived})

    def format(self) -> str:
        lines = [f"{len(self.parts)} part(s) set from the sheet"]
        lines += [f"  warning: {w}" for w in self.warnings]
        if self.derived:
            lines.append(
                f"  still the factory's drawings, derived from them: {', '.join(self.derived)}"
            )
        return "\n".join(lines)


class Recipe(NamedTuple):
    """A recipe document read: ``sheet_to_package(sheet, **recipe._asdict(), ...)``."""

    parts: list[SheetPart]
    source: AssetSource | None
    ours: bool
    unit: float | None


def _check_unit(unit: Any) -> float | None:
    if unit is None:
        return None
    if isinstance(unit, bool) or not isinstance(unit, (int, float)):
        raise ValueError(f"unit {unit!r}: a number (view-box units per sheet pixel)")
    if not (math.isfinite(unit) and unit > 0):
        raise ValueError(
            f"unit {unit!r}: view-box units per sheet pixel, finite and positive"
        )
    return float(unit)


def load_recipe(doc: Mapping[str, Any]) -> Recipe:
    """The :class:`Recipe` of a recipe document.

    ``{"schema_version": 1, "source": {frame_source's arguments} | null,
    "ours": false, "unit": null, "parts": [{"attachment", "crop", "carve",
    "mode", "split"}]}``
    """
    if not isinstance(doc, Mapping) or "parts" not in doc:
        raise ValueError('a recipe is a JSON object with a "parts" list')
    version = doc.get(
        "schema_version", RECIPE_SCHEMA_VERSION
    )  # absent: the current one
    if version != RECIPE_SCHEMA_VERSION:
        raise ValueError(
            f"recipe schema_version {version!r}; this reads {RECIPE_SCHEMA_VERSION}"
        )
    source = frame_source(**doc["source"]) if doc.get("source") else None
    parts = [SheetPart(**p) for p in doc["parts"]]
    return Recipe(parts, source, bool(doc.get("ours")), _check_unit(doc.get("unit")))


def _snapshot(char_dir: Path, into: Path) -> Path:
    return Path(shutil.copytree(char_dir, into / "snapshot"))


def _restore(snapshot: Path, char_dir: Path) -> None:
    """Put ``snapshot`` back: the copy is made beside the character first, so a
    failure to remove the half-written one cannot leave nothing behind."""
    beside = char_dir.with_name(char_dir.name + ".restore")
    shutil.copytree(snapshot, beside)
    shutil.rmtree(char_dir)
    beside.rename(char_dir)


@dataclass(frozen=True)
class _Drawing:
    """One picture to set: the attachment, its file, anchor, width and provenance."""

    attachment: str
    picture: Path
    anchor: tuple[float, float] | None
    width: float | None
    warnings: list[str]
    provenance: AssetSource | None


def _part_provenance(carving: Carving, name: str, origin: tuple[float, float]):
    """The carving's provenance for a part lifted off it at ``origin`` (carving px)."""
    source = carving.provenance()
    if source is None:
        return None
    carve_info = dict(source.extra["carve"])
    if matrix := carve_info.get("source_to_part"):
        carve_info["source_to_part"] = [
            [*row[:2], row[2] - o] for row, o in zip(matrix, origin)
        ]
    carve_info["split"] = {"part": name, "origin": list(origin)}
    return source.model_copy(update={"extra": {**source.extra, "carve": carve_info}})


def _drawings(
    p: SheetPart,
    carving: Carving,
    folder: Path,
    *,
    index: int,
    unit: float | None,
) -> list[_Drawing]:
    """The pictures ``p`` gives: itself, or its base and each split part."""

    def drawing(name, image, anchor, warnings, provenance):
        picture = folder / f"{index:03d}-{len(taken):02d}.png"
        taken.append(picture)
        image.save(picture)
        width = None if unit is None else image.width / carving.scale * unit
        return _Drawing(name, picture, anchor, width, warnings, provenance)

    taken: list[Path] = []
    warnings = carving.quality.warnings() + ([] if p.anchored else [_NO_ANCHOR])
    own_anchor = carving.anchor if p.anchored else None
    if not p.split:
        return [
            drawing(
                p.attachment, carving.image, own_anchor, warnings, carving.provenance()
            )
        ]
    k = max(round(carving.scale), 1)  # split_parts counts the carving's pixels
    specs = {n: replace(sp, grow=sp.grow * k) for n, sp in p.split.items()}
    lifted = split_parts(
        carving, specs, pad=_SPLIT_PAD * k, inpaint_radius=_SPLIT_INPAINT_RADIUS * k
    )
    if lifted.base is None:
        raise ValueError(
            f"{p.attachment!r}: the split parts took every pixel, nothing is left "
            "for the attachment to draw"
        )
    return [
        drawing(p.attachment, lifted.base, own_anchor, warnings, carving.provenance())
    ] + [
        drawing(
            part.name,
            part.image,
            part.anchor,
            [],
            _part_provenance(carving, part.name, part.origin),
        )
        for part in lifted.parts
    ]


def sheet_to_package(
    sheet: ImageLike,
    parts: Sequence[SheetPart | Mapping[str, Any]],
    char_dir: str | Path,
    *,
    source: AssetSource | None = None,
    ours: bool = False,
    unit: float | None = None,
    work_dir: str | Path | None = None,
) -> SheetReport:
    """Carve ``parts`` out of ``sheet`` and draw them on the factory character at ``char_dir``.

    sheet: a path, a PIL image or an array (the whole reference sheet)
    parts: the recipe, :class:`SheetPart` or their dicts; each file the rig
        draws from is replaced once (two attachments of one file are one part)
    source: the sheet's provenance (``frame_source``); required unless ``ours``
    ours: the sheet's pixels are the caller's own art (no source is recorded)
    unit: view-box units per SHEET pixel (``write_prop``'s is per carved pixel;
        they differ under super-resolution); each picture is declared that many
        units wide per carved pixel (default: the factory drawing's width)
    work_dir: where the carved pictures are first written (default: a temporary
        folder, gone afterwards; the rig keeps its own copy beside it either way)

    Raises ``ValueError`` before anything is written when provenance is
    missing, an attachment is unknown, ambiguous or shares its file with another
    part; if setting a part fails, the character is restored.
    """
    if source is None and not ours:
        raise ValueError(
            "a sheet with no provenance reads as art you made: pass "
            "source=frame_source(url, license=...), or ours=True if the pixels are yours"
        )
    unit = _check_unit(unit)
    char_dir = Path(char_dir)
    recipe = [p if isinstance(p, SheetPart) else SheetPart(**p) for p in parts]
    files: dict[str, str] = {}
    for p in recipe:  # fails on an unknown or ambiguous attachment, writes nothing
        for name in (p.attachment, *p.split):
            rel = part_path(char_dir, name)
            if rel in files:
                raise ValueError(f"{name!r} and {files[rel]!r} are both drawn by {rel}")
            files[rel] = name
    image = load_rgb(sheet)
    with tempfile.TemporaryDirectory(prefix="cutan-sheet-") as tmp:
        folder = Path(work_dir) if work_dir is not None else Path(tmp)
        folder.mkdir(parents=True, exist_ok=True)
        drawings = []
        for i, p in enumerate(recipe):
            kwargs = dict(p.carve, source=source)
            if p.crop is not None:
                kwargs["crop"] = p.crop
            carving = _CARVERS[p.mode](image, **kwargs)
            drawings += _drawings(p, carving, folder, index=i, unit=unit)
        snapshot = _snapshot(char_dir, Path(tmp))
        results = []
        try:
            for d in drawings:
                done = set_part(
                    char_dir,
                    d.attachment,
                    d.picture,
                    anchor=d.anchor,
                    source=d.provenance,
                    width=d.width,
                )
                results.append(PartResult(d.attachment, d.warnings, done))
        except BaseException:
            _restore(snapshot, char_dir)
            raise
    return SheetReport(results)
