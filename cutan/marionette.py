"""The marionette style's joints: a control bar, strings, hips (cutan#104).

A marionette is a cut-out figure hung from strings: the figure's parts are
free bodies under gravity, the strings are the solver's ``string`` joints (a
distance held at most, so one may go slack), and the **control bar** is a prop
the author moves (``tween`` its ``x``, ``y``, ``rotation``): the figure follows
on its strings, swings, and settles. This is the first puppet style on the
constraint layer (an#497, ADR 0008); the table of what is tied where is the
style spec's ``joints`` block (:mod:`cutan.styles`, ``marionette.yaml``), and
this module turns it into the joints of one shot.

- :func:`write_control_bar` writes the bar prop, sized in scene pixels.
- :func:`marionette_joints` returns the shot's ``joints:``: one ``string`` per
  tied part and a hip hinge from each leg to the torso (the factory's legs hang
  from the root, not the torso, so nothing else joins them).

A shot then has the character with ``overrides: {free: true}`` (its parts hang
from the strings instead of staying where they were staged), the bar, those
joints, and the style pack's gravity (``meta.style_pack: marionette``):

.. code-block:: yaml

    entities:
      - {kind: character, id: ned, store: characters, ref: ned, overrides: {free: true}}
      - {kind: prop, id: bar, store: props, ref: control_bar, stage: {at: [0, -120], after: ned}}
    joints: <marionette_joints("ned", "bar")>
    actions:
      - {kind: tween, target: bar, property: x, from: 0, to: 150, duration: 1.5}

>>> [j["name"] for j in marionette_joints("ned", "bar")]
['ned.hip_l', 'ned.hip_r', 'ned.head', 'ned.hand_l', 'ned.hand_r', 'ned.knee_l', 'ned.knee_r']
>>> marionette_joints("ned", "bar")[2]
{'type': 'string', 'a': 'ned/head@0.5,0.0', 'b': 'bar@0.5,0.5', 'name': 'ned.head'}
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

__all__ = [
    "STYLE",
    "marionette_joints",
    "write_control_bar",
]

#: The style whose ``joints`` block holds the tables.
STYLE: str = "marionette"
#: The control bar's art box, in the prop's own units (a square canvas, as a prop's view box is).
_BAR_VIEW_BOX: float = 400.0
#: The bar's thickness as a fraction of its length.
_BAR_THICKNESS: float = 0.12


def _point(at: Any) -> str:
    """``@u,v`` for a fraction of a part's art, ``@bone`` for a bone's name.

    >>> _point([0.5, 0.0]), _point("hand_l")
    ('@0.5,0.0', '@hand_l')
    """
    if isinstance(at, str):
        return f"@{at}"
    u, v = at
    return f"@{float(u)!r},{float(v)!r}"


def _bone_names(rig: Any) -> set[str]:
    bones = (
        rig.get("bones") if isinstance(rig, Mapping) else getattr(rig, "bones", None)
    )
    return {
        str(b.get("name") if isinstance(b, Mapping) else b.name) for b in bones or ()
    }


def marionette_joints(
    character: str,
    bar: str,
    *,
    rig: Any = None,
    style: str | Mapping[str, Any] = STYLE,
    strings: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    """The ``joints:`` of a shot that hangs ``character`` from ``bar``.

    ``rig`` is the character's descriptor (a model or its document): a rig with
    ``hand_l``/``hand_r`` bones (``add_forearms``) is tied by its hands, else by
    the end of its arms. ``style`` is a spec (a shipped name or a mapping) whose
    ``joints`` block says what is tied where, so another puppet style reuses
    this builder with its own table; ``strings`` keeps only the named ones (a
    puppet with its knees untied). Each joint is a plain mapping a shot's
    ``joints`` accepts, named ``<character>.<string>``.

    >>> sorted({j["type"] for j in marionette_joints("ned", "bar")})
    ['hinge', 'string']
    >>> [j["a"] for j in marionette_joints("ned", "bar", strings=["hand_l"], rig={"bones": [{"name": "hand_l"}]})][-1]
    'ned/hand_l@hand_l'
    """
    from cutan.characters.limits import limits_for, limits_table
    from cutan.styles import resolve_style_spec

    spec = resolve_style_spec(style)
    block = spec.get("joints") or {}
    table = block.get("strings") or {}
    unknown = set(strings or ()) - set(table)
    if unknown:
        raise ValueError(
            f"style {spec.get('style')!r} ties no string named {sorted(unknown)}; "
            f"it ties: {', '.join(table)}"
        )
    have = _bone_names(rig) if rig is not None else set()
    give = float(block.get("give", 0.0))
    out: list[dict[str, Any]] = []
    if block.get("hips"):
        ranges = limits_table(spec)
        for side in ("l", "r"):
            lo, hi = limits_for(f"leg_{side}", table=ranges) or (-120.0, 120.0)
            out.append(
                {
                    "type": "hinge",
                    "a": f"{character}/leg_{side}@leg_{side}",
                    "b": f"{character}/torso@leg_{side}",
                    "limits": [lo, hi],
                    "name": f"{character}.hip_{side}",
                }
            )
    for name, tie in table.items():
        if strings is not None and name not in strings:
            continue
        part, at = tie["part"], tie["at"]
        better = tie.get("with_hands")
        if better and str(better["at"]) in have:
            part, at = better["part"], better["at"]
        joint: dict[str, Any] = {
            "type": "string",
            "a": f"{character}/{part}{_point(at)}",
            "b": f"{bar}{_point(tie['bar'])}",
            "name": f"{character}.{name}",
        }
        if give:
            joint["give"] = give
        out.append(joint)
    return out


def write_control_bar(
    props_dir: str | Path,
    name: str = "control_bar",
    *,
    width_px: float = 140.0,
    colour: str = "#6b4e2e",
) -> Path:
    """Write a control bar prop ``width_px`` wide at ``stage.scale: 1``; returns its folder.

    A plain horizontal bar, a drawing to replace with an illustrator's. The strings are tied to fractions of the bar's width
    (``bar: [u, v]`` in the style table), so a wider bar spreads them.

    >>> import tempfile
    >>> with tempfile.TemporaryDirectory() as d:
    ...     folder = write_control_bar(d, width_px=100)
    ...     sorted(p.name for p in folder.iterdir())
    ['parts', 'prop.json']
    """
    from an.stage.rig import SCENE_PX_PER_VIEW_BOX

    width = width_px / (SCENE_PX_PER_VIEW_BOX / _BAR_VIEW_BOX)
    height = width * _BAR_THICKNESS
    folder = Path(props_dir) / name
    (folder / "parts").mkdir(parents=True, exist_ok=True)
    centre = _BAR_VIEW_BOX / 2
    doc = {
        "kind": "PropDescriptor",
        "schema_version": "0.2.0",
        "name": name,
        "display_name": "A marionette's control bar",
        "view_box": [0, 0, _BAR_VIEW_BOX, _BAR_VIEW_BOX],
        "origin": [centre, centre],
        "bones": [{"name": "root", "x": centre, "y": centre}],
        "slots": [
            {"name": "bar", "bone": "root", "draw_order": 0, "attachment": "bar"}
        ],
        "skins": {
            "default": {
                "name": "default",
                "slots": {
                    "bar": {"bar": {"path": "parts/bar.svg", "anchor": [0.5, 0.5]}}
                },
            }
        },
    }
    (folder / "prop.json").write_text(json.dumps(doc, indent=2), encoding="utf-8")
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width:g} {height:g}" width="{width:g}" height="{height:g}">'
        f'<rect width="{width:g}" height="{height:g}" rx="{height / 2:g}" fill="{colour}" '
        'stroke="#222" stroke-width="2"/></svg>'
    )
    (folder / "parts" / "bar.svg").write_text(svg, encoding="utf-8")
    return folder
