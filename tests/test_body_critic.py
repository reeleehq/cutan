"""The optional vision critic of body-depicting props (cutan#95).

Offline: the frames and the judge are injected; nothing renders or calls a model.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from PIL import Image

from an.ir.schema import AssetRef, Shot, StagePlacement
from an.project import init, load
from cutan.body_attachment import BODY_ATTACHMENT_KEY
from cutan.characters import new_character
from cutan.verify.critic import BODY_CHECKLIST, critique_body_props

SOCKETS = [{"bone": "arm_l", "at": [0.25, -0.6]}, {"bone": "arm_r", "at": [0.75, -0.6]}]


def _prop(root: Path, name: str, metadata: dict) -> None:
    d = root / "assets" / "props" / name
    (d / "parts").mkdir(parents=True)
    Image.new("RGBA", (40, 20), (0, 0, 0, 255)).save(d / "parts" / "art.png")
    doc = {
        "kind": "PropDescriptor",
        "name": name,
        "slots": [{"name": "body", "bone": "root", "attachment": "art"}],
        "skins": {"default": {"slots": {"body": {"art": {"path": "parts/art.png"}}}}},
        "metadata": metadata,
    }
    (d / "prop.json").write_text(json.dumps(doc), encoding="utf-8")


@pytest.fixture(scope="module")
def project():
    with tempfile.TemporaryDirectory() as d:
        root = init(Path(d) / "p")
        new_character(root / "assets" / "characters", name="ned", seed="ned", use_dicebear=False)
        _prop(root, "wheel", {BODY_ATTACHMENT_KEY: {"character": "ned", "view": "front", "sockets": SOCKETS}})
        _prop(root, "cup", {})  # depicts no body: never asked about
        p = load(root)

        def entity(kind, id_, ref, store):
            return AssetRef(kind=kind, id=id_, store=store, ref=ref, stage=StagePlacement(at=(0.0, 0.0), scale=1.0))

        shots = [
            Shot(id="drive", renderer="cutout", duration=2.0,
                 entities=[entity("character", "ned", "ned", "characters"), entity("prop", "w", "wheel", "props")]),
            Shot(id="tea", renderer="cutout", duration=1.0,
                 entities=[entity("character", "ned", "ned", "characters"), entity("prop", "c", "cup", "props")]),
        ]  # fmt: skip
        p.scene = p.scene.model_copy(update={"timeline": shots})
        yield p


class Judge:
    def __init__(self, reply):
        self.reply, self.prompts = reply, []

    def __call__(self, frames, *, prompt):
        self.prompts.append(prompt)
        return self.reply


def _frames(probed):
    def frames(project, shot, times):
        probed.append((shot, list(times)))
        return [b"png"] * len(times)

    return frames


def _reply(*answers):
    return json.dumps({"answers": [{"n": n, "answer": a, "why": "seen"} for n, a in enumerate(answers, 1)]})


def test_a_correct_drawing_gives_no_finding_and_only_body_props_are_asked(project):
    probed, judge = [], Judge(_reply("yes", "no", "yes"))
    report = critique_body_props(project, judge=judge, frames=_frames(probed), at=(0.25, 0.75))
    assert report.findings == []
    assert probed == [("drive", [0.5, 1.5])], "only the shot with a body-depicting prop"
    assert report.calls == [{"shot": "drive", "prop": "w", "frames": 2, "model": None}]
    assert "w" in judge.prompts[0] and "ned" in judge.prompts[0]


def test_a_drawing_from_the_wrong_side_is_a_warning_never_an_error(project):
    report = critique_body_props(
        project, judge=Judge(_reply("no", "yes", "unsure")), frames=_frames([])
    )
    severities = [f[0] for f in report.findings]
    assert severities == ["warning", "warning", "info"]
    assert all(f[1] == "timeline/0/entities/1" for f in report.findings)
    assert "bottom edge" in report.findings[1][2] and "expected no" in report.findings[1][2]


def test_a_configured_judge_that_fails_is_said_aloud(project):
    def broken(frames, *, prompt):
        raise RuntimeError("no key")

    report = critique_body_props(project, judge=broken, frames=_frames([]))
    assert [f[0] for f in report.findings] == ["error"] and "no key" in report.findings[0][2]
    assert report.calls == []
    gibberish = critique_body_props(project, judge=Judge("looks fine to me"), frames=_frames([]))
    assert [f[0] for f in gibberish.findings] == ["error"]


def test_a_missing_answer_is_unsure_not_a_pass(project):
    report = critique_body_props(
        project, judge=Judge(json.dumps({"answers": [{"n": 1, "answer": "yes"}]})), frames=_frames([])
    )
    assert [f[0] for f in report.findings] == ["info"] * (len(BODY_CHECKLIST) - 1)
