"""Mouth and body cadence apart: "mouths on ones, bodies on twos" made measurable (cutan#80).

The style lint (:mod:`cutan.verify.style`) measures the whole frame, so a
lip-synced line on a still body reads as body motion. For an ``an`` render the
mouth's screen rectangle is known at every frame: the compiled shot has the
mouth node (``<character>/head/mouth``), and ``an`` gives its box at any pose
(``an.stage.timeline.node_box`` over ``evaluate_timeline``). So each frame step
splits in two:

- **mouth**: the step changed pixels inside the mouths' boxes (of either frame);
- **body**: the step changed the picture outside them, by the lint's own rule
  (the frame-wide mean, or the local change of :data:`~cutan.verify.style.MIN_CHANGED_PIXELS`).

:func:`split_cadence` is the pure measurement (frames and masks in);
:func:`mouth_masks` builds the masks from a project. Reference footage has no
project, so this measures our renders only (a face locator for footage is
separate research).
"""

from __future__ import annotations

import warnings
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from cutan.verify.style import (
    MIN_CHANGED_PIXELS,
    PIXEL_CHANGE_DELTA,
    _cadence,
    step_changes_of,
)

#: A mouth step counts when at least this many pixels inside the mouths' boxes
#: (at the decode size) move by more than ``PIXEL_CHANGE_DELTA``: a mouth at
#: 320x180 is a few pixels across, so a swap changes a handful.
MOUTH_MIN_CHANGED_PIXELS: int = 2
#: The mouth's box is grown by this many decode pixels, for anti-aliasing and
#: the art's slack in its box.
MOUTH_MARGIN_PX: int = 1
MOUTH_NODE: str = "mouth"


def split_cadence(
    frames: np.ndarray,
    masks: np.ndarray,
    *,
    fps: float,
    cut_steps: Sequence[int] = (),
    min_mouth_pixels: int = MOUTH_MIN_CHANGED_PIXELS,
    min_changed_pixels: int = MIN_CHANGED_PIXELS,
) -> dict[str, dict[str, float]]:
    """``{"mouth": cadence, "body": cadence}`` of ``frames`` (``(n, h, w, 3)``),
    ``masks`` (``(n, h, w)`` bool) marking the mouths in each frame. A step's
    region is the union of its two frames' masks. The cadence dicts are the
    lint's own (:func:`cutan.verify.style._cadence`): identical-frame share, pose
    changes per second, 1/2/3+ interval shares, longest hold. ``cut_steps``:
    steps into a cut, left out of cadence as the lint does.

    >>> f = np.zeros((5, 20, 20, 3), np.uint8)
    >>> f[1:, 2:4, 2:4] = 255; f[3:, 2:4, 2:4] = 0     # the mouth: on at 1, off at 3
    >>> m = np.zeros((5, 20, 20), bool); m[:, 1:5, 1:5] = True
    >>> out = split_cadence(f, m, fps=12.0, min_changed_pixels=1)
    >>> out["mouth"]["pose_changes_per_s"] > 0, out["body"]["pose_changes_per_s"]
    (True, 0.0)
    """
    if len(frames) < 2:
        raise ValueError("the cadence needs at least two frames")
    if masks.shape != frames.shape[:3]:
        raise ValueError(f"masks {masks.shape} do not match frames {frames.shape[:3]}")
    region = masks[1:] | masks[:-1]
    grey = frames.astype(np.float32).mean(axis=3)
    delta = np.abs(grey[1:] - grey[:-1])
    mouth_moved = ((delta > PIXEL_CHANGE_DELTA) & region).reshape(len(region), -1).sum(axis=1)
    mouth_changed = mouth_moved >= min_mouth_pixels
    # the body: the lint's own rule, on the differences with the mouths zeroed
    _, body, _ = step_changes_of(
        np.where(region, 0.0, delta), min_changed_pixels=min_changed_pixels
    )
    cuts = set(cut_steps)
    return {
        "mouth": _cadence(mouth_changed, cut_steps=cuts, fps=fps),
        "body": _cadence(body, cut_steps=cuts, fps=fps),
    }


def mouth_masks(
    project: Any,
    *,
    n: int,
    fps: float,
    size: tuple[int, int],
    render_size: tuple[int, int],
    margin: int = MOUTH_MARGIN_PX,
) -> np.ndarray:
    """``(n, h, w)`` bool: where the characters' mouths are in each of the film's
    ``n`` frames, at the decode ``size`` (w, h), for a render at
    ``render_size`` (w, h). Each shot is compiled as ``an`` renders it (a world
    lowered first), placed at its film start (``an.assemble.film_timeline``),
    and its mouth nodes boxed at every frame's pose.
    """
    from an.assemble import film_timeline
    from an.project import load
    from an.stage.compile import compile_shot
    from an.stage.timeline import evaluate_timeline, node_box, timeline_from_scene
    from an.stage.tree import walk_document

    project = load(project) if not hasattr(project, "scene") else project
    scene = project.scene
    if getattr(scene, "world", None) is not None:
        from an.stage.world import lower_scene

        scene = lower_scene(scene, project.mall, fps=fps).scene
    w, h = size
    rw, rh = render_size
    sx, sy = w / rw, h / rh
    masks = np.zeros((n, h, w), bool)
    shots = list(scene.timeline)
    tl = film_timeline(shots, fps=fps)
    ends = [*tl.starts[1:], tl.total_frames]
    for shot, start, end in zip(shots, tl.starts, ends):
        chars = {e.id for e in shot.entities if e.kind == "character"}
        if not chars:
            continue
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            doc = compile_shot(shot, project.mall, fps=fps, width=rw, height=rh)
        mouths = [
            path
            for path, _ in walk_document(doc)
            if path.rsplit("/", 1)[-1] == MOUTH_NODE and path.split("/", 1)[0] in chars
        ]
        if not mouths:
            continue
        timeline = timeline_from_scene(doc)
        for i in range(max(0, end - start)):
            frame = start + i
            if frame >= n:
                break
            pose = evaluate_timeline(timeline, i / fps)
            for path in mouths:
                box = node_box(doc, path, pose=pose)
                if box is None:
                    continue
                x0 = max(0, int(np.floor(box[0] * sx)) - margin)
                y0 = max(0, int(np.floor(box[1] * sy)) - margin)
                x1 = min(w, int(np.ceil(box[2] * sx)) + margin)
                y1 = min(h, int(np.ceil(box[3] * sy)) + margin)
                if x1 > x0 and y1 > y0:
                    masks[frame, y0:y1, x0:x1] = True
    return masks


def region_findings(regions: Mapping[str, Mapping[str, float]]) -> str:
    """One line for the lint's report: the mouth's and the body's cadence."""

    def one(name: str) -> str:
        c = regions[name]
        return (
            f"{name}: {c['pose_changes_per_s']} changes/s, intervals "
            f"{c['one_frame_interval_share']:.0%}/{c['two_frame_interval_share']:.0%}/"
            f"{c['three_plus_interval_share']:.0%} on ones/twos/threes+"
        )

    return "; ".join(one(k) for k in ("mouth", "body"))
