"""A cast as data: ``cast.yaml``, one entry per character, read by the factory (cutan#87).

A production pack used to carry its cast as ``cast.sh``, one ``an character``
shell line per step. ``cast.yaml`` says the same as data::

    mara:
      build: tall
      hair_style: bun
      palette: {skin: "#c08a5a", hair: "#2b1d14"}
      mouth_variants: [happy, sad]
      voice_ref: mara_voice
    teo:
      build: squat
      head_scale: 1.2
      hat: cap
      mouths: [angry]          # more mouth sets after the character is made
      half_lid: 0.5            # a half eyelid for squints

Each entry is the factory's options (``an character new``, always offline)
plus three follow-up steps (``mouths``, ``half_lid``, ``gaze``). The keys are
the ones :data:`cutan.pack.CAST_OPTIONS` allows a pack, so a cast file cannot
reach an option a ``cast.sh`` line could not.

:func:`cast_steps` reads a file or a mapping into :class:`CastStep`;
:meth:`CastStep.argv` is the ``an character`` command line (what a pack check
runs, behind the allow-list), and :func:`run_cast` runs the steps in this
process through the factory's own commands (``an character cast FILE``).

>>> [s.argv() for s in cast_steps({"teo": {"build": "squat", "hat": "cap", "half_lid": 0.5}})]
[['an', 'character', 'new', 'teo', '--offline', '--build', 'squat', '--hat', 'cap'], ['an', 'character', 'add-half-lid', 'teo', '--fraction', '0.5']]
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Union

CAST_YAML = "cast.yaml"
#: A character id: lowercase letters, digits, ``_``. ``\Z``, not ``$``: a name
#: ending in a newline would make a folder of that name.
NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,40}\Z")
#: The largest cast file read, and the longest value in it (characters): a
#: cast is a page of options, and a pack is checked on a server.
MAX_CAST_BYTES: int = 64 * 1024
MAX_VALUE_CHARS: int = 200
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")

#: The options of ``an character new`` a cast entry may set, by key, with the
#: type its value must have (a list joins with commas, a mapping as
#: ``key=value`` pairs). ``views: false`` is ``--no-views``.
NEW_OPTIONS: dict[str, tuple[type, ...]] = {
    "build": (str,),
    "head_scale": (int, float),
    "hat": (str,),
    "hair_style": (str,),
    "hair_length": (str,),
    "sash": (bool,),
    "palette": (str, Mapping),
    "clothing_pattern": (str,),
    "mouth_variants": (str, list),
    "views": (bool,),
    "voice_ref": (str,),
}
#: The follow-up steps an entry may ask for, by key: the ``an character``
#: subcommand, its option, and the value's type (``True`` for a step that
#: takes none).
FOLLOW_UPS: dict[str, tuple[str, str | None, tuple[type, ...]]] = {
    "mouths": ("mouths", "--variants", (str, list)),
    "half_lid": ("add-half-lid", "--fraction", (int, float)),
    "gaze": ("add-gaze", None, (bool,)),
}


class CastError(ValueError):
    """A cast file that cannot be read as a cast; the message names the entry."""


@dataclass(frozen=True)
class CastStep:
    """One factory step: ``an character <command> <name> <options>``."""

    command: str
    name: str
    options: dict[str, Any] = field(default_factory=dict)

    def kwargs(self) -> dict[str, Any]:
        """The factory command's keyword arguments (lists and mappings as the
        command's text; a new character is always made offline)."""
        out: dict[str, Any] = {"offline": True} if self.command == "new" else {}
        for key, value in self.options.items():
            out[key] = _text(value) if isinstance(value, (list, Mapping)) else value
        return out

    def argv(self) -> list[str]:
        """The ``an character`` command line of this step (from :meth:`kwargs`)."""
        args = ["an", "character", self.command, self.name]
        for key, value in self.kwargs().items():
            flag = "--" + key.replace("_", "-")
            if key == "views":
                if not value:
                    args.append("--no-views")
            elif value is True:
                args.append(flag)
            elif value is not False:
                args += [flag, str(value)]
        return args


def _text(value: Any) -> str:
    if isinstance(value, Mapping):
        return ",".join(f"{k}={v}" for k, v in value.items())
    if isinstance(value, list):
        return ",".join(str(v) for v in value)
    return str(value)


