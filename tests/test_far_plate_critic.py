"""The vision critic of a travel's far plates (cutan#166). Offline: the judge is injected."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from PIL import Image

from an.ir.schema import Travel
from an.ir.world import World, WorldMember
from an.project import init, load
from cutan.verify.critic import FAR_PLATE_CHECKLIST, critique_far_plates

GOOD = json.dumps({"answers": [{"n": 1, "answer": "no"}, {"n": 2, "answer": "no"}, {"n": 3, "answer": "yes"}]})
TREES = json.dumps({"answers": [{"n": 1, "answer": "no"}, {"n": 2, "answer": "yes", "why": "a tree"}, {"n": 3, "answer": "no"}]})


@pytest.fixture()
def project():
    with tempfile.TemporaryDirectory() as d:
        root = init(Path(d) / "p")
        env = root / "assets" / "environments" / "road"
        (env / "plates").mkdir(parents=True)
        Image.new("RGB", (2400, 800), (120, 160, 220)).save(env / "plates" / "sky.png")
        Image.new("RGB", (64, 32), (90, 90, 90)).save(env / "plates" / "verge.jpg")
        (env / "plates" / "hills.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" width="4" height="4"/>')
        planes = [
            {"name": "sky", "art": {"kind": "image", "src": "plates/sky.png"}},
            {"name": "verge", "art": {"kind": "image", "src": "plates/verge.jpg"}},
            {"name": "hills", "art": {"kind": "image", "src": "plates/hills.svg"}},
            {"name": "tint", "art": {"kind": "fill", "color": "#ffffff"}},
            {"name": "escape", "art": {"kind": "image", "src": "../../../secret.png"}},
        ]
        (env / "meta.json").write_text(json.dumps({"kind": "EnvironmentDescriptor", "name": "road", "planes": planes}))
        p = load(root)
        far = ["set/sky", "set/verge", "set/hills", "set/tint", "set/escape", "set/nope"]
        p.scene.world = World(
            members=[WorldMember(kind="environment", id="set", store="environments", ref="road")],
            travel=Travel(plates={"far": far, "vehicle": []}),
        )
        yield p


class Judge:
    def __init__(self, reply):
        self.reply, self.shown = reply, []

    def __call__(self, frames, *, prompt):
        self.shown.append(frames)
        return self.reply


def test_only_raster_far_plates_are_judged_as_png_and_small(project):
    judge = Judge(GOOD)
    report = critique_far_plates(project, judge=judge)
    assert {f[0] for f in report.findings} == {"info"}, "the plates not judged are said"
    assert len(report.findings) == 4 and all("not judged" in f[2] for f in report.findings)
    assert [c["plate"] for c in report.calls] == ["set/sky", "set/verge"], "no SVG, fill, escape or unknown plane"
    for (png,) in judge.shown:
        assert png.startswith(b"\x89PNG")
        with Image.open(__import__("io").BytesIO(png)) as im:
            assert max(im.size) <= 1024


def test_a_plate_with_near_things_is_a_warning_on_its_travel_entry(project):
    report = critique_far_plates(project, judge=Judge(TREES))
    warnings = [f for f in report.findings if f[0] == "warning"]
    assert {f[1] for f in warnings} == {"world/travel/plates/far/0", "world/travel/plates/far/1"}
    assert any("a tree" in f[2] and "vehicle" in f[2] for f in report.findings)


def test_no_travel_no_call(project):
    project.scene.world = None
    judge = Judge(GOOD)
    assert critique_far_plates(project, judge=judge).calls == [] and judge.shown == []


def test_a_broken_judge_is_an_error(project):
    def broken(frames, *, prompt):
        raise RuntimeError("no key")

    report = critique_far_plates(project, judge=broken)
    assert [f[0] for f in report.findings if f[0] != "info"] == ["error", "error"]
    assert len(FAR_PLATE_CHECKLIST) == 3


def test_a_far_entry_on_a_member_that_is_not_an_environment_is_not_judged(project):
    project.scene.world.members.append(WorldMember(kind="prop", id="cup", store="props", ref="road", at=(0.0, 0.0, 5.0), height=0.2))
    project.scene.world.travel.plates["far"] = ["cup/sky"]
    judge = Judge(GOOD)
    report = critique_far_plates(project, judge=judge)
    assert judge.shown == [] and "not a plane of an environment" in report.findings[0][2]


def test_transparency_is_flattened_before_the_judge_sees_it(project, tmp_path):
    from cutan.verify.critic import PLATE_MATTE, _plate_png

    clear = tmp_path / "clear.png"
    Image.new("RGBA", (8, 8), (255, 0, 0, 0)).save(clear)
    with Image.open(__import__("io").BytesIO(_plate_png(clear))) as im:
        assert im.mode == "RGB" and im.getpixel((0, 0)) == PLATE_MATTE


def test_the_cli_says_when_nothing_was_judged(project, monkeypatch):
    from cutan import art_cli
    from cutan.verify import critic

    monkeypatch.setattr(critic, "critique_far_plates", lambda project, model=None: critic.CritiqueReport())
    assert art_cli.critique_plates(".") == "0 judge calls"


def test_a_plane_far_only_by_its_frame_is_judged_too(project):
    """cutan#177: the critic judges the set `an validate` pins to infinity
    (`an.ir.world.planes_at_infinity`), not only the planes the travel lists."""
    from an.ir.schema import Frame
    from an.ir.world import planes_at_infinity

    world = project.scene.world
    world.travel.plates["far"] = []
    world.members[0] = WorldMember(
        kind="environment", id="set", store="environments", ref="road",
        planes={"sky": "horizon"},
    )
    world.frames = {
        "car": Frame(),
        "far": Frame(parent="car", coupling="far"),
        "horizon": Frame(parent="far"),
    }
    judge = Judge(TREES)
    report = critique_far_plates(project, judge=judge)
    assert [c["plate"] for c in report.calls] == ["set/sky"]
    assert [p.path for p in planes_at_infinity(world, project.mall["environments"])] == ["set/sky"]
    # the finding points at the world member that puts the plane in the frame
    assert any(f[0] == "warning" and f[1] == "world/members/0" for f in report.findings)
