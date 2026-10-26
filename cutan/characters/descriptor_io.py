"""Read, check and write a character's ``character.json`` (cutan#129).

Every edit of a character folder is the same cycle: read ``character.json``,
:func:`~an.ir.migrate.migrate` it to the current schema, validate it as a
:class:`~cutan.characters.schema.CharacterDescriptor`, change it, write it back.
It was copied about ten times; each copy decided for itself whether the document
was valid BEFORE it wrote any file, and a few did not (a part's picture copied
beside a descriptor that then failed to validate). This is that cycle once:

- :func:`load_descriptor` reads and validates; :func:`write_descriptor` writes;
- :func:`save_raw` is the same for an edit made on the raw JSON: it validates
  the document first and writes only a valid one (:func:`validate_raw` alone,
  for a caller that has files to write between the check and the write).

>>> import tempfile, pathlib
>>> from cutan.characters import new_character
>>> with tempfile.TemporaryDirectory() as d:
...     char = new_character(d, name='nobody', use_dicebear=False).parent
...     desc = load_descriptor(char)
...     desc.display_name = 'Nobody'
...     write_descriptor(char, desc).name, load_descriptor(char).display_name
('character.json', 'Nobody')
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

__all__ = [
    "DESCRIPTOR_FILE",
    "descriptor_path",
    "load_descriptor",
    "read_raw",
    "save_raw",
    "validate_raw",
    "write_descriptor",
]

#: The descriptor's file name in a character folder.
DESCRIPTOR_FILE = "character.json"
#: The document kind ``migrate`` is asked to bring up to date.
_KIND = "CharacterDescriptor"


def descriptor_path(char_dir: str | Path) -> Path:
    """Where the descriptor of the character folder ``char_dir`` is."""
    return Path(char_dir) / DESCRIPTOR_FILE


def read_raw(char_dir: str | Path) -> dict[str, Any]:
    """The descriptor as the JSON document on disk (not migrated, not validated)."""
    return json.loads(descriptor_path(char_dir).read_text(encoding="utf-8"))


def validate_raw(raw: dict[str, Any]):
    """``raw`` migrated to the current schema and validated: a ``CharacterDescriptor``
    (``pydantic.ValidationError`` when it is not one)."""
    from an.ir.migrate import migrate

    from cutan.characters.schema import CharacterDescriptor

    return CharacterDescriptor.model_validate(migrate(raw, kind=_KIND))


def load_descriptor(char_dir: str | Path):
    """The character's descriptor, migrated and validated."""
    return validate_raw(read_raw(char_dir))


def write_descriptor(char_dir: str | Path, desc) -> Path:
    """Write ``desc`` as the character's ``character.json``; return its path.
    A model changed in place is validated again first (the schema does not
    validate assignments), so an invalid edit writes nothing."""
    desc = type(desc).model_validate(desc.model_dump())
    path = descriptor_path(char_dir)
    path.write_text(desc.model_dump_json(indent=2), encoding="utf-8")
    return path


def save_raw(char_dir: str | Path, raw: dict[str, Any]):
    """Validate ``raw`` (an edited document), THEN write it; return the descriptor.
    Nothing is written when it does not validate."""
    desc = validate_raw(raw)
    write_descriptor(char_dir, desc)
    return desc
