"""`cutan.pack.check_pack`: the production-pack checker as a function (cutan#87)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from cutan.pack import PackCheck, PackReport, check_pack

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
