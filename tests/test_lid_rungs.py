"""A partial lid on a rig that draws only open and closed eyelids (an#272).

The ladder picks a drawing per lid state, so `lid_open -0.45` on a factory
character (no `HALF` drawing) shows the open lid: an identical frame, which the
end-user test then read as a cache bug. `an validate` says so, with the fix.
"""

from __future__ import annotations

from an.ir.schema import AssetRef, Meta, SceneIR, Shot

from cutan.characters import new_character
from cutan.expression.registration import expression


def _findings(tmp_path, *actions):
    from an.ir.validate import validate_semantic
    from an.stores.characters import CharactersStore

    new_character(tmp_path, name="bob", use_dicebear=False, overwrite=True)
    shot = Shot(
        id="s",
        duration=2.0,
        entities=[AssetRef(kind="character", id="b", store="characters", ref="bob")],
        actions=list(actions),
    )
    report = validate_semantic(
        SceneIR(meta=Meta(), timeline=[shot]), available_characters=CharactersStore(tmp_path)
    )
    return [f for f in report.findings if "eyelids have no" in f.description]


def test_a_partial_lid_without_a_half_drawing_is_said(tmp_path):
    (finding, other) = _findings(
        tmp_path, expression("b", axes={"lid_open_l": -0.45, "lid_open_r": -0.45})
    )
    assert finding.severity == "warning" and "'HALF'" in finding.description
    assert "shows 'OPEN'" in finding.description and "-0.85 or lower" in finding.description
    assert "lid_open_r" in other.description


def test_a_lid_the_ladder_can_show_is_not(tmp_path):
    assert _findings(tmp_path, expression("b", axes={"lid_open_l": -0.9})) == []
    assert _findings(tmp_path, expression("b", "neutral")) == []
