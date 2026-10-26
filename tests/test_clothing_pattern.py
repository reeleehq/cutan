"""A print on the factory's clothing (cutan#94): an SVG ``<pattern>`` over the
clothing fill of the torso (every view) and the sleeves, under the outline.

Held here: the default is byte-identical (the variety goldens hold that too);
each print draws what it says, where it says; the base fill keeps its
``clothing`` role and the print's literals never collide with a role; the
descriptor records the print; ``add_views`` and the recipe's replay redraw it;
the CLI parses it and refuses a bad spec in one line.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cutan.characters.cli import new as cli_new
from cutan.characters.factory import (
    RECIPE_KEY,
    add_views,
    new_character,
    redraw_digests,
)
from cutan.characters.patterns import (
    PATTERN_ID,
    PATTERN_KINDS,
    ClothingPattern,
    parse_clothing_pattern,
)
from cutan.characters.schema import CharacterDescriptor

CLOTHING_PARTS = ("torso", "arm_l", "arm_r")
VIEW_TORSOS = ("torso_back", "torso_side", "torso_three_quarter")
BARE_PARTS = ("head", "leg_l", "leg_r")


def _make(tmp: Path, name: str = "c", **knobs) -> Path:
    # One seed for every character here, so two drawings differ only by the knobs.
    return new_character(
        tmp, name=name, seed="print", use_dicebear=False, **knobs
    ).parent


def _part(char: Path, part: str) -> str:
    return (char / "parts" / f"{part}.svg").read_text("utf-8")


def _desc(char: Path) -> CharacterDescriptor:
    return CharacterDescriptor.model_validate_json(
        (char / "character.json").read_text("utf-8")
    )


def _files(char: Path) -> dict[str, bytes]:
    """Every part the factory drew (the canonical `<name>.svg` carries the name)."""
    return {
        p.relative_to(char).as_posix(): p.read_bytes()
        for p in (char / "parts").rglob("*.svg")
    }


# --- the default is untouched ---------------------------------------------------


def test_no_pattern_draws_no_pattern_and_records_nothing(tmp_path):
    char = _make(tmp_path)
    for part in (*CLOTHING_PARTS, *VIEW_TORSOS, *BARE_PARTS):
        assert PATTERN_ID not in _part(char, part)
    assert "clothing_pattern" not in _desc(char).metadata
    # `none` and an empty spec are the default, byte for byte.
    assert _files(_make(tmp_path, "d", clothing_pattern="none")) == _files(char)
    assert _files(_make(tmp_path, "e", clothing_pattern="")) == _files(char)


# --- each print draws what it says, where it says -------------------------------


def _tile_png_b64(size=(4, 4)) -> str:
    import base64
    import io

    from PIL import Image

    img = Image.new("RGBA", size, (0, 0, 0, 0))
    for x in range(size[0]):
        for y in range(size[1]):
            if (x + y) % 2 == 0:
                img.putpixel((x, y), (230, 60, 60, 255) if x < size[0] // 2 else (250, 250, 250, 128))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _spec(kind: str):
    return {"kind": "tile", "image": _tile_png_b64()} if kind == "tile" else kind


@pytest.mark.parametrize("kind", [k for k in PATTERN_KINDS if k != "none"])
def test_a_print_covers_the_torso_in_every_view_and_the_sleeves_only(tmp_path, kind):
    char = _make(tmp_path, clothing_pattern=_spec(kind))
    for part in (*CLOTHING_PARTS, *VIEW_TORSOS):
        svg = _part(char, part)
        assert (
            f'<pattern id="{PATTERN_ID}"' in svg and f'fill="url(#{PATTERN_ID})"' in svg
        )
        # The print sits over the base fill and under the outline.
        assert svg.index(f"url(#{PATTERN_ID})") > svg.index('fill="#')
        # The outline rect (`#222` on the front parts, `#222222` on the views) is last.
        assert svg.rindex('fill="none" stroke="#222') > svg.index(f"url(#{PATTERN_ID})")
    for part in BARE_PARTS:
        assert PATTERN_ID not in _part(char, part)


@pytest.mark.parametrize("kind", [k for k in PATTERN_KINDS if k != "none"])
def test_a_patterned_part_is_well_formed_svg_with_one_pattern_definition(
    tmp_path, kind
):
    import xml.etree.ElementTree as ET

    char = _make(tmp_path, clothing_pattern=_spec(kind), sash=True)
    for part in (*CLOTHING_PARTS, *VIEW_TORSOS):
        root = ET.fromstring(_part(char, part))
        patterns = [e for e in root.iter() if e.tag.endswith("pattern")]
        assert len(patterns) == 1 and patterns[0].get("id") == PATTERN_ID
        assert len(list(patterns[0])) >= 1  # the tile draws something


def test_the_colours_and_the_scale_reach_the_print(tmp_path):
    char = _make(
        tmp_path,
        clothing_pattern="floral:base=#e8735a,motif=#ffffff,leaf=#2f6b3a,scale=0.5",
    )
    torso = _part(char, "torso")
    assert 'fill="#e8735a"' in torso  # the base is the clothing colour
    assert "#ffffff" in torso and "#2f6b3a" in torso
    assert 'width="20" height="20"' in torso  # half the tile
    assert _desc(char).metadata["clothing_pattern"] == {
        "kind": "floral",
        "base": "#e8735a",
        "motif": "#ffffff",
        "scale": 0.5,
    }


def test_the_base_fill_keeps_its_clothing_role_and_the_print_never_collides(tmp_path):
    # The motif is the clothing colour: it is nudged, so a clothing swap leaves it.
    char = _make(
        tmp_path,
        clothing_pattern="stripes:motif=#e8735a",
        palette={"clothing": "#e8735a"},
    )
    desc = _desc(char)
    for part in CLOTHING_PARTS:
        roles = desc.colour_roles[f"parts/{part}.svg"]
        assert roles["#e8735a"] == "clothing"
        svg = _part(char, part)
        motif = (
            svg.split(f'<pattern id="{PATTERN_ID}"', 1)[1]
            .split('fill="', 2)[1]
            .split('"')[0]
        )
        assert motif != "#e8735a" and motif not in roles
        assert motif.startswith("#e8735")


def test_a_sash_and_a_print_share_the_torso_under_its_outline(tmp_path):
    torso = _part(
        _make(
            tmp_path,
            sash=True,
            clothing_pattern="check",
            palette={"accessory": "#0a0b0c"},
        ),
        "torso",
    )
    assert "#0a0b0c" in torso and PATTERN_ID in torso
    assert torso.rindex('fill="none" stroke="#222"') > max(
        torso.index("#0a0b0c"), torso.index(f"url(#{PATTERN_ID})")
    )


def test_a_dicebear_body_takes_a_print_too(tmp_path, monkeypatch):
    from cutan.characters import factory

    monkeypatch.setattr(
        factory,
        "fetch_dicebear",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("offline")),
    )
    char = new_character(
        tmp_path, name="db", use_dicebear=True, clothing_pattern="stripes"
    ).parent
    assert PATTERN_ID in _part(char, "torso")


# --- the print is redrawn from the descriptor -----------------------------------


def test_add_views_redraws_the_print_and_the_recipe_replays_it(tmp_path):
    spec = "floral:base=#345678,motif=#fafafa"
    with_views = _make(tmp_path, "a", clothing_pattern=spec)
    later = _make(tmp_path, "b", clothing_pattern=spec, views=False)
    add_views(later)
    for part in VIEW_TORSOS:
        assert _part(later, part) == _part(with_views, part)
    desc = json.loads((with_views / "character.json").read_text("utf-8"))
    assert (
        desc["metadata"][RECIPE_KEY]["steps"][0]["params"]["clothing_pattern"] == spec
    )
    import hashlib

    assert redraw_digests(desc) == {
        p.relative_to(with_views).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in with_views.rglob("*")
        if p.is_file() and p.name != "character.json"
    }


def test_a_mapping_spec_is_the_same_print_as_its_string(tmp_path):
    a = _make(tmp_path, "a", clothing_pattern="check:motif=#111111,scale=2")
    b = _make(
        tmp_path,
        "b",
        clothing_pattern={"kind": "check", "motif": "#111111", "scale": 2},
    )
    assert _files(a) == _files(b)


# --- refusals and the CLI ---------------------------------------------------------


@pytest.mark.parametrize(
    "spec",
    [
        "plaid",
        "stripes:leaf=#000",
        "floral:motif=red",
        "check:scale=9",
        "stripes:x",
        42,
    ],
)
def test_a_bad_spec_is_refused_before_anything_is_drawn(tmp_path, spec):
    with pytest.raises(ValueError):
        _make(tmp_path, clothing_pattern=spec)
    assert not (tmp_path / "c").exists()


def test_the_cli_passes_the_print_and_says_what_is_wrong(tmp_path):
    msg = cli_new(
        "k",
        out_dir=str(tmp_path),
        offline=True,
        clothing_pattern="stripes:motif=#000000",
    )
    assert msg.startswith("created"), msg
    assert _desc(tmp_path / "k").metadata["clothing_pattern"] == {
        "kind": "stripes",
        "motif": "#000000",
    }
    assert "unknown clothing pattern" in cli_new(
        "j", out_dir=str(tmp_path), offline=True, clothing_pattern="plaid"
    )


def test_parse_is_total_over_its_vocabulary():
    assert parse_clothing_pattern("none") is None
    p = parse_clothing_pattern("floral")
    assert isinstance(p, ClothingPattern) and p.as_dict() == {"kind": "floral"}


# --- review of cutan#94: forearms, packs, one clothing colour ---------------------


def test_the_arms_of_a_patterned_character_split_and_keep_the_print(tmp_path):
    from cutan.characters.factory import add_forearms

    desc_path = new_character(
        tmp_path, name="ned", seed="ned", use_dicebear=False, clothing_pattern="floral"
    )
    add_forearms(desc_path.parent)
    for part in ("arm_l", "forearm_l", "arm_r", "forearm_r"):
        text = (desc_path.parent / "parts" / f"{part}.svg").read_text()
        assert text.count('<pattern id="clothing_print"') == 1, part
    assert not (desc_path.parent / "parts" / "hand_l.svg").read_text().count("<pattern")
    digests = redraw_digests(json.loads(desc_path.read_text()))
    assert digests and digests["parts/forearm_l.svg"]  # the recipe still replays it


def test_a_pack_may_ask_for_a_print_and_two_clothing_colours_are_refused(tmp_path):
    from cutan.pack import _checked_cast_line

    line = 'an character new ned --offline --clothing-pattern "floral:base=#e8735a,motif=#ffffff"'
    import shlex

    assert _checked_cast_line(shlex.split(line), 1, line)
    with pytest.raises(ValueError, match="two clothing colours"):
        new_character(
            tmp_path,
            name="ned",
            use_dicebear=False,
            clothing_pattern="check:base=#445566",
            palette={"clothing": "#112233"},
        )
    # the same colour said twice is one colour
    new_character(
        tmp_path,
        name="ned2",
        use_dicebear=False,
        clothing_pattern="check:base=#445566",
        palette={"clothing": "#445566"},
    )


# --- a tile of the caller's own (cutan#132) ------------------------------------------


def test_a_tile_is_drawn_as_rects_in_the_pattern_and_never_as_an_image(tmp_path):
    char = _make(tmp_path, clothing_pattern={"kind": "tile", "image": _tile_png_b64()})
    svg = _part(char, "torso")
    assert "<image" not in svg and "data:image" not in svg
    assert 'fill-opacity="0.502"' in svg  # the translucent pixels keep their alpha
    from cutan.characters.validate import validate_character

    assert not [f for f in validate_character(char).findings if f.severity == "error"]


def test_a_tile_is_recorded_by_its_bytes_and_replays_on_another_machine(tmp_path):
    import hashlib

    spec = {"kind": "tile", "image": _tile_png_b64(), "base": "#345678"}
    char = _make(tmp_path, clothing_pattern=spec)
    desc = json.loads((char / "character.json").read_text("utf-8"))
    assert desc["metadata"]["clothing_pattern"]["image"] == spec["image"]
    assert redraw_digests(desc) == {
        p.relative_to(char).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in char.rglob("*")
        if p.is_file() and p.name != "character.json"
    }


def test_the_tile_s_colours_never_collide_with_a_role_literal(tmp_path):
    char = _make(tmp_path, clothing_pattern={"kind": "tile", "image": _tile_png_b64(), "base": "#e63c3c"})
    svg = _part(char, "torso")
    # the base fill is #e63c3c; the tile's own #e63c3c is nudged off it
    assert svg.count('fill="#e63c3c"') == 1


@pytest.mark.parametrize(
    "spec, why",
    [
        ("tile", "needs image"),
        ({"kind": "tile", "image": "not base64!"}, "base64"),
        ({"kind": "tile", "image": "aGVsbG8="}, "must be a PNG"),
        ({"kind": "tile", "image": _tile_png_b64((40, 4))}, "px a side"),
        ({"kind": "stripes", "image": _tile_png_b64()}, "takes base, motif, scale"),
    ],
)
def test_a_bad_tile_is_refused_in_one_line(tmp_path, spec, why):
    with pytest.raises(ValueError, match=why):
        parse_clothing_pattern(spec)


def test_a_tile_over_the_byte_limit_is_refused():
    import base64
    import io

    from PIL import Image

    noise = Image.frombytes("RGBA", (32, 32), __import__("random").Random(1).randbytes(32 * 32 * 4))
    buf = io.BytesIO()
    noise.save(buf, "PNG")
    assert len(buf.getvalue()) > 3072
    with pytest.raises(ValueError, match="at most 3072 bytes"):
        parse_clothing_pattern({"kind": "tile", "image": base64.b64encode(buf.getvalue()).decode()})


def test_the_cli_reads_a_tile_file_and_records_its_bytes_not_its_path(tmp_path):
    import base64

    png = tmp_path / "tile.png"
    png.write_bytes(base64.b64decode(_tile_png_b64()))
    out = cli_new("t", out_dir=str(tmp_path), offline=True, clothing_pattern=f"tile:image={png},scale=0.5")
    assert "error" not in out.lower(), out
    desc = json.loads((tmp_path / "t" / "character.json").read_text("utf-8"))
    recorded = json.dumps(desc["metadata"])
    assert str(tmp_path) not in recorded and _tile_png_b64() in recorded
    gone = cli_new("u", out_dir=str(tmp_path), offline=True, clothing_pattern="tile:image=/nope.png")
    assert "cannot be read" in gone
