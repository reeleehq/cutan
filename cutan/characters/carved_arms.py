"""Split a carved character's one-stroke raster arms at the elbow (cutan#208).

The factory's :func:`cutan.characters.factory.add_forearms` splits an arm it drew
itself (an SVG sleeve and a round hand). A character carved from a video frame has
arms that are pixels: the OverSimplified persona's arms are one black stroke each,
a ``(`` and a ``)`` beside the body, with no drawn hand. Such an arm can still bend
at the elbow, the way OverSimplified draws a figure carrying a cup (the upper arm
down the side, the forearm across the front):

- each arm's drawing is cut across the stroke at ``elbow_at`` of its painted
  length: the upper part keeps the ``arm_*`` slot and bone, the lower part becomes
  a ``forearm_*`` slot on a ``forearm_*`` bone hinged at the stroke's centre line
  on the cut, so at rest the arm looks exactly as it did;
- both halves get a round cap of the stroke's own ink on the cut (the stroke's
  width, its median colour), so the elbow reads as a joint at any bend instead of
  showing the flat ends of the cut;
- the hand is a slotless ``hand_*`` bone at the end of the stroke (half a stroke
  width back from its last painted row, on the centre line), so ``stu@hand_r``
  holds things exactly at the end of the drawn arm;
- the rig turns to ``nesting: bones``, so a forearm follows its upper arm.

**Nesting changes what a swap pose hides.** Under ``nesting: bones`` a slot on a
child bone draws inside its parent's part: the carved persona's ``face`` slot (on
a ``face`` bone under ``head``) would draw inside the head, so a face pose that
hides the head (``head: {alpha: 0}``: the drawn face replaces the round head) would
hide the face as well. :func:`split_carved_arms` hoists such a bone to the hidden
part's parent (the ``face`` bone under the torso, at the same rest place), as the
flat rig drew it, and reports it. A hoisted face does not turn with a tween of the
head: tween it as well (``stu/torso/face``).

Opt-in, one character at a time; idempotent at the same ``elbow_at``. The new
part files are derived from the character's own art and keep its provenance (the
descriptor's ``source``); ``metadata.arms`` records ``"split-carved"``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

__all__ = [
    "CARVED_ELBOW_AT",
    "RASTER_SUFFIXES",
    "ArmSplit",
    "CarvedArmsReport",
    "has_raster_arms",
    "split_carved_arms",
]

#: Where the elbow sits on the painted length of the stroke, shoulder to hand.
CARVED_ELBOW_AT: float = 0.5
#: Part files this module can cut (what :mod:`cutan.carve` writes).
RASTER_SUFFIXES: tuple[str, ...] = (".png", ".webp")
#: Alpha above which a pixel is the stroke's ink.
INK_ALPHA: int = 128
#: Supersampling of the elbow cap's disc (antialiased edge).
CAP_SUPERSAMPLE: int = 8
SIDES: tuple[str, ...] = ("l", "r")


@dataclass(frozen=True)
class ArmSplit:
    """Where one arm was cut, in its drawing's pixels: the elbow (on the stroke's
    centre line at the cut), the hand (the end of the stroke) and the stroke's
    width at the elbow."""

    side: str
    elbow: tuple[float, float]
    hand: tuple[float, float]
    stroke_width: float


@dataclass(frozen=True)
class CarvedArmsReport:
    """What :func:`split_carved_arms` did: the descriptor written, each arm's cut,
    and the bones it hoisted out of a part a swap pose hides (``(bone, from, to)``)."""

    descriptor: Path
    arms: tuple[ArmSplit, ...] = ()
    hoisted: tuple[tuple[str, str, str], ...] = field(default=())
    already_split: bool = False


def _arm_attachment(desc: Any, side: str):
    arm = f"arm_{side}"
    slot = next((s for s in desc.slots if s.name == arm), None)
    if slot is None:
        return None
    return desc.skins["default"].slots.get(arm, {}).get(slot.attachment)


def has_raster_arms(desc: Any) -> bool:
    """Whether both of ``desc``'s arms are drawn as raster images (a carved rig).

    >>> from types import SimpleNamespace as NS
    >>> att = lambda p: {"a": NS(path=p)}
    >>> rig = NS(slots=[NS(name="arm_l", attachment="a"), NS(name="arm_r", attachment="a")],
    ...          skins={"default": NS(slots={"arm_l": att("parts/arm_l.png"), "arm_r": att("parts/arm_r.png")})})
    >>> has_raster_arms(rig)
    True
    >>> rig.skins["default"].slots["arm_r"] = att("parts/arm_r.svg")
    >>> has_raster_arms(rig)
    False
    """
    for side in SIDES:
        att = _arm_attachment(desc, side)
        if att is None or Path(att.path).suffix.lower() not in RASTER_SUFFIXES:
            return False
    return True


def _cut_geometry(alpha, elbow_at: float):
    """``(elbow_row, elbow_x, width, hand_x, hand_y)`` of a stroke whose ink is
    ``alpha > INK_ALPHA``: the cut at ``elbow_at`` of its painted rows, the stroke's
    centre and width on that row, and the hand on the centre line half a width
    back from the last painted row."""
    import numpy as np

    ink = alpha > INK_ALPHA
    rows = np.where(ink.any(axis=1))[0]
    if len(rows) < 3:
        raise ValueError("the arm's drawing has no stroke to cut (too little ink)")
    top, bottom = int(rows[0]), int(rows[-1])
    elbow = int(round(top + elbow_at * (bottom - top)))

    def centre(row: int) -> tuple[float, float]:
        cols = np.where(ink[row])[0]
        if not len(cols):
            raise ValueError(f"the arm's stroke is broken at row {row}: no ink to cut")
        return (float(cols[0] + cols[-1]) / 2.0, float(cols[-1] - cols[0] + 1))

    ex, width = centre(elbow)
    hand_y = max(float(elbow), bottom - width / 2.0)
    hx, _ = centre(int(round(hand_y)))
    return elbow, ex, width, hx, hand_y


def _halves(img, elbow: int, ex: float, width: float):
    """The upper and the lower part of the drawing, each with a cap on the cut."""
    import numpy as np
    from PIL import Image, ImageDraw

    a = np.array(img.convert("RGBA"))
    opaque = a[a[:, :, 3] > INK_ALPHA][:, :3]
    ink = tuple(int(v) for v in np.median(opaque, axis=0)) + (255,)
    w, h = img.size
    r = width / 2.0
    s = CAP_SUPERSAMPLE
    disc = Image.new("RGBA", (w * s, h * s), (0, 0, 0, 0))
    ImageDraw.Draw(disc).ellipse(
        [(ex - r) * s, (elbow - r) * s, (ex + r) * s, (elbow + r) * s], fill=ink
    )
    disc = disc.resize((w, h), Image.LANCZOS)
    upper, lower = a.copy(), a.copy()
    upper[elbow + 1 :, :, 3] = 0
    lower[:elbow, :, 3] = 0
    out = []
    for part in (upper, lower):
        im = Image.fromarray(part)
        im.alpha_composite(disc)
        out.append(im)
    return out


def _ancestors(bone: str, parent_of: Mapping[str, str | None]):
    seen, cursor = {bone}, parent_of.get(bone)
    while cursor is not None and cursor not in seen:
        seen.add(cursor)
        yield cursor
        cursor = parent_of.get(cursor)


def _primary_slots(desc: Any) -> dict[str, str]:
    """``{bone: slot}``: the part a child bone's slots draw inside under ``nesting:
    bones`` (the slot named like the bone, else its first in draw order; the other
    slots on that bone ride beside it)."""
    primary: dict[str, str] = {}
    for s in sorted(desc.slots, key=lambda x: (x.draw_order, x.name)):
        primary.setdefault(s.bone, s.name)
    for s in desc.slots:
        if s.name == s.bone:
            primary[s.bone] = s.name
    return primary


def _compose(outer: Any, inner: Any) -> dict[str, float]:
    """``inner``'s rest transform (x, y, rotation_deg, scale) in ``outer``'s parent's frame."""
    import math

    a = math.radians(outer.rotation_deg)
    ix, iy = inner.x * outer.scale_x, inner.y * outer.scale_y
    return {
        "x": round(outer.x + ix * math.cos(a) - iy * math.sin(a), 6),
        "y": round(outer.y + ix * math.sin(a) + iy * math.cos(a), 6),
        "rotation_deg": outer.rotation_deg + inner.rotation_deg,
        "scale_x": outer.scale_x * inner.scale_x,
        "scale_y": outer.scale_y * inner.scale_y,
    }


