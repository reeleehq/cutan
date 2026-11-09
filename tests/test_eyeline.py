"""The eyeline lint (cutan#173, part 2): a speaker faces the one it speaks to, and a
shot/reverse-shot pair keeps the line. The rules are pure (:mod:`cutan.verify.eyeline`);
these tests also run them through ``an validate`` on a real project."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from an.ir.schema import AssetRef, Dialogue, Meta, SceneIR, SetAction, Shot
from an.ir.validate import validate_semantic
from an.project import init, load
from cutan.characters.factory import new_character
from cutan.verify.eyeline import Presence, cut_findings, shot_findings


@pytest.fixture(scope="module")
def project():
    with tempfile.TemporaryDirectory() as d:
        root = init(Path(d) / "p")
        for name in ("ned", "carl"):
            new_character(root / "assets" / "characters", name=name, seed=name, use_dicebear=False)
        yield root


def _shot(shot_id, *entities, actions=(), speaker=None, duration=2.0):
    """``entities``: ``(id, x)`` or ``(id, x, facing_left)``."""
    refs, acts = [], list(actions)
    for e in entities:
        name, x, *left = e
        stage = {"at": (x, 0.0)} if x is not None else None
        refs.append(AssetRef(kind="character", id=name, store="characters", ref=name, stage=stage))
        if left and left[0]:
            acts.append(SetAction(target=name, property="scale_x", value=-1.0, at=0.0))
    dialogue = [Dialogue(speaker=speaker, text="hello")] if speaker else []
    return Shot(id=shot_id, renderer="cutout", duration=duration, entities=refs, actions=acts, dialogue=dialogue)


def _eyeline(root, *shots):
    scene = SceneIR(meta=Meta(title="t", duration=sum(s.duration for s in shots)), timeline=list(shots))
    report = validate_semantic(scene, available_characters=load(root).mall["characters"])
    ours = ("180-degree", "who stands to its")
    return [
        f.description
        for f in report.findings
        if f.severity == "warning" and any(m in f.description for m in ours)
    ]


# --- the pure rules -------------------------------------------------------------


def test_a_speaker_facing_the_listener_is_fine_and_facing_away_is_not():
    listener = Presence("ben", "left", 1.0)
    assert shot_findings([Presence("ana", "right", -1.0, True), listener]) == []
    (f,) = shot_findings([Presence("ana", "left", -1.0, True), listener])
    assert f.entity == "ana" and "stands to its right" in f.message


@pytest.mark.parametrize(
    "present",
    [
        [Presence("ana", "left", -1.0, True)],  # nobody to speak to
        [Presence("ana", "left", -1.0, True), Presence("ben", None, 1.0), Presence("cy", None, 2.0)],  # ambiguous
        [Presence("ana", "left", None, True), Presence("ben", None, 1.0)],  # not placed
        [Presence("ana", None, -1.0, True), Presence("ben", None, 1.0)],  # a back view
        [Presence("ana", "left", 1.0, True), Presence("ben", None, 1.0)],  # same x
        [Presence("ana", "left", -1.0), Presence("ben", "left", 1.0)],  # nobody speaks
    ],
)
def test_what_cannot_be_judged_is_not(present):
    assert shot_findings(present) == []


def test_a_reverse_shot_facing_the_same_way_jumps_the_line():
    (f,) = cut_findings([Presence("ana", "right", speaks=True)], [Presence("ben", "right", speaks=True)])
    assert f.entity == "ben" and "180-degree" in f.message and "face left" in f.message
    assert cut_findings([Presence("ana", "right")], [Presence("ben", "left")]) == []
    assert cut_findings([Presence("ana", "right")], [Presence("ana", "right")]) == []  # same person
    assert cut_findings([Presence("ana", "right"), Presence("cy", "left")], [Presence("ben", "right")]) == []


# --- through `an validate` ------------------------------------------------------


def test_validate_warns_when_a_pair_of_shots_jumps_the_line(project):
    a = _shot("a", ("ned", None), speaker="ned")
    b = _shot("b", ("carl", None), speaker="carl")
    (msg,) = _eyeline(project, a, b)
    assert "'ned' faces right and 'carl' answers facing right" in msg
    turned = _shot("b", ("carl", None, True), speaker="carl")
    assert _eyeline(project, a, turned) == []


def test_validate_warns_when_a_speaker_looks_away_from_the_other_in_the_shot(project):
    away = _shot("s", ("ned", -1.0, True), ("carl", 1.0), speaker="ned")
    (msg,) = _eyeline(project, away)
    assert "'ned' speaks to 'carl'" in msg and "right" in msg
    toward = _shot("s", ("ned", -1.0), ("carl", 1.0, True), speaker="ned")
    assert _eyeline(project, toward) == []
