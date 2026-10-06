"""A HALF eyelid drawing, made from a character's own OPEN and CLOSED lid art (cutan#65).

The expression solver picks an eyelid DRAWING per lid state (the ladder: wide,
open, half, closed; :func:`cutan.expression.axes.lid_key`). A rig whose
``eyelid`` set draws only ``OPEN`` and ``CLOSED`` shows ``OPEN`` for a partial
lid, so a squint, suspicion or annoyance cannot narrow the eyes, and the
validator says so. This module gives such a rig its ``HALF`` drawing without an
illustrator: for each eye, the CLOSED drawing clipped to its upper part, with
the OPEN drawing (its outline) laid over it. It works on any pair of SVG eye
drawings that share a view box, the factory's or a hand-drawn rig's.

>>> half_lid_svg(
...     '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 32"><ellipse cx="32" cy="16" rx="14" ry="10" fill="none" stroke="#222"/></svg>',
...     '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 32"><ellipse cx="32" cy="16" rx="14" ry="10" fill="#8b5a3b"/></svg>',
... ).count("clip-path")
1

The ``half`` attachment copies the ``open`` one's placement. Its source says
what it was derived from; when both drawings carry the same licence it carries
that licence too, pinned to the new file's digest, so the asset library and
``an credits`` can state it. Otherwise it is left unlabelled (UNVERIFIED), never
guessed.
"""

from __future__ import annotations

import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

__all__ = [
    "DFLT_HALF_LID_FRACTION",
    "HALF_ATTACHMENT",
    "HALF_LID_PROVIDER",
    "add_half_lid",
    "half_lid_svg",
]

#: How much of the eye the half lid covers, from the top of the drawing.
DFLT_HALF_LID_FRACTION: float = 0.5

#: The attachment name the HALF key points at.
HALF_ATTACHMENT: str = "half"

#: The provider of the source a derived half lid carries.
HALF_LID_PROVIDER: str = "cutan add-half-lid (derived from the rig's own lid art)"

_EYELID_SET: str = "eyelid"
_SVG_NS: str = "http://www.w3.org/2000/svg"
_CLIP_ID: str = "half_lid_clip"


class HalfLidError(ValueError):
    """The rig's lid art cannot give a HALF drawing; the message says what to do."""


def _view_box(root: ET.Element) -> tuple[float, float, float, float]:
    raw = root.get("viewBox")
    if raw:
        x, y, w, h = (float(v) for v in raw.replace(",", " ").split())
        return x, y, w, h
    return 0.0, 0.0, float(root.get("width", "0")), float(root.get("height", "0"))


def _inner(root: ET.Element) -> str:
    ET.register_namespace("", _SVG_NS)
    return "".join(ET.tostring(child, encoding="unicode") for child in root)


def half_lid_svg(
    open_svg: str, closed_svg: str, *, fraction: float = DFLT_HALF_LID_FRACTION
) -> str:
    """The HALF drawing: ``closed_svg`` clipped to its top ``fraction``, under
    ``open_svg``. Both must share a view box (else :class:`HalfLidError`)."""
    if not 0.0 < fraction < 1.0:
        raise HalfLidError(f"fraction must be between 0 and 1; got {fraction!r}")
    o, c = ET.fromstring(open_svg), ET.fromstring(closed_svg)
    box = _view_box(o)
    if box != _view_box(c):
        raise HalfLidError(
            f"the open and closed lid drawings have different view boxes ({box} "
            f"and {_view_box(c)}), so the lid cannot be cut out of one and laid "
            "on the other: draw the HALF lid by hand"
        )
    x, y, w, h = box
    size = "".join(
        f' {k}="{o.get(k)}"' for k in ("width", "height") if o.get(k) is not None
    )
    return (
        f'<svg xmlns="{_SVG_NS}" viewBox="{x:g} {y:g} {w:g} {h:g}"{size}>'
        f'<defs><clipPath id="{_CLIP_ID}"><rect x="{x:g}" y="{y:g}" '
        f'width="{w:g}" height="{h * fraction:g}"/></clipPath></defs>'
        f'<g clip-path="url(#{_CLIP_ID})">{_inner(c)}</g>'
        f"<g>{_inner(o)}</g></svg>"
    )