def _hoist_out_of_hidden_parts(desc: Any) -> tuple[tuple[str, str, str], ...]:
    """Re-parent each bone whose drawing a swap pose SHOWS while the same pose
    HIDES (``alpha`` 0) a part that bone would draw inside under ``nesting: bones``
    (a drawn face on a ``face`` bone under the head, whose pose hides the head),
    to that part's own parent bone, at the same rest place: the flat rig drew it
    beside the hidden part, and so does the nested one. ``(bone, from, to)`` for each."""
    bones = {b.name: b for b in desc.bones}
    slot_bone = {s.name: s.bone for s in desc.slots}
    primary = _primary_slots(desc)
    skin = desc.skins["default"].slots
    hoisted: list[tuple[str, str, str]] = []
    for set_name, per_key in (desc.swap_poses or {}).items():
        mapping = (desc.asset_sets or {}).get(set_name) or {}
        for key, pose in per_key.items():
            attachment = mapping.get(key)
            if attachment is None:
                continue
            hidden = {s for s, p in pose.items() if getattr(p, "alpha", 1.0) == 0}
            for slot in [n for n, atts in skin.items() if attachment in atts]:
                bone = slot_bone.get(slot)
                parent_of = {b.name: b.parent for b in bones.values()}
                chain = list(_ancestors(bone, parent_of))
                hide_at = [i for i, a in enumerate(chain) if primary.get(a) in hidden]
                if not hide_at:
                    continue
                outer = chain[max(hide_at)]  # the outermost hidden part it draws inside
                moved = bones[bone]
                for a in chain[: max(hide_at) + 1]:  # fold the chain up to `outer` into it
                    moved = moved.model_copy(update={**_compose(bones[a], moved), "parent": bones[a].parent})
                hoisted.append((bone, bones[bone].parent, moved.parent))
                bones[bone] = moved
    desc.bones = [bones[b.name] for b in desc.bones]
    return tuple(hoisted)


