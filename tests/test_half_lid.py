"""A HALF eyelid drawing from a rig's own lid art (cutan#65).

The second end-user test (Reiniger) asked for annoyance with `lid_open -0.6` and
got the validator's "eyelids have no 'HALF' drawing … add a HALF eyelid drawing
to the set", with no way to do it. `add_half_lid` (`an character add-half-lid`)
makes one, and the message now names it.
"""

from __future__ import annotations

import hashlib
import json

import pytest

from cutan.characters.factory import new_character
from cutan.characters.lids import (
    HALF_ATTACHMENT,
    HalfLidError,
    add_half_lid,
)
from cutan.characters.schema import CharacterDescriptor
from cutan.expression.binding import lid_rung_problems

pytestmark = pytest.mark.genre("cutout_animation")


@pytest.fixture
def amy(tmp_path):
    return new_character(tmp_path, name="amy", use_dicebear=False).parent


def _desc(char):
    return CharacterDescriptor.model_validate(
        json.loads((char / "character.json").read_text(encoding="utf-8"))
    )


def test_the_validator_names_the_command(amy):
    (problem,) = lid_rung_problems(_desc(amy), None, axes={"lid_open_l": -0.6})
    assert "an character add-half-lid amy" in problem


def test_a_half_lid_is_made_from_the_rig_s_own_lids_and_used(amy):
    add_half_lid(amy)
    desc = _desc(amy)
    assert desc.asset_sets["eyelid"]["HALF"] == HALF_ATTACHMENT
    slots = desc.skins["default"].slots
    for slot, side in (("left_eye", "l"), ("right_eye", "r")):
        half, opened = slots[slot][HALF_ATTACHMENT], slots[slot]["open"]
        assert half.path == f"parts/eye_{side}_half.svg"
        assert (half.x, half.y, half.anchor) == (opened.x, opened.y, opened.anchor)
        svg = (amy / half.path).read_text(encoding="utf-8")
        assert "clip-path" in svg
        # Both lid drawings are the factory's cc0, so the derived one says so,
        # pinned to its own bytes.
        assert half.source.license == opened.source.license
        assert half.source.sha256 == hashlib.sha256(svg.encode("utf-8")).hexdigest()
    assert lid_rung_problems(desc, None, axes={"lid_open_l": -0.6, "lid_open_r": -0.6}) == []


def test_it_is_idempotent(amy):
    add_half_lid(amy)
    first = (amy / "character.json").read_text(encoding="utf-8")
    svg = (amy / "parts" / "eye_l_half.svg").read_bytes()
    add_half_lid(amy)
    assert (amy / "character.json").read_text(encoding="utf-8") == first
    assert (amy / "parts" / "eye_l_half.svg").read_bytes() == svg


def test_a_half_lid_someone_drew_is_not_replaced(amy):
    raw = json.loads((amy / "character.json").read_text(encoding="utf-8"))
    raw["asset_sets"]["eyelid"]["HALF"] = "drawn_half"
    (amy / "character.json").write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(HalfLidError, match="overwrite"):
        add_half_lid(amy)


def test_the_cli_reports_and_does_it(amy):
    from cutan.characters.cli import add_half_lid as cli_add_half_lid

    said = cli_add_half_lid("amy", out_dir=str(amy.parent))
    assert said.startswith("added a HALF eyelid drawing")
    assert _desc(amy).asset_sets["eyelid"]["HALF"] == HALF_ATTACHMENT
    assert cli_add_half_lid("nobody", out_dir=str(amy.parent)).startswith("no character")
