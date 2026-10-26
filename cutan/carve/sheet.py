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
touched, so a bad recipe changes nothing. Provenance is required, as for
:func:`~cutan.carve.write_prop`: the sheet's ``source`` (``frame_source``), or
``ours=True`` for pixels that are the caller's. The report carries each part's
quality warnings in words, for the writer to read before anything renders.

Needs OpenCV: ``pip install "cutan[carve]"``.
"""

from __future__ import annotations

import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from an.ir.assets import AssetSource

from cutan.carve.core import Box, Carving, ImageLike, carve, load_rgb
from cutan.characters.set_part import PartReplacement, part_path, set_part

__all__ = ["PartResult", "SheetPart", "SheetReport", "sheet_to_package"]

#: carve() arguments the recipe cannot carry: the function owns them.
_OWNED = frozenset({"crop", "source"})


@dataclass(frozen=True)
class SheetPart:
    """One attachment and where on the sheet it is drawn.

    attachment: the attachment's name (``head``, ``mouth_a``), or ``slot/name``
    crop: ``(x0, y0, x1, y1)`` in the sheet's pixels, the region carved
    carve: the other :func:`~cutan.carve.carve` arguments (``matte``, ``point``,
        ``keep``, ``superres``...), JSON-able; a ``point`` anchors the part
    """

    attachment: str
    crop: Box
    carve: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if clash := _OWNED & set(self.carve):
            raise ValueError(
                f"{self.attachment!r}: {sorted(clash)} are not recipe arguments "
                "(the region is `crop`; the provenance is the sheet's)"
            )


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
        """Every part's quality warnings, each led by its attachment's name."""
        return [f"{r.attachment}: {w}" for r in self.parts for w in r.warnings]

    def format(self) -> str:
        head = f"{len(self.parts)} part(s) set from the sheet"
        return "\n".join([head, *(f"  warning: {w}" for w in self.warnings)])


def sheet_to_package(
    sheet: ImageLike,
    parts: Sequence[SheetPart | Mapping[str, Any]],
    char_dir: str | Path,
    *,
    source: AssetSource | None = None,
    ours: bool = False,
    work_dir: str | Path | None = None,
    carver: Callable[..., Carving] = carve,
    setter: Callable[..., PartReplacement] = set_part,
) -> SheetReport:
    """Carve ``parts`` out of ``sheet`` and draw them on the factory character at ``char_dir``.

    sheet: a path, a PIL image or an array (the whole reference sheet)
    parts: the recipe, :class:`SheetPart` or their dicts (``{"attachment", "crop",
        "carve"}``); each attachment appears once
    source: the sheet's provenance (``frame_source``); required unless ``ours``
    ours: the sheet's pixels are the caller's own art
    work_dir: where the carved pictures are first written (default: a temporary
        folder, gone afterwards; the rig keeps its own copy beside it either way)
    carver, setter: the strategies (default :func:`~cutan.carve.carve` and
        :func:`~cutan.characters.set_part.set_part`), for a host that carves
        another way or writes elsewhere

    Raises ``ValueError`` before anything is written when provenance is missing,
    an attachment is named twice or not in the rig.
    """
    if source is None and not ours:
        raise ValueError(
            "a sheet with no provenance reads as art you made: pass "
            "source=frame_source(url, license=...), or ours=True if the pixels are yours"
        )
    recipe = [p if isinstance(p, SheetPart) else SheetPart(**p) for p in parts]
    names = [p.attachment for p in recipe]
    if dupes := sorted({n for n in names if names.count(n) > 1}):
        raise ValueError(f"an attachment is drawn once per recipe: {dupes}")
    for p in recipe:  # fails on an unknown or ambiguous attachment, writes nothing
        part_path(char_dir, p.attachment)
    image = load_rgb(sheet)
    with tempfile.TemporaryDirectory(prefix="cutan-sheet-") as tmp:
        folder = Path(work_dir) if work_dir is not None else Path(tmp)
        folder.mkdir(parents=True, exist_ok=True)
        carved = []
        for p in recipe:
            carving = carver(image, crop=p.crop, source=source, **p.carve)
            picture = folder / f"{p.attachment.replace('/', '_')}.png"
            carving.image.save(picture)
            carved.append((p, carving, picture))
        results = []
        for p, carving, picture in carved:
            done = setter(
                char_dir,
                p.attachment,
                picture,
                anchor=carving.anchor if "point" in p.carve else None,
                source=carving.provenance(),
            )
            results.append(PartResult(p.attachment, carving.quality.warnings(), done))
    return SheetReport(results)
