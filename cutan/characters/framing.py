"""Shot sizes from a character's own rig: where a close-up and a medium shot cut THIS build (cutan#106).

``an`` frames a viewpoint's ``size`` (``close_up``, ``medium``, ...) by a table on
human proportions (:data:`an.ir.schema.SHOT_SIZES`: a close-up is the top 35 %
of the subject's box). A factory character's head is about a third of its
height, a squat build's more, a tall one's less, so the table cuts them at the
wrong place. ``an`` asks a kind for its own bands (``EntityKind.shot_sizes``,
genre API level 14): :func:`character_shot_sizes` answers from the rig, by
compiling the character alone (its specimen shot, the path ``an`` measures its
box by) and reading where its head and torso are drawn:

- ``close_up``: from the top of the box to a little below the chin
  (:data:`CLOSE_UP_BELOW_CHIN` of the torso's height: the top of the shoulders);
- ``medium``: from the top to the bottom of the torso (the hips).

``wide`` and ``full`` stay the table's (the whole figure). A rig with no part
named ``head`` or ``torso`` gives no band for the sizes that need it, and the
table applies.
"""

from __future__ import annotations

import warnings
from collections.abc import Mapping
from typing import Any

#: How far below the chin a close-up's band ends, as a share of the torso's
#: drawn height: the top of the shoulders, so the head is not cut at the jaw.
CLOSE_UP_BELOW_CHIN: float = 0.25
#: The canvas the specimen is compiled on; the boxes are in scene pixels
#: relative to the placement point, which this does not change.
SPECIMEN_SIZE: tuple[int, int] = (1280, 720)
HEAD_PART: str = "head"
TORSO_PART: str = "torso"


def _part_boxes(entity: Any, mall: Mapping[str, Any]) -> dict[str, tuple[float, float, float, float]]:
    """``{part name: (x0, y0, x1, y1)}`` of the character's drawn nodes, in scene
    pixels relative to its placement point, as ``an.stage.world.native_box``
    measures the whole."""
    from an.stage.compile import compile_shot
    from an.stage.timeline import node_box, screen_position
    from an.stage.tree import walk_document

    from cutan.characters.registration import character_specimen

    bare = entity.model_copy(update={"stage": None, "joints": []})
    width, height = SPECIMEN_SIZE
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        doc = compile_shot(character_specimen(bare), mall=mall or {}, width=width, height=height)
    ox, oy = screen_position(doc, entity.id)
    out: dict[str, tuple[float, float, float, float]] = {}
    for path, _node in walk_document(doc):
        if not path.startswith(entity.id + "/"):
            continue
        box = node_box(doc, path)
        name = path.rsplit("/", 1)[-1]
        if box is not None and name not in out:  # the shallowest node of a name
            out[name] = (box[0] - ox, box[1] - oy, box[2] - ox, box[3] - oy)
    return out


def character_shot_sizes(
    entity: Any,
    mall: Mapping[str, Any],
    box: tuple[float, float, float, float],
    *,
    below_chin: float = CLOSE_UP_BELOW_CHIN,
) -> dict[str, tuple[float, float]] | None:
    """``{size: (top, bottom)}`` for ``entity``'s rig, as fractions of ``box``'s
    height from its top (``box``: its measured ``(x0, y0, x1, y1)``); ``None``
    when the rig has neither a head nor a torso to measure."""
    parts = _part_boxes(entity, mall)
    y0, y1 = float(box[1]), float(box[3])
    height = y1 - y0
    if height <= 0:
        return None

    def fraction(y: float) -> float:
        return min(1.0, max(0.0, (y - y0) / height))

    head, torso = parts.get(HEAD_PART), parts.get(TORSO_PART)
    bands: dict[str, tuple[float, float]] = {}
    if head is not None:
        chin = head[3]
        extra = below_chin * (torso[3] - torso[1]) if torso is not None else 0.0
        bands["close_up"] = (0.0, fraction(chin + extra))
    if torso is not None:
        bands["medium"] = (0.0, fraction(torso[3]))
    return {k: v for k, v in bands.items() if v[1] > v[0]} or None
