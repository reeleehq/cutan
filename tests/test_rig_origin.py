"""A character's declared origin (an#338): the stage's rule, read by the factory too.

``CharacterDescriptor`` is an ``an.stage.rig.RigDocument``, so it carries the
optional ``origin``; ``stage_extent`` reads ``an.stage.rig.rig_origin``, the
rule the compiler places the rig by, so the two agree by construction.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from an.stage.rig import RigDocument, bone_positions, rig_origin
from cutan.characters.factory import stage_extent
from cutan.characters.schema import CharacterDescriptor
from cutan.characters.validate import validate_character


def test_a_character_is_a_rig_document_and_an_unset_origin_is_not_written():
    desc = CharacterDescriptor(name="c")
    assert isinstance(desc, RigDocument)
    dumped = desc.model_dump(mode="json")
    assert "origin" not in dumped
    # ...while its own unset view facts are still omitted (its serializer
    # replaces the base's and must do both).
    assert "rest_view" not in dumped and "gait" not in dumped


def test_stage_extent_reads_the_declared_origin():
    desc = CharacterDescriptor(name="c")
    feet_y = bone_positions(desc)["root"][1]
    footed = desc.model_copy(update={"origin": (bone_positions(desc)["root"][0], feet_y)})
    assert rig_origin(footed)[1] == feet_y
    assert stage_extent(footed)["feet"] == 0.0
    assert stage_extent(desc)["feet"] > 0.0
    # The height is the art's, wherever the origin is.
    assert stage_extent(footed)["height"] == stage_extent(desc)["height"]


def test_validate_character_advises_on_an_origin_outside_the_view_box():
    with tempfile.TemporaryDirectory() as d:
        doc = json.loads(CharacterDescriptor(name="c").model_dump_json())
        doc["origin"] = [512.0, 99999.0]
        Path(d, "character.json").write_text(json.dumps(doc), encoding="utf-8")
        report = validate_character(d, name="c")
    findings = [f for f in report.findings if f.ir_path == "character.json#rig"]
    assert findings and all(f.severity != "error" for f in findings), report.findings


def test_a_characters_rest_pose_migration_protects_only_a_posed_legacy_rig():
    """0.3.0 -> 0.4.0 (an#339): the stage's protective step, registered for the
    character kind; a default rig (no posed bone) migrates to the new version
    and gains nothing."""
    from an.ir.migrate import migrate
    from an.stage.rig import REST_POSE_SINCE
    from cutan.characters.schema import CHARACTER_SCHEMA_VERSION

    doc = json.loads(CharacterDescriptor(name="c").model_dump_json())
    doc["schema_version"] = "0.3.0"
    out = migrate(dict(doc), kind="CharacterDescriptor")
    assert out["schema_version"] == CHARACTER_SCHEMA_VERSION == REST_POSE_SINCE["CharacterDescriptor"]
    assert "rest_rotation" not in out
    doc["bones"][0]["rotation_deg"] = 12.0
    assert migrate(dict(doc), kind="CharacterDescriptor")["rest_rotation"] is False


def test_feet_origin_puts_the_stage_point_at_the_feet_for_every_build():
    """an#285's asset half: with `feet_origin`, two builds placed at one `y`
    stand on one line, and `stage_extent` says the feet are AT the point."""
    from cutan.characters.factory import new_character

    feet = {}
    with tempfile.TemporaryDirectory() as d:
        for build in ("regular", "squat", "tall"):
            path = new_character(d, name=build, use_dicebear=False, build=build, feet_origin=True, views=False)
            desc = CharacterDescriptor.model_validate_json(path.read_text(encoding="utf-8"))
            feet[build] = stage_extent(desc)["feet"]
        plain = new_character(d, name="plain", use_dicebear=False, views=False)
        assert "origin" not in json.loads(plain.read_text(encoding="utf-8")), "the default is unchanged"
    assert set(feet.values()) == {0.0}

def test_stage_extent_accepts_the_stored_dict():
    """an#410: the skill writes `stage_extent(desc)`; a `character.json` read
    with `json.load` works as well as the model."""
    desc = CharacterDescriptor(name="c")
    assert stage_extent(json.loads(desc.model_dump_json())) == stage_extent(desc)


def test_validate_character_says_the_migration_kept_a_pose_unapplied():
    """an#407: an old (0.3.0) character hand-edited to rotate an arm."""
    with tempfile.TemporaryDirectory() as d:
        doc = json.loads(CharacterDescriptor(name="c").model_dump_json())
        doc["schema_version"] = "0.3.0"
        next(b for b in doc["bones"] if b["name"] == "arm_l")["rotation_deg"] = 38.0
        Path(d, "character.json").write_text(json.dumps(doc), encoding="utf-8")
        report = validate_character(d, name="c")
    assert any("rest_rotation: true" in f.description for f in report.findings)


def test_an_character_new_stands_a_new_character_on_its_feet_by_default():
    """The maintainer's decision (an#423, 2026-10-09): `an character new` uses
    the feet origin by default; `--no-feet-origin` keeps the bones' middle."""
    from cutan.characters.cli import new

    with tempfile.TemporaryDirectory() as d:
        new("amy", out_dir=d, offline=True, views=False)
        new("bob", out_dir=d, offline=True, views=False, feet_origin=False)
        amy = json.loads(Path(d, "amy", "character.json").read_text(encoding="utf-8"))
        bob = json.loads(Path(d, "bob", "character.json").read_text(encoding="utf-8"))
    assert stage_extent(amy)["feet"] == 0.0
    assert "origin" not in bob and stage_extent(bob)["feet"] > 0.0


def test_an_existing_character_is_converted_only_when_asked_and_says_by_how_much():
    """No migration: an existing character keeps its placement until
    `an character feet-origin` converts it, and the command says how far to
    move its `stage.at` to keep it where it stood. `--undo` goes back."""
    from cutan.characters.cli import feet_origin
    from cutan.characters.factory import new_character

    with tempfile.TemporaryDirectory() as d:
        path = new_character(d, name="old", use_dicebear=False, build="squat", views=False)
        before = json.loads(path.read_text(encoding="utf-8"))
        feet = stage_extent(before)["feet"]
        assert feet > 0.0 and "origin" not in before
        said = feet_origin("old", out_dir=d)
        after = json.loads(path.read_text(encoding="utf-8"))
        assert stage_extent(after)["feet"] == 0.0
        assert f"add {feet:g} x its stage.scale" in said
        # Only `origin` changed.
        assert {k: v for k, v in after.items() if k != "origin"} == before
        assert "already stood there" in feet_origin("old", out_dir=d)
        said = feet_origin("old", out_dir=d, undo=True)
        assert json.loads(path.read_text(encoding="utf-8")) == before
        assert f"add {-feet:g} x" in said
        assert feet_origin("nobody", out_dir=d).startswith("no character at")