def _half_path(open_path: str) -> str:
    p = Path(open_path)
    stem = (
        p.stem.replace("open", HALF_ATTACHMENT)
        if "open" in p.stem
        else f"{p.stem}_half"
    )
    return (p.parent / f"{stem}{p.suffix}").as_posix()


def _derived_source(
    open_att: dict, closed_att: dict, digest: str, paths
) -> dict | None:
    licences = {
        (att.get("source") or {}).get("license") for att in (open_att, closed_att)
    }
    if len(licences) != 1 or None in licences:
        return None
    return {
        "provider": HALF_LID_PROVIDER,
        "license": licences.pop(),
        "sha256": digest,
        "extra": {"derived_from": sorted(paths)},
    }


def add_half_lid(
    char_dir: str | Path,
    *,
    fraction: float = DFLT_HALF_LID_FRACTION,
    overwrite: bool = False,
) -> Path:
    """Give the character at ``char_dir`` a ``HALF`` eyelid drawing; return its descriptor path.

    For every slot of the default skin that holds both the ``OPEN`` and the
    ``CLOSED`` attachment of the ``eyelid`` set, writes the half drawing beside
    the open one (``eye_l_open.svg`` -> ``eye_l_half.svg``), adds a ``half``
    attachment placed like the open one, and maps ``HALF`` to it. Idempotent.
    A rig that already has a ``HALF`` it did not get from here is refused
    unless ``overwrite``: that drawing is an illustrator's.
    """
    char_dir = Path(char_dir)
    desc_path = char_dir / "character.json"
    raw = json.loads(desc_path.read_text(encoding="utf-8"))
    eyelid = (raw.get("asset_sets") or {}).get(_EYELID_SET) or {}
    keys = {str(k).upper(): v for k, v in eyelid.items()}
    if "OPEN" not in keys or "CLOSED" not in keys:
        raise HalfLidError(
            f"{raw.get('name')!r} has no eyelid set with OPEN and CLOSED drawings "
            f"(its eyelid set: {sorted(keys) or 'none'}): there is nothing to make a "
            "HALF lid from"
        )
    existing = keys.get("HALF")
    if existing is not None and existing != HALF_ATTACHMENT and not overwrite:
        raise HalfLidError(
            f"{raw.get('name')!r} already has a HALF lid ({existing!r}), drawn by "
            "someone: pass overwrite=True (`--overwrite`) to replace it"
        )
    open_name, closed_name = keys["OPEN"], keys["CLOSED"]
    slots = ((raw.get("skins") or {}).get("default") or {}).get("slots") or {}
    done = 0
    for attachments in slots.values():
        if open_name not in attachments or closed_name not in attachments:
            continue
        open_att, closed_att = attachments[open_name], attachments[closed_name]
        o_path, c_path = open_att.get("path"), closed_att.get("path")
        if not (str(o_path).endswith(".svg") and str(c_path).endswith(".svg")):
            raise HalfLidError(
                f"{raw.get('name')!r}'s lid art is not SVG ({o_path}, {c_path}): draw "
                "the HALF lid by hand and map it in the eyelid set"
            )
        svg = half_lid_svg(
            (char_dir / o_path).read_text(encoding="utf-8"),
            (char_dir / c_path).read_text(encoding="utf-8"),
            fraction=fraction,
        )
        h_path = _half_path(o_path)
        (char_dir / h_path).write_text(svg, encoding="utf-8")
        digest = hashlib.sha256(svg.encode("utf-8")).hexdigest()
        half = {k: v for k, v in open_att.items() if k != "source"}
        half["path"] = h_path
        source = _derived_source(open_att, closed_att, digest, (o_path, c_path))
        if source is not None:
            half["source"] = source
        attachments[HALF_ATTACHMENT] = half
        done += 1
    if not done:
        raise HalfLidError(
            f"no slot of {raw.get('name')!r}'s default skin holds both the "
            f"{open_name!r} and the {closed_name!r} lid drawings"
        )
    raw["asset_sets"][_EYELID_SET] = {**eyelid, "HALF": HALF_ATTACHMENT}
    from an.ir.migrate import migrate

    from cutan.characters.schema import CharacterDescriptor

    desc = CharacterDescriptor.model_validate(migrate(raw, kind="CharacterDescriptor"))
    desc_path.write_text(desc.model_dump_json(indent=2), encoding="utf-8")
    return desc_path
