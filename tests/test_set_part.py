"""`an character set-part`: a factory attachment drawn by a picture (cutan#92)."""

from __future__ import annotations

import json

import pytest
from PIL import Image

from cutan.characters import new_character
from cutan.characters.cli import set_part as set_part_command
from cutan.characters.schema import CharacterDescriptor
from cutan.characters.set_part import SetPartError, replace_part_art, set_part
from cutan.characters.validate import validate_character


@pytest.fixture()
def char(tmp_path):
    return new_character(tmp_path, name="ned", seed="ned", use_dicebear=False).parent


def _picture(path, size=(120, 90)):
    Image.new("RGBA", size, (0, 0, 0, 0)).save(path)
    img = Image.open(path)
    img.paste((200, 60, 40, 255), (20, 20, 100, 70))
    img.save(path)
    return path


def _head(char_dir):
    doc = CharacterDescriptor.model_validate_json((char_dir / "character.json").read_text())
    return doc, doc.skins["default"].slots["head"]["head"]


def test_the_picture_takes_the_factory_svg_s_place_in_its_box(char, tmp_path):
    _, before = _head(char)
    set_part(char, "head", _picture(tmp_path / "head.png"))
    desc, head = _head(char)
    assert head.path == "parts/head.png" and (char / "parts" / "head.png").is_file()
    assert not (char / "parts" / "head.svg").exists()
    assert head.width and head.height  # the box the factory's drawing had
    if before.width and before.height:
        assert (head.width, head.height) == (before.width, before.height)
    assert "parts/head.svg" not in desc.colour_roles
    assert head.source is None
    report = validate_character(char, name="ned")
    assert not [f for f in report.findings if f.severity == "error"], report.findings


def test_a_slot_name_disambiguates_and_a_bad_name_or_picture_is_refused(char, tmp_path):
    picture = _picture(tmp_path / "x.png")
    with pytest.raises(SetPartError, match="no attachment"):
        set_part(char, "nope", picture)
    with pytest.raises(SetPartError, match="several files"):
        set_part(char, "open", picture)  # both eyes carry it
    set_part(char, "left_eye/open", picture)
    (tmp_path / "bad.png").write_bytes(b"not a picture")
    with pytest.raises(SetPartError, match="readable"):
        replace_part_art(char, "parts/head.svg", tmp_path / "bad.png")
    (tmp_path / "x.gif").write_bytes(b"GIF89a")
    with pytest.raises(SetPartError, match="not a picture"):
        replace_part_art(char, "parts/head.svg", tmp_path / "x.gif")


def test_a_path_leaving_the_folder_is_refused(char, tmp_path):
    doc = json.loads((char / "character.json").read_text())
    doc["skins"]["default"]["slots"]["head"]["head"]["path"] = "../x.svg"
    (char / "character.json").write_text(json.dumps(doc))
    with pytest.raises(SetPartError, match="leaves"):
        replace_part_art(char, "../x.svg", _picture(tmp_path / "x.png"))


def test_the_command_says_what_it_did(char, tmp_path):
    out = set_part_command("ned", "head", str(_picture(tmp_path / "h.png")), out_dir=str(char.parent))
    assert "now drawn by h.png" in out
    assert "no character" in set_part_command("ghost", "head", "x.png", out_dir=str(char.parent))
