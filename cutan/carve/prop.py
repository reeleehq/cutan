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

**Where a hand holds it.** ``landmarks=`` names points of the prop (a sabre's
grip and its tip, a mug's handle) in the source's pixels, the same frame as
``point``. Each is written as a bone with no slot, hung from the root: what
``an`` reads as a rig's named point (``an.stage.rig.rig_structure``'s
``anchors``), so a scene addresses it as ``<prop>@<name>`` (a joint's
``wheel@grip``), and a bone called :data:`GRIP` is where the hold verbs take
the prop by default (an#502). Two landmarks give an axis: ``grip`` and ``tip``
say which way the blade points from the hand.

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

__all__ = ["BASE_SLOT", "GRIP", "ROOT_BONE", "write_prop"]

#: The bone every carved prop hangs from, at the carving's anchor.
ROOT_BONE: str = "root"
#: The slot of the base art (a single-part prop's only slot).
BASE_SLOT: str = "body"
#: The landmark a hand takes a prop by when a scene names no other (an's hold
#: verbs read a bone of this name; an#502).
GRIP: str = "grip"
#: Characters a landmark's name may not hold: a scene addresses it as
#: ``<prop>@<name>``, and ``u,v`` there is a fraction of the drawing.
_NOT_IN_A_LANDMARK = frozenset("@/, \t\n")

Point = tuple[float, float]


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


def _landmark_bones(
    carving: Carving,
    landmarks: Mapping[str, Point],
    *,
    unit: float,
    taken: set[str],
) -> list[dict[str, Any]]:
    """``landmarks`` (source pixels) as slotless bones hung from the root, in
    view_box units from the carving's anchor (where the root bone sits).

    >>> import numpy as np
    >>> img = np.full((60, 80, 3), 250, np.uint8); img[15:45, 20:60] = (30, 90, 200)
    >>> from cutan.carve import carve
    >>> part = carve(img, point=(30, 40))
    >>> _landmark_bones(part, {"grip": (30, 40), "tip": (55, 20)}, unit=0.5, taken={"root"})
    [{'name': 'grip', 'parent': 'root', 'x': 0.0, 'y': 0.0}, {'name': 'tip', 'parent': 'root', 'x': 12.5, 'y': -10.0}]
    """
    w, h = carving.size
    ax, ay = carving.anchor[0] * w, carving.anchor[1] * h
    bones = []
    for name, at in landmarks.items():
        name = str(name)
        if not name.strip() or set(name) & _NOT_IN_A_LANDMARK:
            raise ValueError(
                f"a landmark's name is what a scene writes after '@' (stu@hand_r, "
                f"sabre@grip): no '@', '/', ',' or spaces, not {name!r}"
            )
        if name in taken:
            raise ValueError(
                f"landmark {name!r} is already a bone of this prop (the root or a part)"
            )
        try:
            x, y = (float(v) for v in at)
        except (TypeError, ValueError):
            raise ValueError(
                f"landmark {name!r}: a point is (x, y) in the source's pixels, not {at!r}"
            ) from None
        ((px, py),) = carving.to_part([(x, y)])
        taken.add(name)
        bones.append(
            {
                "name": name,
                "parent": ROOT_BONE,
                "x": round((px - ax) * unit, 3) + 0.0,
                "y": round((py - ay) * unit, 3) + 0.0,
            }
        )
    return bones


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
    landmarks: Mapping[str, Point] | None = None,
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
    landmarks: named points of the prop in the source's pixels, each written
        as a slotless bone on the root: ``{"grip": (x, y), "tip": (x, y)}``
        (``grip``, :data:`GRIP`, is where a hand takes it). See the module
        docstring.

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
    if landmarks:
        bones += _landmark_bones(
            carving, landmarks, unit=unit, taken={b["name"] for b in bones}
        )

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
