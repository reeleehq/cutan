"""The rig view from the camera's yaw (cutan#173 part 1, an#734)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from an.genres.registry import entity_kind
from an.ir.schema import AssetRef, Meta, Resolution, SceneIR, Shot, Viewpoint, World, WorldMember
from an.project import init, load
from cutan.characters import new_character
from cutan.characters.views import VIEW_YAW_RANGES, character_view_for, view_for_yaw

pytestmark = pytest.mark.skipif(
    not hasattr(entity_kind("character"), "view_for"), reason="needs an.genres.API_LEVEL >= 20"
)


@pytest.fixture(scope="module")
def project():
    with tempfile.TemporaryDirectory() as d:
        root = init(Path(d) / "p")
        chars = root / "assets" / "characters"
        new_character(chars, name="ned", seed="ned", use_dicebear=False)  # draws its views
        new_character(chars, name="flat", seed="flat", use_dicebear=False, views=False)
        yield load(root)


def _view(project, name, yaw):
    ref = AssetRef(kind="character", id=name, store="characters", ref=name)
    acts = character_view_for(ref, project.mall, yaw)
    return None if acts is None else acts[0].value


def test_the_character_kind_answers_the_hook():
    assert entity_kind("character").view_for is character_view_for


@pytest.mark.parametrize(
    "yaw, want",
    [(0, "front"), (10, "front"), (45, "three_quarter"), (90, "side"), (135, "back"), (180, "back"), (-180, "back"), (-10, "front")],
)
def test_the_ranges_pick_the_view(project, yaw, want):
    assert _view(project, "ned", yaw) == want


def test_a_screen_left_profile_is_not_shown_facing_the_wrong_way(project):
    # a mirror, which a view's actions cannot give yet (reeleehq/an#868): the front
    assert _view(project, "ned", -90) == "front"
    assert _view(project, "ned", -45) == "front"
    assert _view(project, "ned", -135) == "back"


def test_art_that_faces_left_takes_its_profile_on_the_left(project):
    ref = AssetRef(kind="character", id="ned", store="characters", ref="ned", overrides={"faces": "left"})
    value = lambda yaw: (character_view_for(ref, project.mall, yaw) or [None])[0]  # noqa: E731
    assert value(-90).value == "side"
    assert value(90).value == "front"


def test_no_mall_is_no_view():
    ref = AssetRef(kind="character", id="ned", store="characters", ref="ned")
    assert character_view_for(ref, None, 90.0) is None


def test_a_character_without_views_is_left_alone(project):
    assert _view(project, "flat", 90) is None


def test_the_bounds_are_the_midpoints_between_the_drawn_views():
    assert [v for _, v in VIEW_YAW_RANGES] == ["front", "three_quarter", "side", "back"]
    assert view_for_yaw(40.0, available=("front", "side")) == "front"


def test_a_framed_shot_shows_the_view_the_camera_sees(project):
    """End to end through an's lowering: facing the camera is front, turned a quarter is side."""
    from an.stage.world import lower_scene

    def lowered(facing):
        world = World(
            members=[WorldMember(kind="character", id="ned", store="characters", ref="ned",
                                 at=(0.0, 0.0, 6.0), height=1.8, facing=facing)],
            viewpoints={"cam": Viewpoint(at=(0.0, -1.0, 0.0), focal=600.0)},
        )  # fmt: skip
        scene = SceneIR(
            meta=Meta(fps=24, resolution=Resolution(width=1280, height=720)),
            world=world,
            timeline=[Shot(id="s", duration=1.0, viewpoint="cam", actions=[])],
        )
        return lower_scene(scene, project.mall).scene.timeline[0]

    def views(shot):
        return [a.value for a in shot.actions if getattr(a, "property", None) == "view"]

    assert views(lowered(180.0)) == ["front"]
    assert views(lowered(90.0)) == ["side"]
    assert views(lowered(None)) == []
