"""A character's feet as contacts for an's ``support`` check (cutan#201, an#519)."""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

import pytest
from an.ir.schema import AssetRef, Shot, StagePlacement
from an.ir.validate import validate_semantic
from an.project import init, load

from cutan.characters.factory import new_character
from cutan.characters.registration import PlayAction

GROUND = 400.0
#: Where `stage.at` puts the factory character's feet on the ground at scale 1.
STANDING_Y = 305.7
SUPPORT = [{"type": "support", "a": "paul", "b": "ground"}]
CHECKS = {"support", "unknown_body", "floating_item"}


@pytest.fixture(scope="module")
def project():
    with tempfile.TemporaryDirectory() as d:
        root = init(Path(d) / "p")
        new_character(root / "assets" / "characters", name="paul", seed="paul", use_dicebear=False)
        yield load(root)


def _findings(project, *, y: float, actions=(), duration=1.0) -> list[str]:
    paul = AssetRef(
        kind="character", id="paul", store="characters", ref="paul",
        stage=StagePlacement(at=(320.0, y), scale=1.0),
    )
    shot = Shot(
        id="s", renderer="cutout", duration=duration, entities=[paul],
        actions=list(actions), joints=SUPPORT, solve={"ground": GROUND},
    )
    scene = project.scene.model_copy(update={"timeline": [shot]})
    report = validate_semantic(
        scene, available_characters=project.mall["characters"], only=CHECKS
    )
    return [f.description for f in report.findings]


def test_a_standing_character_passes_the_support_check(project):
    assert _findings(project, y=STANDING_Y) == []


def test_a_character_lifted_ten_px_floats(project):
    (msg,) = _findings(project, y=STANDING_Y - 10)
    assert "floats 10.0 px above `ground`" in msg


def test_a_character_sunk_into_the_floor_is_reported_at_its_foot(project):
    (msg,) = _findings(project, y=STANDING_Y + 10)
    assert "`foot_l` is 10.0 px into `ground`" in msg


def test_the_factory_walks_hip_swing_lifts_a_foot_a_few_px_and_never_sinks_it(project):
    """The measurement cutan#201 asks for: at the contact pose the swung leg's far end
    is ``L (1 - cos stride)`` off the floor (about 6 px on the factory rig)."""
    walk = PlayAction(
        target="paul", animation="walk",
        args={"steps": 4, "step_s": 0.5, "distance": 0}, start=0.0,
    )
    found = _findings(project, y=STANDING_Y, actions=[walk], duration=3.0)
    assert found and not any("into" in m for m in found)
    lifts = [float(m) for f in found for m in re.findall(r"floats ([\d.]+) px", f)]
    assert lifts and max(lifts) < 8.0
