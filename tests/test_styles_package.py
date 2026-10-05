"""The style specs ship as package data and load by name (cutan#4)."""

from __future__ import annotations

import subprocess
import sys

import pytest
import yaml

import cutan
from cutan.styles import (
    UnknownStyleError,
    style_spec,
    style_spec_path,
    style_spec_text,
    style_specs,
)
from cutan.verify.style import load_style_spec

SIX = {"south_park", "oversimplified", "kurzgesagt", "gilliam", "reiniger", "norstein"}


def test_the_six_styles_load_by_name_from_the_package():
    assert set(style_specs()) >= SIX
    for name in style_specs():
        spec = style_spec(name)
        assert spec["style"] == name
        assert style_spec_path(name).parent.name == "styles"
        assert style_spec_path(name).parent.parent.name == "cutan"


def test_the_package_root_exports_the_loader():
    assert cutan.style_spec is style_spec and cutan.style_specs is style_specs


def test_each_call_returns_a_new_dict():
    a = style_spec("south_park")
    a["live"]["meta"]["fps"] = 999
    assert style_spec("south_park")["live"]["meta"]["fps"] == 24


def test_the_text_keeps_the_comments():
    assert style_spec_text("south_park").lstrip().startswith("#")
    assert yaml.safe_load(style_spec_text("south_park")) == style_spec("south_park")


@pytest.mark.parametrize(
    "bad", ["pixar", "South_Park", "../styles/south_park", "south_park.yaml", "", None]
)
def test_an_unknown_name_is_refused_with_the_names_there_are(bad):
    with pytest.raises(UnknownStyleError, match="the specs are: gilliam"):
        style_spec(bad)
    with pytest.raises(LookupError):
        style_spec_path(bad)


def test_the_lint_takes_a_name_a_path_or_a_mapping(tmp_path):
    by_name = load_style_spec("reiniger")
    assert load_style_spec(style_spec_path("reiniger")) == by_name
    assert load_style_spec(str(style_spec_path("reiniger"))) == by_name
    assert load_style_spec(by_name) == by_name
    # a file beside the caller wins over the shipped spec of the same name
    edited = tmp_path / "reiniger"
    edited.write_text("style: reiniger\ntargets: {}\n", encoding="utf-8")
    assert load_style_spec(str(edited)) == {"style": "reiniger", "targets": {}}
    # a path that does not exist is a missing file, not an unknown style
    with pytest.raises(FileNotFoundError):
        load_style_spec(str(tmp_path / "nope.yaml"))
    with pytest.raises(UnknownStyleError):
        load_style_spec("nope")


def _run(*args):
    return subprocess.run(
        [sys.executable, "-m", *args], capture_output=True, text=True, check=False
    )


def test_python_m_cutan_styles_lists_prints_and_locates():
    listing = _run("cutan.styles")
    assert listing.returncode == 0, listing.stderr
    assert {line.split("\t")[0] for line in listing.stdout.splitlines()} == set(
        style_specs()
    )
    text = _run("cutan.styles", "gilliam")
    assert text.returncode == 0 and text.stdout == style_spec_text("gilliam")
    path = _run("cutan.styles", "gilliam", "--path")
    assert path.returncode == 0 and path.stdout.strip() == str(
        style_spec_path("gilliam")
    )
    bad = _run("cutan.styles", "pixar")
    assert bad.returncode == 2 and "the specs are" in bad.stderr


def test_the_lint_cli_refuses_an_unknown_style_before_decoding(tmp_path):
    res = _run("cutan.verify.style", str(tmp_path / "x.mp4"), "pixar")
    assert res.returncode == 2
    assert "no style spec named 'pixar'" in res.stderr
