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
    assert report.findings == []
    assert [c["plate"] for c in report.calls] == ["set/sky", "set/verge"], "no SVG, fill, escape or unknown plane"
    for (png,) in judge.shown:
        assert png.startswith(b"\x89PNG")
        with Image.open(__import__("io").BytesIO(png)) as im:
            assert max(im.size) <= 1024


def test_a_plate_with_near_things_is_a_warning_on_its_travel_entry(project):
    report = critique_far_plates(project, judge=Judge(TREES))
    assert {f[0] for f in report.findings} == {"warning"}
    assert {f[1] for f in report.findings} == {"world/travel/plates/far/0", "world/travel/plates/far/1"}
    assert any("a tree" in f[2] and "vehicle" in f[2] for f in report.findings)


def test_no_travel_no_call(project):
    project.scene.world = None
    judge = Judge(GOOD)
    assert critique_far_plates(project, judge=judge).calls == [] and judge.shown == []


def test_a_broken_judge_is_an_error(project):
    def broken(frames, *, prompt):
        raise RuntimeError("no key")

    report = critique_far_plates(project, judge=broken)
    assert [f[0] for f in report.findings] == ["error", "error"]
    assert len(FAR_PLATE_CHECKLIST) == 3
