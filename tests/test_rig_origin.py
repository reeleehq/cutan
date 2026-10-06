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
