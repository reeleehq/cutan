"""Mouth and body cadence apart (cutan#80)."""

from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np
import pytest

from cutan.verify.regions import mouth_masks, split_cadence

CORPUS = Path(__file__).resolve().parents[1] / "misc" / "bench" / "corpus"


def _film(n=13, size=(40, 60)):
    return np.zeros((n, *size, 3), np.uint8), np.zeros((n, *size), bool)


def test_a_mouth_on_ones_over_a_still_body_is_mouth_motion_only():
    frames, masks = _film()
    masks[:, 5:10, 20:30] = True
    for i in range(len(frames)):  # the mouth changes every frame, nothing else does
        frames[i, 6:9, 22:28] = 255 if i % 2 else 0
    out = split_cadence(frames, masks, fps=12.0)
    assert out["mouth"]["one_frame_interval_share"] == 1.0
    assert out["body"]["pose_changes_per_s"] == 0.0, "a lip-synced line is not body motion"


def test_a_body_on_twos_with_a_shut_mouth_is_body_motion_only():
    frames, masks = _film()
    masks[:, 5:10, 20:30] = True
    for i in range(len(frames)):  # the body moves every second frame
        frames[i, 20:40, 10:50] = 200 if (i // 2) % 2 else 40
    out = split_cadence(frames, masks, fps=12.0)
    assert out["mouth"]["pose_changes_per_s"] == 0.0
    assert out["body"]["two_frame_interval_share"] == 1.0


def test_masks_must_match_the_frames():
    frames, masks = _film()
    with pytest.raises(ValueError, match="do not match"):
        split_cadence(frames, masks[:, :10], fps=12.0)


def test_the_mouth_is_found_where_the_rig_draws_it(tmp_path):
    project = tmp_path / "dialogue"
    shutil.copytree(CORPUS / "dialogue", project)
    masks = mouth_masks(project, n=24, fps=24.0, size=(320, 180), render_size=(320, 240))
    assert masks.shape == (24, 180, 320) and masks.all(axis=0).any(), "the mouth in every frame"
    ys, xs = np.nonzero(masks[0])
    assert 0 < ys.max() - ys.min() < 30 and 0 < xs.max() - xs.min() < 60, "a mouth, not a body"
    assert ys.mean() < 90, "in the upper half: the head"
