"""Asset references stay inside the asset's folder (cutan#107, an#483).

Each of cutan's own readers refuses a reference that leaves the asset's folder
(by name, or through a symlink) and never reads it: a production pack is
someone else's input.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from an.ir.schema import AssetRef

from cutan.characters.schema import CharacterDescriptor
from cutan.characters.validate import validate_character

SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1" width="1" height="1"><rect/></svg>'

#: How a reference leaves the folder: by name, and through a link.
ESCAPES = ("../outside.svg", "link/outside.svg")


@pytest.fixture()
def outside(tmp_path):
    """A file next to (not inside) the asset folder, a link to its folder, and a read log."""
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "outside.svg").write_text(SVG, encoding="utf-8")
    folder = tmp_path / "chars" / "rae"
    folder.mkdir(parents=True)
    (tmp_path / "chars" / "outside.svg").write_text(SVG, encoding="utf-8")
    try:
        (folder / "link").symlink_to(elsewhere, target_is_directory=True)
    except OSError:  # Windows without the privilege: the `..` escape still runs
        pass
    return SimpleNamespace(folder=folder, reads=[])


@pytest.fixture()
def read_log(outside, monkeypatch):
    """Record every stat/read of a path that resolves outside the asset's folder."""
    root = os.path.realpath(outside.folder)

    def spy(name):
        real = getattr(Path, name)

        def wrapper(self, *a, **kw):
            if not os.path.realpath(self).startswith(root):
                outside.reads.append((name, str(self)))
            return real(self, *a, **kw)

        monkeypatch.setattr(Path, name, wrapper)

    for name in ("exists", "is_file", "read_text", "read_bytes"):
        spy(name)

    def art_size(path):
        outside.reads.append(("art_size", str(path)))
        return (1, 1)

    monkeypatch.setattr("an.stage.raster.art_size", art_size)
    return outside.reads


def _write_descriptor(folder: Path, **edits) -> CharacterDescriptor:
    doc = json.loads(CharacterDescriptor(name="rae").model_dump_json())
    doc.update(edits)
    (folder / "character.json").write_text(json.dumps(doc), encoding="utf-8")
    return CharacterDescriptor.model_validate(doc)


@pytest.mark.parametrize("escape", ESCAPES)
def test_validate_blocks_a_part_that_leaves_the_folder_and_reads_nothing(
    outside, read_log, escape
):
    doc = json.loads(CharacterDescriptor(name="rae").model_dump_json())
    att = next(iter(doc["skins"]["default"]["slots"]["head"].values()))
    att.update(path=escape, width=10.0, height=10.0)
    (outside.folder / "character.json").write_text(json.dumps(doc), encoding="utf-8")
    del read_log[:]
    report = validate_character(outside.folder, name="rae")
    assert any(
        f.severity == "error" and "inside the asset's own folder" in f.description
        for f in report.findings
    ), report.findings
    assert not [r for r in read_log if r[0] in ("art_size",) or escape.split("/")[-1] in r[1]]


@pytest.mark.parametrize("escape", ESCAPES)
def test_validate_blocks_colour_roles_and_source_svg_that_leave_the_folder(outside, escape):
    _write_descriptor(
        outside.folder,
        colour_roles={escape: {"#ffffff": "skin"}},
        source_svg=escape,
    )
    report = validate_character(outside.folder, name="rae")
    named = {f.ir_path for f in report.findings if "inside the asset's own folder" in f.description}
    assert {"character.json#source_svg", f"character.json#colour_roles {escape}"} <= named


@pytest.mark.parametrize("escape", ESCAPES)
def test_a_colour_roles_key_outside_the_folder_is_not_read(outside, read_log, escape):
    from cutan.compile.passes import _recoloured_texture_srcs

    pack = SimpleNamespace(colour_for=lambda role, entity=None: "#123456")
    store = SimpleNamespace(_root=outside.folder.parent)
    doc = {"colour_roles": {escape: {"#ffffff": "skin"}}}
    entity = AssetRef(kind="character", id="rae", store="characters", ref="rae")
    assert _recoloured_texture_srcs(entity, doc, store, pack) == {}
    assert not [r for r in read_log if "outside.svg" in r[1]]


@pytest.mark.parametrize("escape", ESCAPES)
def test_the_factory_stamp_does_not_read_a_source_svg_outside_the_folder(
    outside, read_log, escape
):
    from cutan.characters.factory import stamp_factory_descriptor

    _write_descriptor(outside.folder, source_svg=escape)
    stamp_factory_descriptor(outside.folder)
    assert not [r for r in read_log if "outside.svg" in r[1]]
    assert CharacterDescriptor.model_validate_json(
        (outside.folder / "character.json").read_text()
    ).source is None


def test_the_half_lid_tool_refuses_art_outside_the_folder(outside, read_log):
    from cutan.characters.lids import HalfLidError, add_half_lid

    doc = json.loads(CharacterDescriptor(name="rae").model_dump_json())
    for attachments in doc["skins"]["default"]["slots"].values():
        for att in attachments.values():
            if att["path"].endswith(("eye_l_open.svg", "eye_l_closed.svg")):
                att["path"] = "../outside.svg"
    (outside.folder / "character.json").write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(HalfLidError, match="leaves the character's folder"):
        add_half_lid(outside.folder)
    assert not [r for r in read_log if "outside" in r[1]]
    assert not (outside.folder.parent / "outside_half.svg").exists()


@pytest.mark.parametrize("escape", ESCAPES)
def test_the_generated_head_stamp_does_not_read_a_part_outside_the_folder(
    outside, read_log, escape
):
    from an.ir.assets import AssetSource

    from cutan.characters.factory import stamp_generated_head

    doc = json.loads(CharacterDescriptor(name="rae").model_dump_json())
    doc["skins"]["default"]["slots"]["head"]["head"]["path"] = escape
    (outside.folder / "character.json").write_text(json.dumps(doc), encoding="utf-8")
    stamp_generated_head(outside.folder, AssetSource(provider="x", license="cc0-1.0"))
    assert not [r for r in read_log if "outside.svg" in r[1]]
