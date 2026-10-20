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
    (voices / "ok.json").write_text(json.dumps({"provider": "elevenlabs", "notes": "warm, slow, a Limerick lilt", "sample_text": "Hello there. " * 10}))
    (voices / "bad.json").write_text(json.dumps({"provider": "elevenlabs", "accent": "limerick", "notes": 3}))
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
