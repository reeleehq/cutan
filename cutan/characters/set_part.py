"""Replace a factory part's drawing with a picture (cutan#92).

A factory character draws every attachment as an SVG (``parts/head.svg``). An
illustrator, an image generator or a carve can instead supply a picture with an
alpha channel (PNG, WebP, JPEG): :func:`replace_part_art` copies it beside the
rig, points every attachment that drew the old file at it, and keeps the box the
attachment already declared (or the old drawing's root size, an#220), so the
slot draws it where and as large as the factory's did. The old drawing's
``colour_roles`` and pinned source go with it: a picture's pixels are not the
factory's and a pack cannot recolour them. Nothing else in the descriptor moves,
so the swap channels and the rig contract are untouched.

:func:`set_part` is the by-name front: ``an character set-part <name>
<attachment> <file>``.
"""

from __future__ import annotations

import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

from an.stores._common import ASSET_REF_RULE, inside_folder

__all__ = ["SetPartError", "replace_part_art", "set_part"]


class SetPartError(ValueError):
    """A part cannot be replaced; the message says what to do."""


def _slot_attachments(raw: dict):
    """``(skin, slot, name, attachment dict)`` for every attachment in the document."""
    for skin, body in (raw.get("skins") or {}).items():
        for slot, attachments in ((body or {}).get("slots") or {}).items():
            for name, att in (attachments or {}).items():
                yield skin, slot, name, att


def _root_size(svg: Path) -> tuple[float, float] | None:
    """The drawing's declared ``width`` and ``height``, else its viewBox's."""
    try:
        root = ET.parse(svg).getroot()
        box = (root.get("viewBox") or "").replace(",", " ").split()
        w = float(root.get("width") or (box[2] if len(box) == 4 else ""))
        h = float(root.get("height") or (box[3] if len(box) == 4 else ""))
    except (OSError, ET.ParseError, ValueError):
        return None
    return (w, h) if w > 0 and h > 0 else None


def replace_part_art(char_dir: str | Path, old_rel: str, picture: str | Path) -> Path:
    """Draw every attachment that used ``old_rel`` (``parts/head.svg``) with ``picture``.

    Returns the descriptor path. Raises :class:`SetPartError` when no attachment
    draws ``old_rel``, when ``picture`` is not a readable PNG/JPEG/WebP, or when
    a path leaves the character's folder.
    """
    from an.ir.migrate import migrate
    from an.stage.raster import RASTER_SUFFIXES, image_size

    from cutan.characters.schema import CharacterDescriptor

    char_dir, picture = Path(char_dir), Path(picture)
    desc_path = char_dir / "character.json"
    raw = json.loads(desc_path.read_text(encoding="utf-8"))
    users = [a for *_, a in _slot_attachments(raw) if a.get("path") == old_rel]
    if not users:
        raise SetPartError(f"no attachment of {raw.get('name')!r} draws {old_rel!r}")
    if picture.suffix.lower() not in RASTER_SUFFIXES:
        raise SetPartError(
            f"{picture.name} is not a picture ({', '.join(RASTER_SUFFIXES)})"
        )
    try:
        image_size(picture)
    except (OSError, ValueError) as e:
        raise SetPartError(f"{picture.name} is not a readable picture: {e}") from None
    new_rel = str(Path(old_rel).with_suffix(picture.suffix.lower()).as_posix())
    old_file, new_file = inside_folder(char_dir, old_rel), inside_folder(char_dir, new_rel)
    if old_file is None or new_file is None:
        raise SetPartError(f"{old_rel!r} leaves the character's folder: {ASSET_REF_RULE}")
    size = _root_size(old_file) if old_file.suffix.lower() == ".svg" else None
    new_file.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(picture, new_file)
    if old_file != new_file:
        old_file.unlink(missing_ok=True)
    for att in users:
        att["path"] = new_rel
        att.pop("source", None)  # pinned to the factory's drawing
        if size and not (att.get("width") and att.get("height")):
            att["width"], att["height"] = size
    (raw.get("colour_roles") or {}).pop(old_rel, None)
    desc = CharacterDescriptor.model_validate(migrate(raw, kind="CharacterDescriptor"))
    desc_path.write_text(desc.model_dump_json(indent=2), encoding="utf-8")
    return desc_path


def set_part(char_dir: str | Path, attachment: str, picture: str | Path) -> Path:
    """Replace the drawing of ``attachment`` (``name``, or ``slot/name`` when
    several slots carry that name) with ``picture``; see :func:`replace_part_art`."""
    raw = json.loads((Path(char_dir) / "character.json").read_text(encoding="utf-8"))
    slot_wanted, _, name_wanted = attachment.rpartition("/")
    found = {
        (slot, name): att.get("path")
        for _skin, slot, name, att in _slot_attachments(raw)
        if name == name_wanted and slot_wanted in ("", slot)
    }
    paths = set(found.values())
    if not paths:
        raise SetPartError(f"no attachment {attachment!r} (try slot/name)")
    if len(paths) > 1:
        raise SetPartError(
            f"{attachment!r} is drawn by several files ({', '.join(sorted(map(str, paths)))}): "
            "name it slot/name"
        )
    return replace_part_art(char_dir, paths.pop(), picture)
