"""The style specs ship as package data and load by name (cutan#4)."""

from __future__ import annotations

import subprocess
import sys

import pytest
import yaml

import cutan
from cutan.styles import (
    STYLE_SPEC_SCHEMA_VERSION,
    UnknownStyleError,
    resolve_style_spec,
    style_spec,
    style_spec_digest,
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
        assert spec["schema_version"] == STYLE_SPEC_SCHEMA_VERSION
        path = style_spec_path(name)
        assert path.is_file()
        assert (path.parent.name, path.parent.parent.name) == ("styles", "cutan")


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
    with pytest.raises(UnknownStyleError, match="the specs are: .*south_park"):
        style_spec(bad)
    with pytest.raises(KeyError):  # so a ChainMap of spec sources falls through it
        style_spec_path(bad)


def test_the_lint_takes_a_name_a_path_or_a_mapping():
    by_name = load_style_spec("reiniger")
    assert by_name == style_spec("reiniger") == resolve_style_spec("reiniger")
    assert load_style_spec(style_spec_path("reiniger")) == by_name
    assert load_style_spec(str(style_spec_path("reiniger"))) == by_name
    assert load_style_spec(by_name) == by_name


def test_a_bare_name_is_always_the_shipped_spec_and_a_local_file_needs_a_path(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "reiniger").write_text("style: reiniger\ntargets: {}\n", "utf-8")
    assert resolve_style_spec("reiniger") == style_spec("reiniger")
    assert resolve_style_spec("./reiniger") == {"style": "reiniger", "targets": {}}
    assert resolve_style_spec(tmp_path / "reiniger") == {
        "style": "reiniger",
        "targets": {},
    }


def test_a_missing_file_named_like_a_style_says_how_to_load_the_shipped_one(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(FileNotFoundError, match=r"style_spec\('oversimplified'\)"):
        resolve_style_spec("oversimplified.yaml")
    with pytest.raises(FileNotFoundError) as e:
        resolve_style_spec("nope.yaml")
    assert "style_spec(" not in str(e.value)
    with pytest.raises(UnknownStyleError):
        resolve_style_spec("nope")


def test_the_digest_names_the_bytes_of_the_shipped_file():
    import hashlib

    for name in style_specs():
        data = style_spec_path(name).read_bytes().replace(b"\r\n", b"\n")
        assert style_spec_digest(name) == hashlib.sha256(data).hexdigest()
    assert len(set(map(style_spec_digest, style_specs()))) == len(style_specs())


def test_a_spec_that_is_not_a_file_on_disk_has_no_path(monkeypatch):
    """Under zipimport a resource is a member of the archive, not a file."""
    import cutan.styles as styles

    class _Member:
        name = "zipped.yaml"

        def is_file(self):
            return True

        def __str__(self):
            return "/no/such/archive.whl/cutan/styles/zipped.yaml"

    monkeypatch.setattr(styles, "_spec_files", lambda: {"zipped": _Member()})
    with pytest.raises(FileNotFoundError, match="style_spec_text"):
        style_spec_path("zipped")


def _run(*args):
    return subprocess.run(
        [sys.executable, "-m", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
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
    assert _run("cutan.styles", "--path").returncode == 2


def test_the_lint_cli_refuses_an_unknown_style_before_decoding(tmp_path):
    res = _run("cutan.verify.style", str(tmp_path / "x.mp4"), "pixar")
    assert res.returncode == 2
    assert "no style spec named 'pixar'" in res.stderr


def test_the_digest_does_not_see_line_endings(monkeypatch):
    """A Windows checkout (CRLF) holds the same spec version as the wheel (LF)."""
    import cutan.styles as styles

    lf = styles._resource("gilliam").read_bytes().replace(b"\r\n", b"\n")

    class _Crlf:
        name = "gilliam.yaml"

        def is_file(self):
            return True

        def read_bytes(self):
            return lf.replace(b"\n", b"\r\n")

    want = style_spec_digest("gilliam")
    monkeypatch.setattr(styles, "_spec_files", lambda: {"gilliam": _Crlf()})
    assert style_spec_digest("gilliam") == want


def test_the_cli_writes_to_a_redirected_text_stream():
    import contextlib
    import io

    from cutan.styles.__main__ import _main

    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        assert _main(["gilliam"]) == 0
    assert out.getvalue() == style_spec_text("gilliam")
