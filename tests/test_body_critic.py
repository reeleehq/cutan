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
from cutan.body_attachment import FIRST_PERSON
from cutan.verify.critic import CHECKLISTS, critique_body_props

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


def _entity(kind, id_, ref, store):
    return AssetRef(kind=kind, id=id_, store=store, ref=ref, stage=StagePlacement(at=(0.0, 0.0), scale=1.0))


@pytest.fixture(scope="module")
def project():
    with tempfile.TemporaryDirectory() as d:
        root = init(Path(d) / "p")
        new_character(root / "assets" / "characters", name="ned", seed="ned", use_dicebear=False)
        _prop(root, "wheel", {BODY_ATTACHMENT_KEY: {"character": "ned", "view": "front", "sockets": SOCKETS}})
        _prop(root, "cup", {})  # depicts no body: never asked about
        _prop(root, "pov", {BODY_ATTACHMENT_KEY: {"character": "ned", "view": FIRST_PERSON, "sockets": SOCKETS}})
        p = load(root)
        entity = _entity
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
    assert [f[0] for f in report.findings] == ["info"] * (len(CHECKLISTS["front"]) - 1)
    empty = critique_body_props(project, judge=Judge('{"answers": []}'), frames=_frames([]))
    assert [f[0] for f in empty.findings] == ["error"], "no answers is not 'unsure'"


def _with_shots(project, *shots):
    return type(project)(root=project.root, mall=project.mall,
                         scene=project.scene.model_copy(update={"timeline": list(shots)}))  # fmt: skip


def test_a_first_person_prop_is_asked_its_own_questions(project):
    e = _entity
    pov = Shot(id="pov", renderer="cutout", duration=1.0, entities=[e("prop", "p", "pov", "props")])
    judge = Judge(_reply("yes", "no"))  # arms from below, no face: a correct first-person drawing
    report = critique_body_props(_with_shots(project, pov), judge=judge, frames=_frames([]))
    assert report.findings == [] and len(judge.prompts) == 1
    assert "bottom edge" in judge.prompts[0]


def test_the_prop_is_asked_about_the_character_it_is_bound_to(project):
    e = _entity
    wheel = e("prop", "w", "wheel", "props").model_copy(update={"overrides": {"body_of": "kim"}})
    kim = e("character", "kim", "ned", "characters")
    shot = Shot(id="s", renderer="cutout", duration=1.0, entities=[kim, wheel])
    judge = Judge(_reply("yes", "no", "yes"))
    critique_body_props(_with_shots(project, shot), judge=judge, frames=_frames([]))
    assert "kim" in judge.prompts[0] and "ned" not in judge.prompts[0]
    off_stage = Shot(id="s", renderer="cutout", duration=1.0, entities=[e("prop", "w", "wheel", "props")])
    judge = Judge(_reply("yes", "no", "yes"))
    critique_body_props(_with_shots(project, off_stage), judge=judge, frames=_frames([]))
    assert judge.prompts == [], "nobody on screen for the arms to belong to"


def test_a_probe_that_fails_is_an_error_and_a_shot_is_probed_once(project):
    def broken(project, shot, times):
        raise RuntimeError("no browser")

    report = critique_body_props(project, judge=Judge(_reply("yes", "no", "yes")), frames=broken)
    assert [f[0] for f in report.findings] == ["error"] and "no browser" in report.findings[0][2]
    e = _entity
    two = Shot(id="two", renderer="cutout", duration=1.0, entities=[
        e("character", "ned", "ned", "characters"), e("prop", "w1", "wheel", "props"), e("prop", "w2", "wheel", "props")])  # fmt: skip
    probed = []
    critique_body_props(_with_shots(project, two), judge=Judge(_reply("yes", "no", "yes")), frames=_frames(probed))
    assert len(probed) == 1


def test_the_envelope_names_the_model_and_bad_instants_are_refused(project):
    report = critique_body_props(
        project, judge=lambda frames, *, prompt: {"reply": _reply("yes", "no", "yes"), "model": "m-1"},
        frames=_frames([]),
    )
    assert report.calls[0]["model"] == "m-1"
    with pytest.raises(ValueError, match="fractions"):
        critique_body_props(project, judge=Judge(""), frames=_frames([]), at=(1.5,))
