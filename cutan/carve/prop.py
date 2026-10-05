"""Write a carving (or a carving split into parts) as a library-ready prop folder.

The folder is the layout every ``an`` project store and the library read:
``prop.json`` (a :class:`~an.stage.props.PropDescriptor`) and ``parts/*.png``.
The descriptor's ``source`` is the carving's provenance, recipe and quality
included, so publishing it records the rights without a single flag::

    from an.library import open_library, publish_dir
    publish_dir(open_library("cutan"), folder, "prop.wall-clock", origin="carved")

(``an library publish <folder> prop.wall-clock --package cutan --origin carved``
from a shell.) One pixel of the carving is one view_box unit times ``unit``,
and each part declares its size, so the prop draws the same whatever the
resolution the art was carved at.

**Rights are never loosened by accident.** A descriptor with no ``source``
means "we made this" to ``an``, so a carving with no provenance is refused
unless the caller says the art is its own (``ours=True``). A ``source=`` that
would loosen the carving's licence class is refused unless ``relicense=``
says who decided and why (``an``'s own rule for relaxing rights); the
carving's source is kept beside it as ``extra.carved_from`` either way.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from an.ir.assets import AssetSource, license_class
from an.stage.props import PropDescriptor
from cutan.carve.core import Carving
from cutan.carve.parts import PartSet

__all__ = ["BASE_SLOT", "ROOT_BONE", "write_prop"]

#: The bone every carved prop hangs from, at the carving's anchor.
ROOT_BONE: str = "root"
#: The slot of the base art (a single-part prop's only slot).
BASE_SLOT: str = "body"


def _looser(new: AssetSource, old: AssetSource) -> bool:
    """Whether ``new``'s licence class is less restrictive than ``old``'s."""
    from an.library.rights import most_restrictive

    a, b = license_class(old), license_class(new)
    return a != b and most_restrictive([a, b]) == a


def _provenance(
    carving: Carving,
    source: AssetSource | None,
    *,
    ours: bool,
    relicense: Mapping[str, str] | None,
) -> AssetSource | None:
    prov = carving.provenance()
    if source is None:
        if prov is None and not ours:
            raise ValueError(
                "this carving has no provenance, and a prop with no source reads as art "
                "you made: pass source=frame_source(url, license=...) to carve(), or "
                "write_prop(..., source=...) here, or ours=True if the pixels are yours"
            )
        return prov
    extra = dict(source.extra or {})
    if prov is not None:
        extra["carve"] = prov.extra["carve"]
        original = carving.source
        extra["carved_from"] = original.model_dump(mode="json", exclude_none=True)
        if _looser(source, original):
            given = (
                {k: str(relicense.get(k) or "").strip() for k in ("by", "reason")}
                if relicense
                else {}
            )
            if not all(given.get(k) for k in ("by", "reason")):
                raise ValueError(
                    f"source= would loosen the carving's rights ({license_class(original)} "
                    f"to {license_class(source)}): pass relicense={{'by': ..., 'reason': ...}} "
                    "if that is a decision someone took"
                )
            extra["relicensed"] = given
    return source.model_copy(update={"extra": extra})


def write_prop(
    carved: Carving | PartSet,
    folder: str | Path,
    *,
    name: str | None = None,
    unit: float | None = None,
    max_side: float | None = None,
    display_name: str | None = None,
    source: AssetSource | None = None,
    ours: bool = False,
    relicense: Mapping[str, str] | None = None,
    overwrite: bool = False,
) -> PropDescriptor:
    """Write ``carved`` to ``folder`` as ``prop.json`` + ``parts/*.png``; return the descriptor.

    name: the prop's name (default: the folder's name)
    unit: view_box units per carved pixel (default 1); or ``max_side``: the
        unit that makes the longer side that many units (never above 1)
    source: overrides the carving's provenance (its recipe and quality are
        still recorded in ``extra.carve``, its source in ``extra.carved_from``)
    ours: the pixels are the caller's own art (a carving with no source)
    relicense: ``{"by": who, "reason": why}`` (both non-empty), required for a
        ``source`` that loosens the carving's licence class. Recorded in the
        descriptor's ``source.extra.relicensed``; ``an library publish`` does not
        read it, so say it again there (``relicense=``) when publishing.

    A :class:`~cutan.carve.PartSet` is written with its carving's provenance:
    build one with :func:`~cutan.carve.split_parts` (its parts are cut from
    that carving), never by hand from other carvings' parts.

    The root bone sits at the carving's anchor. A split prop gets one bone per
    part, at its pivot, parented to the root, and one slot per part above the
    base, in the order the parts were listed. Nothing is written unless the
    whole descriptor is valid.
    """
    folder = Path(folder)
    if (folder / "prop.json").exists() and not overwrite:
        raise FileExistsError(
            f"{folder / 'prop.json'} exists; pass overwrite=True to replace it"
        )
    carving = carved.carving if isinstance(carved, PartSet) else carved
    w, h = carving.size
    if unit is None:
        unit = min(max_side / max(w, h), 1.0) if max_side else 1.0
    if unit <= 0:
        raise ValueError(f"unit must be positive, not {unit}")
    ax, ay = carving.anchor[0] * w, carving.anchor[1] * h
    prov = _provenance(carving, source, ours=ours, relicense=relicense)

    bones: list[dict[str, Any]] = [{"name": ROOT_BONE, "parent": None}]
    slots: list[dict[str, Any]] = []
    attachments: dict[str, dict] = {}
    images: dict[str, Any] = {}

    def attach(slot: str, bone: str, image, anchor, order: int) -> None:
        path = f"parts/{slot}.png"
        images[path] = image
        slots.append(
            {"name": slot, "bone": bone, "draw_order": order, "attachment": slot}
        )
        attachments[slot] = {
            slot: {
                "path": path,
                "anchor": [float(anchor[0]), float(anchor[1])],
                "width": round(image.width * unit, 3),
                "height": round(image.height * unit, 3),
                "x": 0.0,
                "y": 0.0,
            }
        }

    if isinstance(carved, PartSet):
        if carved.base is not None:
            attach(BASE_SLOT, ROOT_BONE, carved.base, carving.anchor, 0)
        for part in carved.parts:
            if part.name in (BASE_SLOT, ROOT_BONE):
                raise ValueError(
                    f"a part may not be called {part.name!r} (the prop's own)"
                )
            px, py = part.origin[0] + part.pivot[0], part.origin[1] + part.pivot[1]
            bones.append(
                {
                    "name": part.name,
                    "parent": ROOT_BONE,
                    "x": round((px - ax) * unit, 3),
                    "y": round((py - ay) * unit, 3),
                }
            )
            attach(part.name, part.name, part.image, part.anchor, part.draw_order)
    else:
        attach(BASE_SLOT, ROOT_BONE, carving.image, carving.anchor, 0)

    doc = PropDescriptor.model_validate(
        {
            "name": name or folder.name,
            "display_name": display_name,
            "view_box": [0, 0, max(1, round(w * unit)), max(1, round(h * unit))],
            "bones": bones,
            "slots": slots,
            "skins": {"default": {"name": "default", "slots": attachments}},
            "source": prov.model_dump(mode="json", exclude_none=True) if prov else None,
            "metadata": {
                "carve": {
                    "mode": carving.mode,
                    "anchor": list(carving.anchor),
                    **carving.meta,
                }
            },
        }
    )
    text = json.dumps(
        doc.model_dump(mode="json"), indent=2
    )  # fails before any file is written
    (folder / "parts").mkdir(parents=True, exist_ok=True)
    for path, image in images.items():
        image.save(folder / path)
    (folder / "prop.json").write_text(text, "utf-8")
    return doc
