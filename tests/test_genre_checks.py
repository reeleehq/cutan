"""The cut-out genre's semantic checks: which it declares, and where they run.

These pins live HERE, beside the declarations, not in `an`'s tests: a test in
`an` that pins a genre's list turns every open `an` PR red the moment the genre
adds a check (cutan#19, the an#354 shape). `an` pins only its own checks.
"""

from __future__ import annotations

from cutan.genre import CUTOUT

#: The checks the genre declares, by name.
DECLARED = {
    "cutout.play",
    "cutout.expression",
    "cutout.brow_acting",
    "cutout.walk_gait",
    "cutout.turns",
    "cutout.hidden_mouth_while_speaking",
    "cutout.character_refs",
    "cutout.declared_speech",
    "cutout.shot_policy",
    "cutout.style_copies",
    "cutout.view_continuity",
}


def test_the_genre_declares_its_checks():
    assert set(CUTOUT.provides()["checks"]) == DECLARED


def test_its_shot_checks_run_where_they_did_against_the_cores():
    """N3 (an#241): a genre check lands where it was when all checks were one
    function. Pinned as order relative to the core checks it sits between, so a
    core check added elsewhere does not move this test."""
    from an.genres.registry import checks

    order = [c.name for c in checks("shot")]
    pos = order.index
    assert pos("framing") < pos("cutout.play") < pos("cutout.expression")
    assert pos("cutout.expression") < pos("cutout.brow_acting") < pos("cutout.walk_gait")
    assert pos("cutout.walk_gait") < pos("cutout.shot_policy") < pos("swap_references")
    assert pos("swap_references") < pos("cutout.turns") < pos("cutout.hidden_mouth_while_speaking")
    assert pos("cutout.hidden_mouth_while_speaking") < pos("trim_targets")


def test_the_style_copies_check_runs_once_per_scene():
    from an.genres.registry import checks

    assert "cutout.style_copies" in [c.name for c in checks("scene")]
