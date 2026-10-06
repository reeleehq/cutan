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
    # A turnaround added right after the drawing is the drawing with views on.
    assert [s["call"] for s in recipe["steps"]] == ["new_character"]
    assert recipe["steps"][0]["params"]["views"] is True
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


# ---------------------------------------------------------------- review round


def _with_steps(char: Path, steps: list) -> dict:
    desc = _desc(char)
    desc["metadata"][RECIPE_KEY]["steps"] = steps
    return desc


def test_r1_a_recipe_cannot_reach_outside_its_scratch_folder(tmp_path):
    """A `name` that is a path, or `overwrite`, never reaches the factory."""
    char = new_character(tmp_path, name="kim", use_dicebear=False).parent
    precious = tmp_path / "precious"
    precious.mkdir()
    (precious / "keep.txt").write_text("mine", encoding="utf-8")
    params = _desc(char)["metadata"][RECIPE_KEY]["steps"][0]["params"]
    for bad in (
        {**params, "name": str(precious)},
        {**params, "name": "../escaped"},
        {**params, "overwrite": True},
        {**params, "out_dir": str(precious)},
        {**params, "unknown_knob": 1},
    ):
        assert redraw_digests(_with_steps(char, [{"call": "new_character", "params": bad}])) == {}
    assert (precious / "keep.txt").read_text(encoding="utf-8") == "mine"
    assert not (tmp_path / "escaped").exists()


def test_r2_no_second_drawing_and_never_the_network(tmp_path):
    char = new_character(tmp_path, name="kim", use_dicebear=False).parent
    first = _desc(char)["metadata"][RECIPE_KEY]["steps"][0]
    nested = {"call": "new_character", "params": {**first["params"], "name": "x",
                                                  "use_dicebear": True, "style": "adventurer"}}
    assert redraw_digests(_with_steps(char, [first, nested])) == {}
    assert redraw_digests(_with_steps(char, [first, {"params": {}}])) == {}


def test_r3_a_recipe_is_bounded(tmp_path):
    char = new_character(tmp_path, name="kim", use_dicebear=False).parent
    first = _desc(char)["metadata"][RECIPE_KEY]["steps"][0]
    views = {"call": "add_views", "params": {}}
    assert redraw_digests(_with_steps(char, [first, *[views] * 20])) == {}


def test_r4_only_what_the_replay_wrote_and_stamped_counts(tmp_path, monkeypatch):
    """Bytes swapped into the folder outside the factory's writes are not proved,
    even while the swap is in force; and a memo never outlives the code it ran."""
    from cutan.characters import factory

    carved = b"<svg>a head nobody has seen</svg>"
    original = factory.stamp_factory_parts

    def swap_then_stamp(char_dir, paths, **kwargs):
        (Path(char_dir) / "parts" / "head.svg").write_bytes(carved)
        return original(char_dir, paths, **kwargs)

    monkeypatch.setattr(factory, "stamp_factory_parts", swap_then_stamp)
    char = new_character(tmp_path, name="zed", use_dicebear=False, views=False, gaze=False).parent
    swapped = hashlib.sha256(carved).hexdigest()
    assert redraw_digests(_desc(char)).get("parts/head.svg") != swapped
    monkeypatch.setattr(factory, "stamp_factory_parts", original)
    assert redraw_digests(_desc(char)).get("parts/head.svg") != swapped
