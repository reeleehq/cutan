"""`cutan.pack.check_pack`: the production-pack checker as a function (cutan#87)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from cutan.pack import PackCheck, PackReport, _lint_svgs, check_pack

EVIL = '<svg xmlns="http://www.w3.org/2000/svg"><script>x()</script><rect/></svg>'

EXAMPLE = Path(__file__).resolve().parents[1] / "skills" / "cutan-production-pack" / "examples" / "the-umbrella"


def test_report_shape():
    report = PackReport()
    report.add("svg a.svg", True)
    report.add("voice v", False, "  [error] unknown key 'x'\n  [warning] model_id 'y'")
    assert not report.ok
    assert report.errors == ["voice v: unknown key 'x'"]
    assert report.warnings == ["voice v: model_id 'y'"]
    data = report.to_dict()
    assert data["summary"] == "FAIL: 1/2 checks passed, 1 warning(s)"
    assert [c["ok"] for c in data["checks"]] == [True, False]
    assert "output" not in data["checks"][0]
    json.dumps(report.to_dict(with_output=True))


def test_an_empty_report_is_not_a_pass():
    assert not PackReport().ok


def test_a_silent_failure_still_has_an_error():
    assert PackCheck("an init", False, "").errors == ["failed with no output"]


def test_refused_cast_line_is_a_failed_check_not_an_exception(tmp_path):
    pack = tmp_path / "pack"
    pack.mkdir()
    (pack / "scene.md").write_text("---\n---\n")
    (pack / "cast.sh").write_text("rm -rf /\n")
    report = check_pack(pack)
    assert not report.ok
    assert [c.label for c in report.checks] == ["pack"]
    assert "only `an character" in report.errors[0]


def test_unknown_voice_key_and_notes(tmp_path):
    pack = tmp_path / "pack"
    shutil.copytree(EXAMPLE, pack)
    voices = pack / "assets" / "voices"
    voices.mkdir(parents=True, exist_ok=True)
    (voices / "ok.json").write_text(json.dumps({"provider": "elevenlabs", "notes": "warm, slow, a Yorkshire burr", "sample_text": "Hello there. " * 10}))
    (voices / "bad.json").write_text(json.dumps({"provider": "elevenlabs", "accent": "yorkshire", "notes": 3}))
    from cutan.pack import _lint_voices

    report = PackReport()
    _lint_voices(pack, report)
    verdicts = {c.label: c.ok for c in report.checks}
    assert verdicts["voice ok"] is True
    assert verdicts["voice bad"] is False
    assert any("'accent'" in e for e in report.errors) and any("'notes' must be a string of 20" in e for e in report.errors)


@pytest.mark.parametrize("pack", [EXAMPLE], ids=lambda p: p.name)
def test_example_pack_passes(pack, tmp_path):
    import os
    import sys

    # The `an` subprocess must import this checkout's cutan, as the skill test does.
    root = str(Path(__file__).resolve().parents[1])
    os.environ["PYTHONPATH"] = os.pathsep.join(p for p in (root, os.environ.get("PYTHONPATH")) if p)
    report = check_pack(pack, an_command=(sys.executable, "-m", "an"))
    assert report.ok, report.format()
    assert not report.warnings, report.warnings
    assert report.summary().startswith("PASS")


def _example_copy(tmp_path):
    pack = tmp_path / "pack"
    shutil.copytree(EXAMPLE, pack)
    return pack


def _with_this_checkout(monkeypatch):
    root = str(Path(__file__).resolve().parents[1])
    import os

    monkeypatch.setenv("PYTHONPATH", os.pathsep.join(p for p in (root, os.environ.get("PYTHONPATH")) if p))


def test_code_in_a_pack_is_never_copied_or_imported(tmp_path, monkeypatch):
    """A `dataclasses.py` (or any module) in the pack must not run in the `an` children."""
    _with_this_checkout(monkeypatch)
    pack = _example_copy(tmp_path)
    marker = tmp_path / "ran"
    (pack / "dataclasses.py").write_text(f"open({str(marker)!r}, 'w').write('x')\nraise SystemExit\n", encoding="utf-8")
    (pack / "assets" / "props" / "umbrella" / "parts" / "extra.SVG").write_text("<svg/>", encoding="utf-8")
    report = check_pack(pack)
    assert not marker.exists()
    labels = {c.label: c.ok for c in report.checks}
    assert labels["file dataclasses.py"] is False
    assert labels["file assets/props/umbrella/parts/extra.SVG"] is False


def test_secrets_never_reach_the_children(monkeypatch):
    from cutan.pack import _child_env

    monkeypatch.setenv("ELEVEN_API_KEY", "k")
    monkeypatch.setenv("REELEE_MCP_DOWNLOAD_SECRET", "s")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "a")
    env = _child_env()
    assert not {"ELEVEN_API_KEY", "REELEE_MCP_DOWNLOAD_SECRET", "AWS_ACCESS_KEY_ID"} & set(env)
    assert "PATH" in env


def test_work_is_capped(tmp_path):
    from cutan.pack import MAX_CAST_LINES

    pack = tmp_path / "pack"
    pack.mkdir()
    (pack / "scene.md").write_text("x", encoding="utf-8")
    (pack / "cast.sh").write_text("an character add-views x\n" * (MAX_CAST_LINES + 1), encoding="utf-8")
    report = check_pack(pack)
    assert [c.label for c in report.checks] == ["pack"] and "at most" in report.errors[0]


def test_the_deadline_stops_the_check(tmp_path, monkeypatch):
    _with_this_checkout(monkeypatch)
    report = check_pack(_example_copy(tmp_path), deadline=0.0)
    assert not report.ok and any("ran out of time" in e for e in report.errors)


def test_the_report_names_no_server_path(tmp_path, monkeypatch):
    _with_this_checkout(monkeypatch)
    pack = _example_copy(tmp_path)
    meta = pack / "assets" / "environments" / "bus_stop" / "meta.json"
    meta.write_text(meta.read_text(encoding="utf-8").replace("plates/shelter.svg", "/etc/hostname"), encoding="utf-8")
    report = check_pack(pack)
    text = json.dumps(report.to_dict(with_output=True))
    assert str(tmp_path) not in text and "/etc/hostname" not in text and "/root/" not in text


def _png(path: Path, size: tuple[int, int]) -> None:
    """A picture with a transparent background and an opaque shape in the middle."""
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", size, (0, 0, 0, 0))
    w, h = size
    ImageDraw.Draw(img).ellipse((w // 4, h // 4, 3 * w // 4, 3 * h // 4), fill=(200, 60, 40, 255))
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)


def test_an_all_svg_pack_gets_a_note_and_a_picture_removes_it(tmp_path):
    """Hand-written SVG looks computer-made: the report says so (a note, never a failure)."""
    from cutan.pack import _note_svg_only_art

    pack = _example_copy(tmp_path)
    report = PackReport()
    _note_svg_only_art(pack, report)
    assert len(report.notes) == 1 and "hand-written SVG (3 file(s))" in report.notes[0]
    assert report.to_dict()["notes"] == report.notes and "note: " in report.format()
    _png(pack / "assets" / "environments" / "bus_stop" / "plates" / "sky.png", (64, 36))
    report = PackReport()
    _note_svg_only_art(pack, report)
    assert report.notes == []


def test_a_picture_must_be_what_its_name_says(tmp_path):
    from cutan.pack import _lint_files

    pack = tmp_path / "pack"
    _png(pack / "assets" / "props" / "u" / "parts" / "u.png", (8, 8))
    (pack / "assets" / "props" / "u" / "parts" / "fake.png").write_bytes(b"#!/bin/sh\necho hi\n")
    (pack / "assets" / "props" / "u" / "parts" / "fake.webp").write_bytes(b"RIFF\x00\x00\x00\x00WAVE")
    report = PackReport()
    _lint_files(pack, report)
    assert {c.label for c in report.checks} == {
        "file assets/props/u/parts/fake.png",
        "file assets/props/u/parts/fake.webp",
    }


def test_a_pack_with_pictures_passes(tmp_path, monkeypatch):
    """A plate and a prop as PNG (an#211) check like their SVG versions."""
    _with_this_checkout(monkeypatch)
    pack = _example_copy(tmp_path)
    env = pack / "assets" / "environments" / "bus_stop"
    (env / "plates" / "skyline.svg").unlink()
    _png(env / "plates" / "skyline.png", (1600, 400))
    meta = json.loads((env / "meta.json").read_text())
    for plane in meta["planes"]:
        if plane["name"] == "skyline":
            plane["art"]["src"] = "plates/skyline.png"
    (env / "meta.json").write_text(json.dumps(meta))
    prop = pack / "assets" / "props" / "umbrella"
    (prop / "parts" / "umbrella.svg").unlink()
    _png(prop / "parts" / "umbrella.png", (1024, 1024))
    doc = json.loads((prop / "prop.json").read_text())
    doc["skins"]["default"]["slots"]["body"]["umbrella"]["path"] = "parts/umbrella.png"
    (prop / "prop.json").write_text(json.dumps(doc))
    report = check_pack(pack)
    assert report.ok, report.format()
    assert report.notes == []


def test_a_redrawn_factory_part_may_be_a_picture_named_like_the_factory_s_svg(tmp_path):
    from cutan.pack import _redrawn_problem

    picture = tmp_path / "head.png"
    _png(picture, (8, 8))
    assert "no head.svg" in _redrawn_problem(picture, tmp_path / "head.png")
    (tmp_path / "head.svg").write_text("<svg/>")
    assert _redrawn_problem(picture, tmp_path / "head.png") is None


def test_a_pack_with_a_painted_head_passes_and_the_head_is_the_picture(tmp_path, monkeypatch):
    _with_this_checkout(monkeypatch)
    pack = _example_copy(tmp_path)
    head = pack / "assets" / "characters" / "mara" / "parts" / "head.png"
    _png(head, (200, 200))
    report = check_pack(pack)
    assert report.ok, report.format()
    # the overlay ran (a no-op would be silent): it says what stays the factory's
    assert any("redrawn mara/parts/head.png" in w and "head_side" in w for w in report.warnings), report.warnings


def test_a_picture_and_an_svg_for_the_same_part_are_refused_by_name(tmp_path, monkeypatch):
    _with_this_checkout(monkeypatch)
    pack = _example_copy(tmp_path)
    parts = pack / "assets" / "characters" / "mara" / "parts"
    _png(parts / "head.png", (200, 200))
    (parts / "head.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'/>")
    report = check_pack(pack)
    assert not report.ok and any("two drawings for parts/head" in e for e in report.errors), report.errors


def test_a_picture_s_declared_pixels_are_capped(tmp_path):
    import struct
    import zlib

    from cutan import pack as pack_mod

    pack = tmp_path / "pack"
    big = pack / "assets" / "props" / "u" / "parts" / "big.png"
    big.parent.mkdir(parents=True)
    ihdr = struct.pack(">IIBBBBB", 100_000, 100_000, 8, 6, 0, 0, 0)
    chunk = struct.pack(">I", len(ihdr)) + b"IHDR" + ihdr + struct.pack(">I", zlib.crc32(b"IHDR" + ihdr))
    big.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk)
    assert "over 50,000,000 pixels" in pack_mod._image_problem(big)


