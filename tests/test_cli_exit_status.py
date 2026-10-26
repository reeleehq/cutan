"""`an character new|validate` exit non-zero when they report a failure (an#480)."""

from __future__ import annotations

from typer.testing import CliRunner

from an.__main__ import build_app

runner = CliRunner()


def _run(*args):
    return runner.invoke(build_app(), ["character", *args])


def test_new_with_an_unknown_build_exits_1(tmp_path):
    out = _run("new", "zz", "--out-dir", str(tmp_path), "--offline", "--build", "squatt")
    assert "unknown build" in out.output and out.exit_code == 1


def test_validate_of_a_missing_character_exits_1(tmp_path):
    out = _run("validate", "nosuch", "--out-dir", str(tmp_path))
    assert "FAILED" in out.output and out.exit_code == 1


def test_a_character_that_is_made_and_validates_exits_0(tmp_path):
    made = _run("new", "zz", "--out-dir", str(tmp_path), "--offline")
    assert made.exit_code == 0, made.output
    ok = _run("validate", "zz", "--out-dir", str(tmp_path))
    assert ok.exit_code == 0, ok.output


def test_a_command_on_a_missing_character_exits_1(tmp_path):
    out = _run("add-views", "nosuch", "--out-dir", str(tmp_path))
    assert "no character at" in out.output and out.exit_code == 1
