"""A turn too short to show its squash between two steps is a hard swap (an#273).

The South Park spec's ~1-frame `turn` at `step_hz: 12` gave two squashed frames
and one where the character vanished: a stepped frame sampled the edge-on
scale. Played by name, a `turn` now gets the shot's `step_hz`, and one whose
halves are shorter than a step swaps at its midpoint instead.
"""

from __future__ import annotations

import warnings

import pytest

from an.adapters.cutout.compile import compile_shot
from an.ir.compose import delay, sequence
from an.ir.schema import AssetRef, Shot

from cutan.characters import new_character
from cutan.characters.registration import PlayAction

FPS = 24


def _scale_x(tmp_path, *, step_hz, duration):
    from an.adapters.cutout.timeline import evaluate_timeline, timeline_from_scene
    from an.stores.characters import CharactersStore

    new_character(tmp_path, name="stan", use_dicebear=False, overwrite=True)
    shot = Shot(
        id="s",
        duration=1.0,
        entities=[AssetRef(kind="character", id="c", store="characters", ref="stan")],
        actions=[sequence(delay(0.5), PlayAction(target="c", animation="turn",
                                                 args={"to": "side", "duration": duration}))],
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        scene = compile_shot(
            shot, {"characters": CharactersStore(tmp_path)}, fps=FPS, step_hz=step_hz
        )
    timeline = timeline_from_scene(scene)
    return [evaluate_timeline(timeline, i / FPS).get(("c", "scale_x"), 1.0) for i in range(FPS)]


@pytest.mark.parametrize("frames", [1, 2, 3])
def test_a_short_turn_on_twos_never_vanishes(tmp_path, frames):
    values = _scale_x(tmp_path, step_hz=12, duration=frames / FPS)
    assert min(abs(v) for v in values) > 0.5, values  # never edge-on, never squashed
    assert values[0] == pytest.approx(values[11])  # before: the front, unsquashed


def test_a_turn_long_enough_still_squashes(tmp_path):
    values = _scale_x(tmp_path, step_hz=12, duration=0.6)
    assert min(abs(v) for v in values) < 0.5  # the squash shows across steps
