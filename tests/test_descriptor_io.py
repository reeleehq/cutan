"""The load / migrate / validate / write cycle of a character's descriptor (cutan#129)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from PIL import Image

from cutan.characters import new_character
from cutan.characters.descriptor_io import (
    descriptor_path,
    load_descriptor,
    read_raw,
    save_raw,
    validate_raw,
    write_descriptor,
)
from cutan.characters.set_part import replace_part_art


@pytest.fixture()
def char(tmp_path):
    return new_character(tmp_path, name="ned", seed="ned", use_dicebear=False).parent


def test_a_descriptor_round_trips(char):
    desc = load_descriptor(char)
    desc.display_name = "Ned"
    assert write_descriptor(char, desc) == descriptor_path(char)
    assert load_descriptor(char).display_name == "Ned"


def test_save_raw_validates_before_it_writes(char):
    before = descriptor_path(char).read_text()
    raw = read_raw(char)
    raw["bones"] = "not a list"
    with pytest.raises(ValidationError):
        save_raw(char, raw)
    assert descriptor_path(char).read_text() == before
    raw = read_raw(char)
    raw["display_name"] = "Edited"
    assert save_raw(char, raw).display_name == "Edited"
    assert validate_raw(read_raw(char)).display_name == "Edited"


def test_set_part_copies_no_picture_when_the_descriptor_would_not_validate(char, tmp_path, monkeypatch):
    """The partial-failure class: the picture must not land beside a descriptor that failed."""
    from cutan.characters import set_part as module

    def refuse(raw):
        raise ValidationError.from_exception_data("CharacterDescriptor", [])

    monkeypatch.setattr(module, "validate_raw", refuse)
    picture = tmp_path / "head.png"
    Image.new("RGBA", (20, 20), (200, 0, 0, 255)).save(picture)
    before = descriptor_path(char).read_text()
    with pytest.raises(ValidationError):
        replace_part_art(char, "parts/head.svg", picture)
    assert not (char / "parts" / "head.png").exists() and (char / "parts" / "head.svg").is_file()
    assert descriptor_path(char).read_text() == before


def test_write_descriptor_refuses_an_invalid_in_place_edit(char):
    before = descriptor_path(char).read_text()
    desc = load_descriptor(char)
    desc.bones = "not a list"  # the schema does not validate assignments
    with pytest.raises(ValidationError):
        write_descriptor(char, desc)
    assert descriptor_path(char).read_text() == before


def test_a_half_lid_writes_no_drawing_when_the_descriptor_would_not_validate(char, monkeypatch):
    from cutan.characters import lids

    def refuse(raw):
        raise ValidationError.from_exception_data("CharacterDescriptor", [])

    monkeypatch.setattr(lids, "validate_raw", refuse)
    before = {p.name for p in (char / "parts").iterdir()}
    with pytest.raises(ValidationError):
        lids.add_half_lid(char, overwrite=True)
    assert {p.name for p in (char / "parts").iterdir()} == before
