"""Shot sizes from a character's own rig: where a close-up and a medium shot cut THIS build (cutan#106).

``an`` frames a viewpoint's ``size`` (``close_up``, ``medium``, ...) by a table on
human proportions (:data:`an.ir.schema.SHOT_SIZES`: a close-up is the top 35 % of
the subject's box, about the chin of a person). A factory character's head is
about a third of its height, a squat build's more, a tall one's less, so the
table cuts them at the wrong place. ``an`` asks a kind for its own bands
(``EntityKind.shot_sizes``, genre API level 14): :func:`character_shot_sizes`
answers from the rig, by compiling the character alone (its specimen shot, the
path ``an`` measures its box by) and reading where its parts are drawn:

- ``medium``: from the top of the box to the bottom of the ``torso`` part itself
  (the hips; not its children: arms hang below it);
- ``close_up``: from the top to the chin, the lowest point of the ``head`` and
  everything drawn under it (a mouth below a small head box counts), but no
  lower than keeps a cut from medium to close-up a change of size an's
  jump-cut check accepts (``an.verify.constraints.JUMP_CUT_SIZE_RATIO``): a
  squat build's big head would otherwise make the two sizes nearly the same
  frame. (That holds where the frame is limited by height; a portrait frame
  limited by the subject's width gives every size one distance, in an:
  reeleehq/an#732.)

``wide`` and ``full`` stay the table's (the whole figure). A rig with no part
named ``head`` or ``torso`` (the art-package contract's names) gives no band for
the size that needs it, and the table applies.
"""

from __future__ import annotations

import hashlib
import json
import warnings
from collections.abc import Mapping
from typing import Any

#: The canvas the specimen is compiled on. The boxes are in scene pixels
#: relative to the placement point, which the canvas does not change.
SPECIMEN_SIZE: tuple[int, int] = (1280, 720)
HEAD_PART: str = "head"
TORSO_PART: str = "torso"
#: How far past an's jump-cut size ratio a capped close-up lands, so a ratio
#: computed back from the frames is never a hair under it (1.2999999...).
SIZE_RATIO_MARGIN: float = 1e-6
#: Part boxes kept per (store, ref, descriptor digest): ``an`` lowers a scene
#: several times per render, and each asks again.
_CACHE_SIZE: int = 64
_cache: dict[tuple[str, str, str], dict[str, tuple[float, float, float, float]]] = {}


def _descriptor_digest(entity: Any, mall: Mapping[str, Any]) -> str:
    try:
        doc = (mall or {}).get(entity.store, {})[entity.ref]
    except Exception:  # noqa: BLE001 - an unknown ref draws a placeholder: key it as such
        return "placeholder"
    return hashlib.sha256(
        json.dumps(doc, sort_keys=True, default=str).encode()
    ).hexdigest()


def _part_boxes(
    entity: Any, mall: Mapping[str, Any]
) -> dict[str, tuple[float, float, float, float]]:
    """``{node path below the character: (x0, y0, x1, y1)}`` of its drawn nodes, in
    scene pixels relative to its placement point, as
    ``an.stage.world.native_box`` measures the whole."""
    key = (str(entity.store), str(entity.ref), _descriptor_digest(entity, mall))
    if key in _cache:
        return _cache[key]
    from an.stage.compile import compile_shot
    from an.stage.timeline import node_box, screen_position
    from an.stage.tree import walk_document

    from cutan.characters.registration import character_specimen

    bare = entity.model_copy(update={"stage": None, "joints": []})
    width, height = SPECIMEN_SIZE
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        doc = compile_shot(
            character_specimen(bare), mall=mall or {}, width=width, height=height
        )
    ox, oy = screen_position(doc, entity.id)
    out: dict[str, tuple[float, float, float, float]] = {}
    for path, _node in walk_document(doc):
        if (
            path.startswith(entity.id + "/")
            and (box := node_box(doc, path)) is not None
        ):
            out[path[len(entity.id) + 1 :]] = (
                box[0] - ox,
                box[1] - oy,
                box[2] - ox,
                box[3] - oy,
            )
    if len(_cache) >= _CACHE_SIZE:
        _cache.pop(next(iter(_cache)))
    _cache[key] = out
    return out


def _lowest(
    parts: Mapping[str, tuple[float, float, float, float]], name: str, *, subtree: bool
) -> float | None:
    """The lowest point of the shallowest part named ``name``, and with
    ``subtree`` of everything drawn under it (a mouth below a small head box)."""
    paths = sorted(
        (p for p in parts if name in p.split("/")), key=lambda p: p.count("/")
    )
    if not paths:
        return None
    segments = paths[0].split("/")
    root = "/".join(segments[: segments.index(name) + 1])
    if not subtree:
        return parts[root][3] if root in parts else None
    ys = [
        box[3]
        for path, box in parts.items()
        if path == root or path.startswith(root + "/")
    ]
    return max(ys) if ys else None


def character_shot_sizes(
    entity: Any, mall: Mapping[str, Any], box: tuple[float, float, float, float]
) -> dict[str, tuple[float, float]] | None:
    """``{size: (top, bottom)}`` for ``entity``'s rig, as fractions of ``box``'s
    height from its top (``box``: its measured ``(x0, y0, x1, y1)``); ``None``
    when the rig has neither a head nor a torso to measure."""
    y0, y1 = float(box[1]), float(box[3])
    height = y1 - y0
    if height <= 0:
        return None
    parts = _part_boxes(entity, mall)

    def fraction(y: float) -> float:
        return min(1.0, max(0.0, (y - y0) / height))

    # the head with what is drawn under it; the torso alone (arms hang below it)
    chin = _lowest(parts, HEAD_PART, subtree=True)
    hips = _lowest(parts, TORSO_PART, subtree=False)
    bands: dict[str, tuple[float, float]] = {}
    if hips is not None:
        bands["medium"] = (0.0, fraction(hips))
    if chin is not None:
        bottom = fraction(chin)
        if "medium" in bands:
            from an.verify.constraints import JUMP_CUT_SIZE_RATIO

            least = JUMP_CUT_SIZE_RATIO * (1 + SIZE_RATIO_MARGIN)
            bottom = min(bottom, bands["medium"][1] / least)
        bands["close_up"] = (0.0, bottom)
    return {k: v for k, v in bands.items() if v[1] > v[0]} or None
