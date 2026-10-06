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

An unknown name is refused with the names there are (a ``KeyError``):

>>> try:
...     style_spec('pixar')
... except KeyError as e:
...     print(e)
no style spec named 'pixar'; the specs are: gilliam, kurzgesagt, norstein, oversimplified, reiniger, south_park

**A spec changes between releases** (targets re-measured, roles re-cast), and
whatever a production copied out of one (a StylePack, a voice document with
resolved targets, a kit) is a snapshot of the version it was copied from.
:func:`style_spec_digest` names that version: record it beside the copy, and
compare it with the installed spec's to know whether the copy is current.

>>> len(style_spec_digest('south_park'))
64

:func:`resolve_style_spec` is the one place a *reference* to a spec becomes a
spec: a mapping (passed through), a path to a YAML file, or a style's name.

``python -m cutan.styles`` lists the specs, ``python -m cutan.styles NAME``
prints one, and ``python -m cutan.styles NAME --path`` prints its file's path
(for a tool that wants a path, such as ``an.verify.prosody --targets``).
"""

from __future__ import annotations

import copy
import hashlib
import os
import re
from collections.abc import Mapping
from importlib.resources import files
from pathlib import Path
from typing import Any

__all__ = [
    "STYLE_SPEC_SCHEMA_VERSION",
    "STYLE_SPEC_SUFFIX",
    "UnknownStyleError",
    "resolve_style_spec",
    "style_spec",
    "style_spec_digest",
    "style_spec_path",
    "style_spec_text",
    "style_specs",
    "POLICY_KEY",
    "PolicyError",
    "check_policy",
    "layered_policy",
    "policy_of",
    "policy_problems",
    "style_pack",
]

#: The file suffix of a style spec in this package.
STYLE_SPEC_SUFFIX: str = ".yaml"

#: The ``schema_version`` the shipped specs carry: bumped when a key's meaning
#: changes, so a reader of a spec copied elsewhere knows which shape it holds.
STYLE_SPEC_SCHEMA_VERSION: str = "0.1.0"

#: What a style name may be: the spec's ``style`` key and its file's stem.
_STYLE_NAME = re.compile(r"[a-z][a-z0-9_]*")


class UnknownStyleError(KeyError):
    """No style spec of that name ships with ``cutan``.

    A ``KeyError`` (so a mapping or a ``ChainMap`` of spec sources falls through
    it), and so also a ``LookupError``.
    """

    def __str__(self) -> str:  # KeyError would repr() the message, quotes and all
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


def _is_style_name(ref: Any) -> bool:
    """Whether ``ref`` is spelled as a style's name: a string with no path
    separator and no suffix. Shipped or not; a ``Path`` is never a name.

    >>> _is_style_name('south_park'), _is_style_name('./south_park'), _is_style_name('x.yaml')
    (True, False, False)
    """
    if not isinstance(ref, str) or not ref:
        return False
    seps = {"/", os.sep} | ({os.altsep} if os.altsep else set())
    return not any(s in ref for s in seps) and not Path(ref).suffix


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
    """The file of the style spec ``name`` (for a tool that reads a path).

    Raises ``FileNotFoundError`` when ``cutan`` is imported from an archive
    (a zipped wheel), where the spec is not a file: use :func:`style_spec_text`.
    """
    path = Path(str(_resource(name)))
    if not path.is_file():
        raise FileNotFoundError(
            f"the style spec {name!r} is not a file on disk (cutan is imported from "
            f"an archive); read it with cutan.styles.style_spec_text({name!r})"
        )
    return path


def style_spec_text(name: str) -> str:
    """The YAML text of the style spec ``name``, comments included."""
    return _resource(name).read_text(encoding="utf-8")


def style_spec_digest(name: str) -> str:
    """The sha256 of the style spec ``name``'s file: the version a copy was made from.

    It hashes the file's bytes with line endings normalised to ``\\n`` (a
    Windows checkout has the same spec as the wheel), so a comment-only edit
    is a new version too.
    """
    data = _resource(name).read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


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


def resolve_style_spec(ref: str | os.PathLike | Mapping[str, Any]) -> dict[str, Any]:
    """A style spec as a dict, from whatever refers to one.

    - a mapping is passed through (a deep copy);
    - a string spelled as a name (no path separator, no suffix) is looked up
      by name in the spec sources — today the shipped specs only — and never
      read from a file in the working directory (spell a local file
      ``./south_park``);
    - anything else is a path to a YAML file.

    >>> resolve_style_spec('reiniger')['style']
    'reiniger'
    >>> resolve_style_spec({'targets': {}})
    {'targets': {}}

    A missing file whose stem is a shipped style says how to load that one:

    >>> resolve_style_spec('oversimplified.yaml')  # doctest: +ELLIPSIS
    Traceback (most recent call last):
      ...
    FileNotFoundError: no style spec file 'oversimplified.yaml' ...
    """
    if isinstance(ref, Mapping):
        return copy.deepcopy(dict(ref))
    if _is_style_name(ref):
        return style_spec(ref)
    path = Path(ref)
    if not path.is_file():
        hint = (
            f"; the shipped spec of that name is style_spec({path.stem!r}) "
            f"(pass the bare name {path.stem!r})"
            if path.stem in _spec_files()
            else ""
        )
        raise FileNotFoundError(f"no style spec file {str(ref)!r}{hint}")
    import yaml

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"style spec {ref} is not a mapping")
    return data


# The style's policy (cutan#9): imported last, it reads the specs through the functions above.
from cutan.styles.policy import (  # noqa: E402
    POLICY_KEY,
    PolicyError,
    check_policy,
    layered_policy,
    policy_of,
    policy_problems,
    style_pack,
)
