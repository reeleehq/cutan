"""The factory's recipe (an#292): every drawing call that made a character,
recorded with its parameters, so its bytes can be re-derived on any machine.

`redraw_digests` is what lets a factory stamp be verified away from the machine
that drew it. It can only ever confirm the factory's own output: carved or
hand-drawn bytes are never what it draws, and a DiceBear head (from the
network) is never replayed.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from an.genres import service
from cutan.characters.factory import (
    RECIPE_KEY,
    add_views,
    new_character,
    redraw_digests,
)


def _files(char: Path) -> dict[str, str]:
    return {
        p.relative_to(char).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in char.rglob("*")
        if p.is_file() and p.name != "character.json"
    }


def _desc(char: Path) -> dict:
    return json.loads((char / "character.json").read_text(encoding="utf-8"))


def test_the_recipe_replays_to_the_very_bytes_drawn(tmp_path):
    char = new_character(tmp_path, name="kim", use_dicebear=False, views=False,
                         build="squat", hat="cap", palette={"skin": "#fbd9b5"},
                         head_scale=1.2).parent
    add_views(char)
    recipe = _desc(char)["metadata"][RECIPE_KEY]
    assert [s["call"] for s in recipe["steps"]] == ["new_character", "add_views"]
    assert "out_dir" not in recipe["steps"][0]["params"]
    assert redraw_digests(_desc(char)) == _files(char)


def test_an_edited_recipe_does_not_re_derive_the_bytes(tmp_path):
    char = new_character(tmp_path, name="kim", use_dicebear=False).parent
    desc = _desc(char)
    desc["metadata"][RECIPE_KEY]["steps"][0]["params"]["build"] = "squat"
    assert redraw_digests(desc) != _files(char)


@pytest.mark.parametrize(
    "edit",
    [
        lambda m: m.pop(RECIPE_KEY),
        lambda m: m[RECIPE_KEY].update(version=99),
        lambda m: m.update(dicebear_style="lorelei"),  # a head from the network
        lambda m: m[RECIPE_KEY]["steps"].append({"call": "os.remove", "params": {}}),
    ],
)
def test_what_cannot_be_replayed_confirms_nothing(tmp_path, edit):
    char = new_character(tmp_path, name="kim", use_dicebear=False).parent
    desc = _desc(char)
    edit(desc["metadata"])
    assert redraw_digests(desc) == {}


def test_the_core_reaches_it_as_a_service():
    assert service("credits.factory_redraw") is redraw_digests
