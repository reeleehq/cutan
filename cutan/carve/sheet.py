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

Not covered: lifting several moving parts off ONE carving with pivots
(:func:`~cutan.carve.split_parts`); a limb is a polygon-matte region of its own.
A picture is drawn at the width of the factory drawing it replaces, so parts
from one sheet do not keep their relative scale: size them with ``carve`` or
declare a width. A part with no ``point`` keeps the factory's anchor, which
belongs to a different picture's framing (the report says so).

The recipe as a document is :func:`load_recipe` (``schema_version`` 1).

Needs OpenCV: ``pip install "cutan[carve]"``.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from an.ir.assets import AssetSource

from cutan.carve.core import Box, ImageLike, carve, carve_head, load_rgb
from cutan.carve.provenance import frame_source
from cutan.characters.set_part import PartReplacement, part_path, set_part

__all__ = [
    "RECIPE_SCHEMA_VERSION",
    "PartResult",
    "SheetPart",
    "SheetReport",
    "load_recipe",
    "sheet_to_package",
]

#: The recipe document's version, written as ``schema_version``.
RECIPE_SCHEMA_VERSION = 1
#: How a part is carved: ``carve`` (a region) or ``carve_head`` (a head on its fixed canvas).
_CARVERS = {"part": carve, "head": carve_head}
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
    """

    attachment: str
    crop: Box | None = None
    carve: Mapping[str, Any] = field(default_factory=dict)
    mode: str = "part"

    def __post_init__(self) -> None:
        if self.mode not in _CARVERS:
            raise ValueError(f"{self.attachment!r}: mode is one of {sorted(_CARVERS)}")
        if self.mode == "part" and self.crop is None:
            raise ValueError(f"{self.attachment!r}: a part needs its `crop`")
        if self.mode == "head" and self.crop is not None:
            raise ValueError(f"{self.attachment!r}: a head is found by carve['face'], not a crop")
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
            lines.append(f"  still the factory's drawings, derived from them: {', '.join(self.derived)}")
        return "\n".join(lines)


def load_recipe(doc: Mapping[str, Any]) -> tuple[list[SheetPart], AssetSource | None, bool]:
    """``(parts, source, ours)`` from a recipe document.

    ``{"schema_version": 1, "source": {frame_source's arguments} | null,
    "ours": false, "parts": [{"attachment", "crop", "carve", "mode"}]}``
    """
    version = doc.get("schema_version", RECIPE_SCHEMA_VERSION)
    if version != RECIPE_SCHEMA_VERSION:
        raise ValueError(f"recipe schema_version {version!r}; this reads {RECIPE_SCHEMA_VERSION}")
    source = frame_source(**doc["source"]) if doc.get("source") else None
    parts = [SheetPart(**p) for p in doc["parts"]]
    return parts, source, bool(doc.get("ours"))


def _snapshot(char_dir: Path, into: Path) -> Path:
    return Path(shutil.copytree(char_dir, into / "snapshot"))


def _restore(snapshot: Path, char_dir: Path) -> None:
    shutil.rmtree(char_dir)
    shutil.copytree(snapshot, char_dir)


def sheet_to_package(
    sheet: ImageLike,
    parts: Sequence[SheetPart | Mapping[str, Any]],
    char_dir: str | Path,
    *,
    source: AssetSource | None = None,
    ours: bool = False,
    work_dir: str | Path | None = None,
) -> SheetReport:
    """Carve ``parts`` out of ``sheet`` and draw them on the factory character at ``char_dir``.

    sheet: a path, a PIL image or an array (the whole reference sheet)
    parts: the recipe, :class:`SheetPart` or their dicts; each file the rig
        draws from is replaced once (two attachments of one file are one part)
    source: the sheet's provenance (``frame_source``); required unless ``ours``
    ours: the sheet's pixels are the caller's own art (no source is recorded)
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
    char_dir = Path(char_dir)
    recipe = [p if isinstance(p, SheetPart) else SheetPart(**p) for p in parts]
    files: dict[str, str] = {}
    for p in recipe:  # fails on an unknown or ambiguous attachment, writes nothing
        rel = part_path(char_dir, p.attachment)
        if rel in files:
            raise ValueError(f"{p.attachment!r} and {files[rel]!r} are both drawn by {rel}")
        files[rel] = p.attachment
    image = load_rgb(sheet)
    with tempfile.TemporaryDirectory(prefix="cutan-sheet-") as tmp:
        folder = Path(work_dir) if work_dir is not None else Path(tmp)
        folder.mkdir(parents=True, exist_ok=True)
        carved = []
        for i, p in enumerate(recipe):
            kwargs = dict(p.carve, source=source)
            if p.crop is not None:
                kwargs["crop"] = p.crop
            carving = _CARVERS[p.mode](image, **kwargs)
            picture = folder / f"{i:03d}.png"
            carving.image.save(picture)
            carved.append((p, carving, picture))
        snapshot = _snapshot(char_dir, Path(tmp))
        results = []
        try:
            for p, carving, picture in carved:
                done = set_part(
                    char_dir,
                    p.attachment,
                    picture,
                    anchor=carving.anchor if p.anchored else None,
                    source=carving.provenance(),
                )
                warnings = carving.quality.warnings() + ([] if p.anchored else [_NO_ANCHOR])
                results.append(PartResult(p.attachment, warnings, done))
        except BaseException:
            _restore(snapshot, char_dir)
            raise
    return SheetReport(results)
