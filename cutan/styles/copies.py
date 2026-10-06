"""Copies of a style spec, and whether they are stale (cutan#19).

A spec changes between cutan releases (targets re-measured, roles re-cast), and
what a production copies out of it is a snapshot: the StylePack
(:func:`cutan.styles.style_pack`), a voice cast to one of the spec's roles
(:func:`style_voice`), a kit's members built from them. Each copy records where
it came from in ``metadata.style_spec = {name, sha256}`` (:func:`spec_origin`),
and ``an validate`` compares that digest with the installed spec's
(:func:`check_style_copies`): a copy of an older spec is said, with what to
re-derive. A copy from a spec file, or one that records no digest, is never
compared (only a shipped spec has an installed version to compare with).

>>> spec_origin("south_park")["name"]
'south_park'
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

__all__ = [
    "SPEC_ORIGIN_KEY",
    "check_style_copies",
    "spec_origin",
    "stale_copy_problem",
    "style_voice",
]

#: Where a copy records the spec it came from, inside its ``metadata``.
SPEC_ORIGIN_KEY: str = "style_spec"


def spec_origin(spec: Any) -> dict[str, Any]:
    """``{name, sha256}`` of the spec ``spec`` names (a shipped style's name, a
    file), as a copy records it; no ``sha256`` for an in-memory mapping."""
    from cutan.styles import _is_style_name, resolve_style_spec, style_spec_digest

    origin: dict[str, Any] = {"name": resolve_style_spec(spec).get("style")}
    if _is_style_name(spec):
        origin["sha256"] = style_spec_digest(spec)
    elif not isinstance(spec, Mapping):  # a file: the shipped specs' digest rule
        raw = Path(spec).read_bytes().replace(b"\r\n", b"\n")
        origin["sha256"] = hashlib.sha256(raw).hexdigest()
    return origin


def style_voice(spec: Any, role: str) -> dict[str, Any]:
    """The partial voice document ``spec`` casts ``role`` as (``an.audio.takes.
    style_voice_role``: target names resolved to values), with the spec it came
    from recorded, so a later re-measure of the style is noticed. Merge it beside
    a ``voice_id``: ``{**style_voice("oversimplified", "eager"), "voice_id": ...}``.

    >>> doc = style_voice("oversimplified", "narrator")
    >>> doc["metadata"]["style_spec"]["name"], "targets" in doc["takes"]["cues"]["deadpan"]
    ('oversimplified', True)
    """
    from an.audio.takes import style_voice_role

    from cutan.styles import resolve_style_spec

    doc = style_voice_role(resolve_style_spec(spec), role)
    doc["metadata"] = {
        **(doc.get("metadata") or {}),
        SPEC_ORIGIN_KEY: spec_origin(spec),
    }
    return doc


def stale_copy_problem(doc: Any, *, what: str) -> str | None:
    """Why ``doc`` (a copy that recorded its spec) is stale, or ``None``: the
    shipped spec it names has changed since the copy was made."""
    from cutan.styles import style_spec_digest, style_specs

    meta = (
        doc.get("metadata")
        if isinstance(doc, Mapping)
        else getattr(doc, "metadata", None)
    ) or {}
    origin = meta.get(SPEC_ORIGIN_KEY) or {}
    name, recorded = origin.get("name"), origin.get("sha256")
    if not name or not recorded or name not in style_specs():
        return None  # only a shipped spec has an installed version to compare
    current = style_spec_digest(name)
    if recorded == current:
        return None
    return (
        f"{what} was copied from the {name!r} style spec at {recorded[:12]}, and the "
        f"installed spec is {current[:12]}: it no longer follows the spec "
        "(re-measured targets, re-cast roles)"
    )


#: How to re-derive each kind of copy (the `cutan-style` skill's steps).
_REDERIVE: dict[str, str] = {
    "pack": 're-save it: `mall["styles"][name] = cutan.styles.style_pack("{style}").model_dump(mode="json")` (cutan-style step 3)',
    "voice": 're-merge it: `{{**cutan.styles.style_voice("{style}", <role>), "voice_id": ...}}` (cutan-style step 8c)',
}


def check_style_copies(ctx) -> None:
    """``an validate``: the style pack the scene names, and every voice its lines
    speak with, warn when they were copied from an older version of the shipped
    spec they record (cutan#19). Once per validation."""
    stores = ctx.stores or {}
    styles = stores.get("styles")
    name = getattr(ctx.scene.meta, "style_pack", None)
    if styles is not None and name and name in styles:
        pack = styles[name]
        problem = stale_copy_problem(pack, what=f"style pack {name!r}")
        if problem:
            style = ((pack.get("metadata") or {}).get(SPEC_ORIGIN_KEY) or {}).get(
                "name"
            )
            ctx.report.add(
                "warning",
                "meta/style_pack",
                f"{problem}; {_REDERIVE['pack'].format(style=style)}",
            )
    voices = getattr(ctx, "voices", None)
    if voices is None:
        return
    refs = sorted(
        {
            line.voice_ref
            for shot in ctx.scene.timeline
            for line in shot.dialogue or ()
            if line.voice_ref
        }
    )
    for ref in refs:
        if ref not in voices:
            continue
        try:
            doc = voices[ref]
        except (KeyError, TypeError):
            continue
        problem = stale_copy_problem(doc, what=f"voice {ref!r}")
        if problem:
            style = (
                ((doc or {}).get("metadata") or {}).get(SPEC_ORIGIN_KEY) or {}
            ).get("name")
            ctx.report.add(
                "warning",
                f"voices/{ref}",
                f"{problem}; {_REDERIVE['voice'].format(style=style)}",
            )
