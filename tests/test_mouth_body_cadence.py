"""Mouth and body cadence apart (cutan#80)."""

from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np
import pytest

from cutan.verify import style as S
from cutan.verify.regions import MouthTrack, mouth_track, split_cadence

CORPUS = Path(__file__).resolve().parents[1] / "misc" / "bench" / "corpus"
#: The corpus dialogue scene's viseme changes, by film step (24 fps, 1 s).
DIALOGUE_MOUTH_STEPS = [3, 6, 10, 13, 17, 20]


def _film(n=13, size=(40, 60)):
    return np.zeros((n, *size, 3), np.uint8)


def test_a_mouth_on_ones_over_a_still_body_is_mouth_motion_only():
    frames = _film()
    states = []
    for i in range(len(frames)):  # the mouth swaps every frame, nothing else moves
        frames[i, 6:9, 22:28] = 255 if i % 2 else 0
        states.append({"m": "A" if i % 2 else "X"})
    track = MouthTrack([[(20, 5, 30, 10)]] * len(frames), states)
    out = split_cadence(frames, track, fps=12.0)
    assert out["mouth"]["one_frame_interval_share"] == 1.0
    assert out["body"]["pose_changes_per_s"] == 0.0, "a lip-synced line is not body motion"


def test_a_head_bob_inside_the_mouth_box_is_body_not_mouth():
    """The mouth's steps are its channel's: pixels moving in its box are not."""
    frames = _film()
    for i in range(len(frames)):  # the whole head moves every second frame
        frames[i, 2:20, 15:35] = 200 if (i // 2) % 2 else 40
    track = MouthTrack([[(20, 5, 30, 10)]] * len(frames), [{"m": "X"}] * len(frames))
    out = split_cadence(frames, track, fps=12.0)
    assert out["mouth"]["pose_changes_per_s"] == 0.0
    assert out["body"]["two_frame_interval_share"] == 1.0


def test_the_track_must_match_the_film():
    with pytest.raises(ValueError, match="frames"):
        split_cadence(_film(), MouthTrack([[]] * 3, [{}] * 3), fps=12.0)


@pytest.fixture()
def dialogue(tmp_path):
    project = tmp_path / "dialogue"
    shutil.copytree(CORPUS / "dialogue", project)
    return project


def test_the_mouth_is_found_by_its_channel_where_the_rig_draws_it(dialogue):
    track = mouth_track(dialogue, n=24, fps=24.0, size=(320, 180), render_size=(320, 240))
    assert all(track.boxes), "a mouth in every frame"
    x0, y0, x1, y1 = track.boxes[0][0]
    assert y1 < 90 and 0 < y1 - y0 < 30 and 0 < x1 - x0 < 120, "a (grown) mouth, in the head"
    steps = [k for k in range(23) if track.states[k] != track.states[k + 1]]
    assert steps == DIALOGUE_MOUTH_STEPS


def test_the_lint_reports_regions_for_a_project(dialogue, monkeypatch):
    """Through style_lint: the wiring, not only the pieces."""
    monkeypatch.setattr(S, "_decode_frames", lambda mp4, width, height: np.zeros((24, height, width, 3), np.uint8))
    monkeypatch.setattr(S, "_probe_fps", lambda mp4: 24.0)
    monkeypatch.setattr(S, "_probe_size", lambda mp4: (320, 240))
    video = dialogue / "output" / "main.mp4"
    video.parent.mkdir()
    video.write_bytes(b"stand-in")
    for scene in (dialogue, dialogue / "ir" / "scene.json", None):  # None: found from the render's folder
        result = S.style_lint(video, "south_park", scene=scene)
        assert result.regions is not None, scene
        assert result.regions["mouth"]["pose_changes_per_s"] == 6.0
        assert result.regions["body"]["pose_changes_per_s"] == 0.0
        assert any("cadence by region" in f.description for f in result.report.findings)


@pytest.mark.browser
@pytest.mark.ffmpeg
def test_on_a_real_render_lip_sync_does_not_leak_into_the_body(dialogue):
    """The open visemes draw past the mouth's box (cutan#80 review): the grown
    box keeps them out, and only the head's real move is body motion."""
    from an.project import load
    from an.render import render

    render(load(dialogue))
    result = S.style_lint(dialogue / "output" / "main.mp4", "south_park", scene=dialogue)
    assert result.regions["mouth"]["pose_changes_per_s"] == 6.0
    assert result.regions["body"]["pose_changes_per_s"] <= 1.0


def test_a_mouth_that_comes_or_goes_is_not_a_mouth_step():
    """At a cut, a dissolve's edge or an off-screen mouth, nothing was lip-synced."""
    frames = _film(n=5)
    states = [{}, {"a": "X"}, {"a": "X", "b": "X"}, {"b": "X"}, {"b": "A"}]
    track = MouthTrack([[]] * 5, states)
    out = split_cadence(frames, track, fps=12.0)
    assert out["mouth"]["pose_changes_per_s"] == pytest.approx(12.0 / 5), "only b's X->A"


def test_a_close_up_mouth_is_not_grown_over_the_face(dialogue):
    from cutan.verify.regions import MOUTH_GROW_MAX_PX

    track = mouth_track(dialogue, n=24, fps=24.0, size=(1280, 720), render_size=(320, 240))
    raw = mouth_track(dialogue, n=24, fps=24.0, size=(1280, 720), render_size=(320, 240), grow=0.0)
    (x0, y0, x1, y1), (r0, s0, r1, s1) = track.boxes[0][0], raw.boxes[0][0]
    assert r0 - x0 <= MOUTH_GROW_MAX_PX + 1 and y1 - s1 <= MOUTH_GROW_MAX_PX + 1
