"""A character in ``nesting: bones`` (an#340): the genre's consumers of part paths.

The stage's chain rule (``an.stage.rig.slot_parent_chain``) is the one the
builder uses; cutan's part paths, face suppression, presets and analyser read
it too, so a ``nod``, a ``walk`` and a baked face address the nodes the builder
made.
"""

from __future__ import annotations

from an.stage.rig import RIG_HIERARCHY
from cutan.characters.play import (
    resolve_part_arg,
    slot_node_path,
    suppressed_slots,
)
from cutan.characters.schema import Bone, CharacterDescriptor
from cutan.library import character_affordances
from cutan.motion import WALK_LEG_NAMES, _limb_pair


def _chained(**kw) -> CharacterDescriptor:
    """The default rig with its head bone hung from the torso and the legs
    from the root, in `nesting: bones`."""
    desc = CharacterDescriptor(name="c", **kw)
    desc.nesting = "bones"
    return desc


def test_part_paths_follow_the_chain():
    flat = CharacterDescriptor(name="c")
    chained = _chained()
    assert slot_node_path(flat, "left_eye") == "head/left_eye"
    head = slot_node_path(chained, "head")
    assert slot_node_path(chained, "left_eye") == f"{head}/left_eye"


def test_a_baked_face_suppresses_the_face_not_a_part_on_a_child_bone_of_the_head():
    from cutan.characters.schema import Slot

    flat = CharacterDescriptor(name="c", face_overlay=False)
    chained = _chained(face_overlay=False)
    for desc in (flat, chained):
        desc.bones.append(Bone(name="hat", parent="head", y=-120))
        desc.slots.append(Slot(name="hat", bone="hat", draw_order=20))
    assert suppressed_slots(flat) == suppressed_slots(chained)
    assert "hat" not in suppressed_slots(chained) and "mouth" in suppressed_slots(chained)
    assert slot_node_path(chained, "hat") == "torso/head/hat"  # nested, not suppressed


def _bones_ready(doc: dict) -> dict:
    """``doc`` in `nesting: bones`, its draw orders renumbered in the tree's own
    paint order, so the stage can build it as declared."""
    from an.stage.rig import slot_parent_chain

    doc = {**doc, "nesting": "bones"}
    parents = slot_parent_chain(doc)
    order = {s["name"]: s.get("draw_order", 0) for s in doc["slots"]}
    kids: dict = {}
    for name in sorted(parents, key=lambda n: (order[n], n)):
        kids.setdefault(parents[name], []).append(name)
    painted, stack = [], list(reversed(kids.get(None, [])))
    while stack:
        name = stack.pop()
        painted.append(name)
        stack.extend(reversed(kids.get(name, [])))
    rank = {name: i for i, name in enumerate(painted)}
    doc["slots"] = [{**s, "draw_order": rank[s["name"]]} for s in doc["slots"]]
    return doc


def test_speech_pulse_moves_the_head_at_its_chain_path(tmp_path):
    """The review's critical finding (an#340): the pulse looked for
    `<speaker>/head`, so a bones-mode head (`torso/head`) fell back to pulsing
    the WHOLE BODY, silently, even under strict_assets."""
    import json
    import shutil
    import warnings

    from an.stage.compile import compile_shot
    from an.stage.timeline import evaluate_timeline, timeline_from_scene
    from an.stores.characters import CharactersStore
    from tests.test_methods_compile import FIXTURES, _speaking

    pulsed = {}
    for nesting in ("flat", "bones"):
        root = tmp_path / nesting
        shutil.copytree(FIXTURES / "gale", root / "baked")
        meta = root / "baked" / "character.json"
        doc = json.loads(meta.read_text(encoding="utf-8"))
        doc.update(face_overlay=False, speech="pulse")
        if nesting == "bones":
            doc = _bones_ready(doc)
        meta.write_text(json.dumps(doc), encoding="utf-8")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            scene = compile_shot(
                _speaking("baked"), {"characters": CharactersStore(root)}, strict_assets=True
            )
        pose = evaluate_timeline(timeline_from_scene(scene), 0.66)
        pulsed[nesting] = {k[0] for k, v in pose.items() if k[1] == "scale_y" and v != 1.0}
    assert pulsed["flat"] == {"g/head"}
    assert pulsed["bones"] == {"g/torso/head"}, "the head pulses, not the body"


def test_a_one_part_preset_finds_its_part_by_slot_name():
    assert resolve_part_arg("nod", {}, parts=["torso", "torso/head"])["part"] == "torso/head"


def test_a_walk_finds_its_legs_by_slot_name():
    pair = _limb_pair(None, WALK_LEG_NAMES, {"torso": {}, "root/left_leg": {}, "root/right_leg": {}})
    assert pair is not None and all("/" in p for p in pair)


def test_the_character_analyser_composes_rig_hierarchy():
    flat = CharacterDescriptor(name="c").model_dump(mode="json")
    assert RIG_HIERARCHY not in character_affordances(flat, art={})
    profile = character_affordances(_chained().model_dump(mode="json"), art={})
    # torso -> head and torso -> arms: two BONES deep; the face parts on the
    # head's own bone add no depth.
    assert profile[RIG_HIERARCHY]["count"] == 2
    assert {"torso", "head", "arm_l"} <= set(profile[RIG_HIERARCHY]["keys"])
