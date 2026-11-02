"""Mouth and body cadence apart: "mouths on ones, bodies on twos" made measurable (cutan#80).

The style lint (:mod:`cutan.verify.style`) measures the whole frame, so a
lip-synced line on a still body reads as body motion. For an ``an`` render the
mouth is known at every frame, from the compiled shots:

- **mouth**: a step changes the mouth when a mouth's swap channel (``viseme``,
  and its ``viseme@<form>`` variants) changes value between the two frames:
  exactly the lip-sync's own steps, whatever the head does around it;
- **body**: the lint's own change rule (:func:`~cutan.verify.style.changes_from_stats`)
  on the picture with the mouths' boxes left out. A mouth's art can draw past
  its box (an open viseme), so each box is grown by :data:`MOUTH_GROW` of its
  size before it is left out.

The mouths are found by their channel, not by a node's name: any node a
``viseme`` set swaps. :func:`mouth_track` compiles the shots and reads the
channel and the boxes (from the IR shots, not yet exactly the render's
preparation: reeleehq/an#733); :func:`split_cadence` measures, streaming the frames
(no per-pixel mask of the whole film is held). Reference footage has no rig,
so this measures our renders only (a face locator for footage is research).
"""

from __future__ import annotations

import warnings
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from cutan.verify.style import (
    MIN_CHANGED_PIXELS,
    PIXEL_CHANGE_DELTA,
    cadence_of,
    changes_from_stats,
)

#: The swap channel that draws a mouth (and its ``viseme@<form>`` variants).
MOUTH_CHANNEL: str = "viseme"
#: Each mouth box is grown by this share of its own width and height on every
#: side before the body is measured without it: an open viseme draws past the
#: box the closed one sizes. Measured on the corpus dialogue render (a mouth box
#: 4 render px tall): at 0.5 two lip-sync steps still leaked into the body, at
#: 1.0 none did, and only the head's real move remained.
MOUTH_GROW: float = 1.0
#: ...but by no more than this many decode pixels a side: a close-up's mouth
#: (88x33 decode px on the corpus expressions scene) grown by its own size would
#: hide the brows and the blinks from the body.
MOUTH_GROW_MAX_PX: int = 8
#: Frames are read this many at a time when the body is measured.
CHUNK_FRAMES: int = 256

Box = tuple[int, int, int, int]


@dataclass
class MouthTrack:
    """Per film frame: the mouths' boxes (decode pixels, grown) and the values of
    their swap channels (a change of value is a mouth step)."""

    boxes: list[list[Box]] = field(default_factory=list)
    #: per frame, ``{mouth node path: its swap channels' values}`` for each mouth
    #: drawn in the frame (an off-screen mouth is not drawn)
    states: list[dict] = field(default_factory=list)

    def any(self) -> bool:
        return any(self.boxes)


def _is_mouth_channel(prop: str) -> bool:
    return prop == MOUTH_CHANNEL or prop.startswith(MOUTH_CHANNEL + "@")


def mouth_track(
    project: Any,
    *,
    n: int,
    fps: float,
    size: tuple[int, int],
    render_size: tuple[int, int],
    grow: float = MOUTH_GROW,
    grow_max_px: int = MOUTH_GROW_MAX_PX,
) -> MouthTrack:
    """Where the mouths are, and what they show, in each of the film's ``n``
    frames, at the decode ``size`` (w, h) of a render at ``render_size`` (w, h).
    Each shot is compiled (a world lowered first), placed at its film start
    (``an.assemble.film_timeline``) and read over its whole length, so during a
    dissolve both shots' mouths count."""
    from an.assemble import film_timeline
    from an.project import load
    from an.stage.compile import compile_shot
    from an.stage.timeline import evaluate_timeline, node_box, timeline_from_scene

    project = load(project) if not hasattr(project, "scene") else project
    scene = project.scene
    if getattr(scene, "world", None) is not None:
        from an.stage.world import lower_scene

        scene = lower_scene(scene, project.mall, fps=fps).scene
    w, h = size
    rw, rh = render_size
    sx, sy = w / rw, h / rh
    track = MouthTrack([[] for _ in range(n)], [{} for _ in range(n)])
    shots = list(scene.timeline)
    tl = film_timeline(shots, fps=fps)
    for shot, start in zip(shots, tl.starts):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            doc = compile_shot(
                shot, project.mall, fps=int(round(fps)), width=rw, height=rh
            )
        timeline = timeline_from_scene(doc)
        frames = int(round(shot.duration * fps))
        for i in range(frames):
            frame = start + i
            if frame >= n:
                break
            pose = evaluate_timeline(timeline, i / fps)
            values: dict[str, list] = {}
            for (path, prop), value in pose.items():
                if _is_mouth_channel(prop):
                    values.setdefault(path, []).append((prop, str(value)))
            for path, channels in values.items():
                box = node_box(doc, path, pose=pose)
                if box is None:
                    continue
                # in decode pixels: grown by its own size, at most grow_max_px a side
                bx0, by0, bx1, by1 = box[0] * sx, box[1] * sy, box[2] * sx, box[3] * sy
                gx = min(grow * (bx1 - bx0), grow_max_px)
                gy = min(grow * (by1 - by0), grow_max_px)
                x0, y0 = (
                    max(0, int(np.floor(bx0 - gx))),
                    max(0, int(np.floor(by0 - gy))),
                )
                x1, y1 = min(w, int(np.ceil(bx1 + gx))), min(h, int(np.ceil(by1 + gy)))
                if x1 > x0 and y1 > y0:  # drawn in the frame: its state counts
                    track.boxes[frame].append((x0, y0, x1, y1))
                    track.states[frame][path] = tuple(sorted(channels))
    return track


