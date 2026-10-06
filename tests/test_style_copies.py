"""Copies of a style spec record it, and `an validate` says when they are stale (cutan#19)."""

from __future__ import annotations

import pytest

from an.ir.schema import Dialogue, Meta, SceneIR, Shot

from cutan.styles import style_pack, style_spec_digest, style_voice


def _validate(pack=None, voices=None):
    from an.ir.validate import validate_semantic

    line = Dialogue(speaker="n", text="He did not.", voice_ref="dad_voice")
    scene = SceneIR(
        meta=Meta(style_pack=pack.name if pack is not None else None),
        timeline=[Shot(id="s", dialogue=[line])],
    )
    styles = {pack.name: pack.model_dump(mode="json")} if pack is not None else None
    report = validate_semantic(scene, available_styles=styles, available_voices=voices)
    return [f for f in report.findings if "copied from" in f.description]


def test_copies_record_the_spec_they_came_from():
    origin = {"name": "oversimplified", "sha256": style_spec_digest("oversimplified")}
    assert style_pack("oversimplified").metadata["style_spec"] == origin
    assert style_voice("oversimplified", "eager")["metadata"]["style_spec"] == origin


def test_a_current_copy_is_not_said():
    voice = {**style_voice("oversimplified", "eager"), "voice_id": "x"}
    assert _validate(style_pack("oversimplified"), {"dad_voice": voice}) == []


def test_a_copy_of_an_older_spec_is_said_with_what_to_rederive():
    pack = style_pack("oversimplified")
    pack.metadata["style_spec"]["sha256"] = "0" * 64
    voice = {**style_voice("oversimplified", "eager"), "voice_id": "x"}
    voice["metadata"]["style_spec"]["sha256"] = "1" * 64
    found = _validate(pack, {"dad_voice": voice})
    by_path = {f.ir_path: f for f in found}
    assert set(by_path) == {"meta/style_pack", "voices/dad_voice"}
    assert all(f.severity == "warning" for f in found)
    assert 'style_pack("oversimplified")' in by_path["meta/style_pack"].description
    assert 'style_voice("oversimplified"' in by_path["voices/dad_voice"].description


@pytest.mark.parametrize("origin", [None, {"name": "oversimplified"}, {"name": "my_style", "sha256": "0" * 64}])
def test_a_copy_without_a_comparable_origin_is_never_said(origin):
    """No record, no digest, or a spec that is not shipped: nothing to compare with."""
    voice = {"voice_id": "x", **({"metadata": {"style_spec": origin}} if origin else {})}
    assert _validate(voices={"dad_voice": voice}) == []