def test_an_opaque_prop_picture_gets_a_note(tmp_path):
    from PIL import Image

    from cutan.pack import _note_svg_only_art

    pack = tmp_path / "pack"
    part = pack / "assets" / "props" / "car" / "parts" / "car.jpg"
    part.parent.mkdir(parents=True)
    Image.new("RGB", (16, 16), (255, 255, 255)).save(part)
    report = PackReport()
    _note_svg_only_art(pack, report)
    assert len(report.notes) == 1 and "no transparent background" in report.notes[0]


def test_flux_prompts_say_only_what_is_wanted():
    from cutan.art_brief import image_prompt

    text = image_prompt("sky", "a summer evening", style="south_park", tool="flux")
    assert " no " not in f" {text.lower()} " and "Look:" in text


def test_a_moving_window_plate_holds_only_what_is_at_infinity():
    """Owner finding (2026-10-20): near objects painted into a moving view stay
    still under moving poles; they are separate props (an#484)."""
    from cutan.art_brief import ART_KINDS, VIEWPOINT_RULE, art_guidance

    view = ART_KINDS["window_view"]
    assert "no trees, no poles" in view.framing and "roadside" in " ".join(view.content)
    assert "roadside" in ART_KINDS and "an#484" in ART_KINDS["roadside"].status
    assert "looking back at the driver" in VIEWPOINT_RULE
    assert art_guidance()["viewpoint"] == VIEWPOINT_RULE


