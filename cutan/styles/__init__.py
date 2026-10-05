"""The named cut-out style specs, shipped as package data (cutan#4).

A style spec is one YAML document per named look (``south_park``,
``oversimplified``, ``kurzgesagt``, ``gilliam``, ``reiniger``, ``norstein``):
``live`` settings that map onto shipped ``an`` features, ``targets`` the style
lint measures a render against, ``prosody_targets`` for voice acting, and
``guidance`` for what the style needs beyond them. The ``cutan-style`` skill is
the procedure that applies one; this module is where the specs live, so code
and agents load a spec by its name rather than through a path into a skill
folder.

>>> 'south_park' in style_specs()
True
>>> spec = style_spec('south_park')
>>> spec['style'], spec['cost_class']
('south_park', 'low')
>>> style_spec_path('south_park').name
'south_park.yaml'

Each call returns a fresh dict, so a caller may change it freely:

>>> style_spec('south_park') is style_spec('south_park')
False

An unknown name is refused with the names there are:

>>> style_spec('pixar')  # doctest: +ELLIPSIS
Traceback (most recent call last):
  ...
cutan.styles.UnknownStyleError: no style spec named 'pixar'; the specs are: gilliam, ...

``python -m cutan.styles`` lists the specs, ``python -m cutan.styles NAME``
prints one, and ``python -m cutan.styles NAME --path`` prints its file's path
(for a tool that wants a path, such as ``an.verify.prosody --targets``).
"""

from __future__ import annotations

import re
from importlib.resources import files
from pathlib import Path
from typing import Any

__all__ = [
    "STYLE_SPEC_SUFFIX",
    "UnknownStyleError",
    "style_spec",
    "style_spec_path",
    "style_spec_text",
    "style_specs",
]

#: The file suffix of a style spec in this package.
STYLE_SPEC_SUFFIX: str = ".yaml"

#: What a style name may be: the spec's ``style`` key and its file's stem.
_STYLE_NAME = re.compile(r"[a-z][a-z0-9_]*")


class UnknownStyleError(LookupError):
    """No style spec of that name ships with ``cutan``."""

    def __str__(self) -> str:  # LookupError would repr() the message, quotes and all
        return str(self.args[0]) if self.args else ""


def _spec_files() -> dict[str, Any]:
    """``{name: resource}`` for every spec file in this package."""
    return {
        entry.name[: -len(STYLE_SPEC_SUFFIX)]: entry
        for entry in files(__name__).iterdir()
        if entry.name.endswith(STYLE_SPEC_SUFFIX) and entry.is_file()
    }


def style_specs() -> list[str]:
    """The names of the style specs that ship with ``cutan``, sorted."""
    return sorted(_spec_files())


def _resource(name: str) -> Any:
    specs = _spec_files()
    if (
        not isinstance(name, str)
        or not _STYLE_NAME.fullmatch(name)
        or name not in specs
    ):
        raise UnknownStyleError(
            f"no style spec named {name!r}; the specs are: {', '.join(sorted(specs))}"
        )
    return specs[name]


def style_spec_path(name: str) -> Path:
    """The file of the style spec ``name`` (for a tool that reads a path)."""
    return Path(str(_resource(name)))


def style_spec_text(name: str) -> str:
    """The YAML text of the style spec ``name``, comments included."""
    return _resource(name).read_text(encoding="utf-8")


def style_spec(name: str) -> dict[str, Any]:
    """The style spec ``name``, parsed: a new dict on every call."""
    import yaml

    data = yaml.safe_load(style_spec_text(name))
    if not isinstance(data, dict) or data.get("style") != name:
        raise ValueError(
            f"the style spec file {name}{STYLE_SPEC_SUFFIX} is not a mapping whose "
            f"`style` is {name!r}"
        )
    return data