def _scalar_ok(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return True
    return (
        isinstance(value, str) and len(value) <= MAX_VALUE_CHARS and not _CONTROL.search(value)
    )


def _checked(name: str, key: str, value: Any, types: tuple[type, ...]) -> Any:
    """``value`` when it has one of ``types``; its items (a list's, a mapping's
    keys and values) short text or numbers; no control characters."""
    ok = isinstance(value, types) and not (isinstance(value, bool) and bool not in types)
    if ok and isinstance(value, str):
        ok = _scalar_ok(value)
    elif ok and isinstance(value, list):
        ok = len(value) <= MAX_VALUE_CHARS and all(_scalar_ok(v) for v in value)
    elif ok and isinstance(value, Mapping):
        ok = len(value) <= MAX_VALUE_CHARS and all(
            isinstance(k, str) and _scalar_ok(k) and _scalar_ok(v) for k, v in value.items()
        )
    if not ok:
        wanted = {
            (int, float): "number",
            (bool,): "true or false",
            (str,): f"short text (at most {MAX_VALUE_CHARS} characters, one line)",
        }.get(types, "short text, or a list or mapping of short text and numbers")
        raise CastError(f"{CAST_YAML} {name!r}: {key} must be a {wanted}, not {value!r}")
    return value


def _load_yaml(path: Path) -> Any:
    """A cast file's YAML, refusing what a cast never needs and a server must not
    expand: anchors and aliases (a few hundred bytes of them grow into gigabytes),
    tags, and a file over :data:`MAX_CAST_BYTES`."""
    import yaml

    with open(path, "rb") as f:  # read at most the cap: a FIFO or /dev/zero has no size
        data = f.read(MAX_CAST_BYTES + 1)
    if len(data) > MAX_CAST_BYTES:
        raise CastError(f"{CAST_YAML} is over {MAX_CAST_BYTES} bytes: a cast is a page")

    class _NoAliases(yaml.SafeLoader):
        def compose_node(self, parent, index):
            if self.check_event(yaml.AliasEvent):
                raise CastError(f"{CAST_YAML}: anchors and aliases (& and *) are not allowed")
            return super().compose_node(parent, index)

    try:
        return yaml.load(data.decode("utf-8"), Loader=_NoAliases)  # noqa: S506 - a SafeLoader
    except (yaml.YAMLError, ValueError) as e:  # ValueError: not UTF-8, an int too long
        raise CastError(f"{CAST_YAML} is not readable YAML: {e}") from None


def cast_steps(cast: Union[str, os.PathLike, Mapping[str, Any]]) -> list[CastStep]:
    """The factory steps of a cast file (or its mapping), in order: each
    character's ``new``, then its follow-ups. Raise :class:`CastError` on an
    unknown key, a wrong type or a name the factory would refuse.

    >>> cast_steps({"Teo": {}})
    Traceback (most recent call last):
    ...
    cutan.characters.cast.CastError: cast.yaml 'Teo': not a character name (lowercase letters, digits, _)
    """
    if not isinstance(cast, Mapping):
        cast = _load_yaml(Path(cast)) or {}
        if not isinstance(cast, Mapping):
            raise CastError(f"{CAST_YAML} holds a mapping {{name: options}}, not {type(cast).__name__}")
    steps: list[CastStep] = []
    for name, entry in cast.items():
        if not isinstance(name, str) or not NAME_RE.match(name):
            raise CastError(
                f"{CAST_YAML} {name!r}: not a character name (lowercase letters, digits, _)"
            )
        entry = {} if entry is None else entry
        if not isinstance(entry, Mapping):
            raise CastError(f"{CAST_YAML} {name!r}: an entry is a mapping of options, not {entry!r}")
        unknown = set(entry) - set(NEW_OPTIONS) - set(FOLLOW_UPS)
        if unknown:
            raise CastError(
                f"{CAST_YAML} {name!r}: unknown key(s) {sorted(unknown)}; allowed: "
                f"{', '.join([*NEW_OPTIONS, *FOLLOW_UPS])}"
            )
        new = {
            k: _checked(name, k, v, NEW_OPTIONS[k]) for k, v in entry.items() if k in NEW_OPTIONS
        }
        steps.append(CastStep("new", name, new))
        for key, (command, option, types) in FOLLOW_UPS.items():
            if key not in entry:
                continue
            value = _checked(name, key, entry[key], types)
            if option is None:
                if value:
                    steps.append(CastStep(command, name))
            else:
                steps.append(CastStep(command, name, {option.lstrip("-"): value}))
    return steps


def run_cast(
    cast: Union[str, os.PathLike, Mapping[str, Any]], *, out_dir: str = ""
) -> tuple[bool, list[str]]:
    """Run a cast's steps through the factory's own commands, in this process;
    ``(ok, one message per step)``. Stops at the first step that fails, since
    every later step of a cast builds on the earlier ones.
    """
    from cutan.characters import cli

    commands = {
        "new": cli.new,
        "mouths": cli.mouths,
        "add-half-lid": cli.add_half_lid,
        "add-gaze": cli.add_gaze,
    }
    messages = []
    for step in cast_steps(cast):
        label = " ".join(step.argv()[2:4])
        try:
            result = commands[step.command](step.name, out_dir=out_dir, **step.kwargs())
        except (OSError, ValueError) as e:  # the factory raises on some refusals
            messages.append(f"{label}: [error] {type(e).__name__}: {e}")
            return False, messages
        messages.append(f"{label}: {result}")
        if _is_failure(step, result):
            return False, messages
    return True, messages


def _is_failure(step: CastStep, result: Any) -> bool:
    """A failed exit status, or no word of success: some factory commands still
    return a plain report when they fail (the rule a pack check reads them by,
    :data:`cutan.pack.CAST_SUCCESS`)."""
    from an.cli_status import exit_code_of

    from cutan.pack import CAST_SUCCESS

    return exit_code_of(result) != 0 or CAST_SUCCESS[step.command] not in str(result)
