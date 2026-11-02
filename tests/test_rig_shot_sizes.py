"""Shot sizes from the rig (cutan#106): a close-up and a medium shot cut each build at its own chin and hips."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from an.genres.registry import entity_kind
from an.ir.schema import SHOT_SIZES, AssetRef
from an.project import init, load
from an.stage.world import native_box
from cutan.characters import new_character
from an.ir.world import WorldMember
from an.verify.constraints import JUMP_CUT_SIZE_RATIO
from cutan.characters.framing import MIN_SIZE_RATIO, _part_boxes, character_shot_sizes


@pytest.fixture(scope="module")
def project():
    with tempfile.TemporaryDirectory() as d:
        root = init(Path(d) / "p")
        for name, build, head in (("reg", "regular", 1.0), ("tall", "tall", 1.0), ("squat", "squat", 1.4)):
            new_character(root / "assets" / "characters", name=name, seed=name,
                          use_dicebear=False, build=build, head_scale=head)  # fmt: skip
        yield load(root)


def _sizes(project, name):
    ref = AssetRef(kind="character", id=name, store="characters", ref=name)
    box = native_box(ref, project.mall, width=1280, height=720)
    return ref, box, character_shot_sizes(ref, project.mall, box)


def test_the_character_kind_gives_its_own_shot_sizes():
    assert entity_kind("character").shot_sizes is character_shot_sizes


@pytest.mark.parametrize("name", ["reg", "tall", "squat"])
def test_a_close_up_ends_at_the_chin_and_a_medium_shot_at_the_hips(project, name):
    ref, box, sizes = _sizes(project, name)
    parts = _part_boxes(ref, project.mall)
    height = box[3] - box[1]
    chin = (max(b[3] for p, b in parts.items() if p == "head" or p.startswith("head/")) - box[1]) / height
    hips = (parts["torso"][3] - box[1]) / height
    assert sizes["medium"] == (0.0, pytest.approx(hips))
    top, bottom = sizes["close_up"]
    assert top == 0.0 and bottom <= chin + 1e-9
    assert bottom == pytest.approx(chin) or hips / bottom == pytest.approx(MIN_SIZE_RATIO)
    assert set(sizes) <= set(SHOT_SIZES)


@pytest.mark.parametrize("name", ["reg", "tall", "squat"])
def test_a_cut_from_medium_to_close_up_is_never_a_jump_cut(project, name):
    sizes = _sizes(project, name)[2]
    assert sizes["medium"][1] / sizes["close_up"][1] >= JUMP_CUT_SIZE_RATIO - 1e-9


def test_a_squat_build_is_framed_by_its_own_big_head_not_the_human_table(project):
    reg, squat = _sizes(project, "reg")[2], _sizes(project, "squat")[2]
    assert squat["close_up"][1] > reg["close_up"][1] + 0.15
    assert squat["close_up"][1] > SHOT_SIZES["close_up"][1] + 0.2


def test_the_world_hands_the_hook_a_member(project):
    ref, box, sizes = _sizes(project, "reg")
    member = WorldMember(kind="character", id="reg", store="characters", ref="reg", at=(0.0, 0.0, 5.0), height=1.8)
    assert character_shot_sizes(member, project.mall, box) == sizes


def test_the_hips_are_the_torso_part_not_the_arms_nested_under_it(monkeypatch, project):
    from cutan.characters import framing

    ref = AssetRef(kind="character", id="x", store="characters", ref="x")
    nested = {"torso": (-40.0, -20.0, 40.0, 40.0), "torso/arm_l": (-60.0, -20.0, -40.0, 90.0),
              "torso/head": (-30.0, -100.0, 30.0, -30.0), "torso/head/mouth": (-5.0, -40.0, 5.0, -20.0)}  # fmt: skip
    monkeypatch.setattr(framing, "_part_boxes", lambda entity, mall: nested)
    sizes = character_shot_sizes(ref, project.mall, (-60.0, -100.0, 60.0, 100.0))
    assert sizes["medium"] == (0.0, 0.7), "the torso's bottom, not the hand's"
    assert sizes["close_up"] == (0.0, 0.4), "the chin is the mouth below the head box"


def test_a_rig_without_a_head_or_torso_leaves_those_sizes_to_the_table(project, monkeypatch):
    from cutan.characters import framing

    ref = AssetRef(kind="character", id="x", store="characters", ref="x")
    box = (-50.0, -100.0, 50.0, 100.0)
    monkeypatch.setattr(framing, "_part_boxes", lambda entity, mall: {})
    assert character_shot_sizes(ref, project.mall, box) is None
    monkeypatch.setattr(framing, "_part_boxes", lambda entity, mall: {"torso": (-40.0, -20.0, 40.0, 40.0)})
    assert character_shot_sizes(ref, project.mall, box) == {"medium": (0.0, 0.7)}