def split_cadence(
    frames: np.ndarray,
    track: MouthTrack,
    *,
    fps: float,
    cut_steps: Sequence[int] = (),
    min_changed_pixels: int = MIN_CHANGED_PIXELS,
) -> dict[str, dict[str, float]]:
    """``{"mouth": cadence, "body": cadence}`` of ``frames`` (``(n, h, w, 3)``),
    in the lint's own statistics (:func:`cutan.verify.style.cadence_of`). A mouth
    step is a change of a mouth channel's value; a body step is the lint's rule
    on the picture with the boxes of both frames of the step left out.
    ``cut_steps``: steps into a cut, left out of cadence as the lint does.

    >>> f = np.zeros((5, 20, 20, 3), np.uint8)
    >>> f[1:3, 2:4, 2:4] = 255                       # the mouth opens at 1, shuts at 3
    >>> t = MouthTrack([[(1, 1, 5, 5)]] * 5, [{"m": v} for v in "XAAXX"])
    >>> out = split_cadence(f, t, fps=12.0, min_changed_pixels=1)
    >>> out["mouth"]["pose_changes_per_s"] > 0, out["body"]["pose_changes_per_s"]
    (True, 0.0)
    """
    n = len(frames)
    if n < 2:
        raise ValueError("the cadence needs at least two frames")
    if len(track.boxes) != n or len(track.states) != n:
        raise ValueError(f"the mouth track has {len(track.boxes)} frames, the film {n}")

    def mouth_step(a: dict, b: dict) -> bool:
        """A mouth drawn in both frames changed what it shows (a mouth that comes
        or goes, at a cut or a dissolve's edge, is not a step)."""
        return any(a[p] != b[p] for p in a.keys() & b.keys())

    mouth = np.array(
        [mouth_step(track.states[k], track.states[k + 1]) for k in range(n - 1)]
    )
    step_diff = np.empty(n - 1, np.float32)
    moved = np.empty(n - 1, np.int64)
    for lo in range(0, n - 1, CHUNK_FRAMES):
        hi = min(n - 1, lo + CHUNK_FRAMES)
        grey = frames[lo : hi + 1].astype(np.float32).mean(axis=3)
        delta = np.abs(grey[1:] - grey[:-1])
        for k in range(lo, hi):
            for x0, y0, x1, y1 in (*track.boxes[k], *track.boxes[k + 1]):
                delta[k - lo, y0:y1, x0:x1] = 0.0
        step_diff[lo:hi] = delta.mean(axis=(1, 2))
        moved[lo:hi] = (delta > PIXEL_CHANGE_DELTA).reshape(hi - lo, -1).sum(axis=1)
    _, body, _ = changes_from_stats(
        step_diff, moved, min_changed_pixels=min_changed_pixels
    )
    cuts = set(cut_steps)
    return {
        "mouth": cadence_of(mouth, cut_steps=cuts, fps=fps),
        "body": cadence_of(body, cut_steps=cuts, fps=fps),
    }


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