def split_carved_arms(
    char_dir: str | Path, *, elbow_at: float = CARVED_ELBOW_AT
) -> CarvedArmsReport:
    """Split a carved character's raster one-stroke arms at the elbow (see the module docstring).

    Writes ``parts/arm_<side>_upper.png`` and ``parts/forearm_<side>.png`` next to the
    character's parts, the bones ``forearm_<side>`` (hinged at the cut) and
    ``hand_<side>`` (slotless, at the stroke's end), the ``forearm_<side>`` slots
    (drawn just above their upper arm), and ``nesting: bones``. Refuses a rig whose
    arms are not raster drawings, one already nested, and an ``elbow_at`` outside
    0.1..0.9. Idempotent at the same ``elbow_at``.
    """
    from PIL import Image

    from cutan.characters.descriptor_io import load_descriptor, write_descriptor
    from cutan.characters.schema import Attachment, Bone, Slot

    if not 0.1 <= elbow_at <= 0.9:
        raise ValueError(f"elbow_at {elbow_at} must be within 0.1..0.9 of the stroke")
    char_dir = Path(char_dir)
    desc = load_descriptor(char_dir)
    bones = {b.name: b for b in desc.bones}
    meta = desc.metadata
    if all(f"forearm_{s}" in bones for s in SIDES):
        if meta.get("arms") == "split-carved" and abs(
            float(meta.get("elbow_at", CARVED_ELBOW_AT)) - elbow_at
        ) < 1e-9:
            return CarvedArmsReport(write_descriptor(char_dir, desc), already_split=True)
        raise ValueError(
            f"{desc.name!r}'s arms are already split; split them again from the "
            "unsplit character to cut them elsewhere"
        )
    if not has_raster_arms(desc):
        raise ValueError(
            f"{desc.name!r}'s arms are not raster drawings: a factory arm is split by "
            "`add_forearms`"
        )
    if desc.nesting not in (None, "flat"):
        raise ValueError(f"{desc.name!r} is already nested by {desc.nesting!r}")
    if any(f"hand_{s}" in bones or f"forearm_{s}" in bones for s in SIDES):
        raise ValueError(f"{desc.name!r} has a forearm or a hand bone already")

    skin = desc.skins["default"].slots
    splits: list[ArmSplit] = []
    for side in SIDES:
        arm = f"arm_{side}"
        att = _arm_attachment(desc, side)
        img = Image.open(char_dir / att.path).convert("RGBA")
        import numpy as np

        elbow, ex, width, hx, hy = _cut_geometry(np.array(img)[:, :, 3], elbow_at)
        upper, lower = _halves(img, elbow, ex, width)
        w, h = img.size
        up_rel = f"parts/{arm}_upper{Path(att.path).suffix}"
        fo_rel = f"parts/forearm_{side}{Path(att.path).suffix}"
        upper.save(char_dir / up_rel)
        lower.save(char_dir / fo_rel)
        ax, ay = att.anchor[0] * w, att.anchor[1] * h
        slot = next(s for s in desc.slots if s.name == arm)
        skin[arm][slot.attachment] = att.model_copy(update={"path": up_rel})
        skin[f"forearm_{side}"] = {
            f"forearm_{side}": Attachment(path=fo_rel, anchor=(ex / w, elbow / h))
        }
        desc.bones += [
            Bone(
                name=f"forearm_{side}",
                parent=arm,
                pivot=f"elbow_{side}",
                x=round(ex - ax + att.x, 3),
                y=round(elbow - ay + att.y, 3),
            ),
            Bone(
                name=f"hand_{side}",
                parent=f"forearm_{side}",
                x=round(hx - ex, 3),
                y=round(hy - elbow, 3),
            ),
        ]
        desc.slots.append(
            Slot(
                name=f"forearm_{side}",
                bone=f"forearm_{side}",
                draw_order=slot.draw_order,
                attachment=f"forearm_{side}",
            )
        )
        splits.append(ArmSplit(side, (ex, float(elbow)), (hx, hy), width))
    desc.nesting = "bones"
    meta["arms"] = "split-carved"
    if elbow_at != CARVED_ELBOW_AT:
        meta["elbow_at"] = elbow_at
    hoisted = _hoist_out_of_hidden_parts(desc)
    return CarvedArmsReport(write_descriptor(char_dir, desc), tuple(splits), hoisted)