def test_the_pack_lint_reads_every_file_a_descriptor_names_by_content(tmp_path):
    """A part under `.txt` holding a <script> is SVG to `an`, so the pack lint fails it."""
    prop = tmp_path / "pack" / "assets" / "props" / "umbrella"
    (prop / "parts").mkdir(parents=True)
    (prop / "parts" / "umbrella.txt").write_text(EVIL, encoding="utf-8")
    (prop / "prop.json").write_text(
        json.dumps({"skins": {"default": {"slots": {"body": {"body": {"path": "parts/umbrella.txt"}}}}}}),
        encoding="utf-8",
    )
    report = PackReport()
    _lint_svgs(tmp_path / "pack", report)
    (check,) = report.checks
    assert check.label == "svg assets/props/umbrella/parts/umbrella.txt"
    assert not check.ok and "script" in check.output


def test_the_pack_lint_does_not_follow_a_reference_out_of_the_asset(tmp_path):
    prop = tmp_path / "pack" / "assets" / "props" / "umbrella"
    prop.mkdir(parents=True)
    (prop.parent / "evil.txt").write_text(EVIL, encoding="utf-8")
    (prop / "prop.json").write_text(
        json.dumps({"skins": {"default": {"slots": {"body": {"body": {"path": "../evil.txt"}}}}}}),
        encoding="utf-8",
    )
    report = PackReport()
    _lint_svgs(tmp_path / "pack", report)
    assert report.checks == []


def test_the_pack_lint_reads_nothing_behind_a_link(tmp_path):
    host = tmp_path / "host"
    host.mkdir()
    secret = '<svg xmlns="http://www.w3.org/2000/svg"><rect fill="url(SECRET)"/></svg>'
    (host / "x.svg").write_text(secret, encoding="utf-8")
    (host / "prop.json").write_text(
        json.dumps({"skins": {"default": {"slots": {"b": {"b": {"path": "x.svg"}}}}}}),
        encoding="utf-8",
    )
    pack = tmp_path / "pack"
    (pack / "assets" / "props").mkdir(parents=True)
    try:
        (pack / "assets" / "props" / "u").symlink_to(host, target_is_directory=True)
        (pack / "linked.svg").symlink_to(host / "x.svg")
    except OSError:
        pytest.skip("no symlinks here")
    report = PackReport()
    _lint_svgs(pack, report)
    assert "SECRET" not in report.format() and report.checks == []
