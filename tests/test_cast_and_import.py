"""A cast as data (``cast.yaml``) and a pack into a project (cutan#87)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from an.cli_status import exit_code_of
from cutan import pack as P
from cutan.characters.cast import CastError, cast_steps, run_cast
from cutan.characters.cli import cast as cast_cli

EXAMPLE = Path(__file__).resolve().parents[1] / "skills" / "cutan-production-pack" / "examples" / "the-umbrella"


def test_a_cast_entry_is_the_factory_options_and_its_follow_ups():
    steps = cast_steps(
        {
            "teo": {
                "build": "squat",
                "head_scale": 1.2,
                "palette": {"skin": "#f1c9a5", "hair": "#5a3a22"},
                "mouth_variants": ["happy", "sad"],
                "views": False,
                "sash": True,
                "mouths": ["angry"],
                "half_lid": 0.5,
                "gaze": True,
            },
            "mara": None,  # every option defaulted
        }
    )
    assert [s.argv() for s in steps] == [
        ["an", "character", "new", "teo", "--offline", "--build", "squat", "--head-scale", "1.2",
         "--palette", "skin=#f1c9a5,hair=#5a3a22", "--mouth-variants", "happy,sad", "--no-views", "--sash"],
        ["an", "character", "mouths", "teo", "--variants", "angry"],
        ["an", "character", "add-half-lid", "teo", "--fraction", "0.5"],
        ["an", "character", "add-gaze", "teo"],
        ["an", "character", "new", "mara", "--offline"],
    ]  # fmt: skip
    # every step passes the pack's allow-list: the two forms meet one gate
    for n, s in enumerate(steps, 1):
        P._checked_cast_line(s.argv(), n, "", source=P.CAST_YAML)


@pytest.mark.parametrize(
    "cast, match",
    [
        ({"Teo": {}}, "not a character name"),
        ({"../x": {}}, "not a character name"),
        ({"teo": {"out_dir": "/tmp"}}, "unknown key"),
        ({"teo": {"overwrite": True}}, "unknown key"),
        ({"teo": {"head_scale": "big"}}, "head_scale must be"),
        ({"teo": {"sash": "yes"}}, "sash must be"),
        ({"teo": {"half_lid": True}}, "half_lid must be"),
        ({"teo": "squat"}, "a mapping"),
        ({"teo\n": {}}, "not a character name"),
        ({"teo": {"voice_ref": "x\ny"}}, "short text"),
        ({"teo": {"hat": "x" * 500}}, "short text"),
        ({"teo": {"mouth_variants": [["happy"]]}}, "short text"),
        ({"teo": {"palette": {"skin": ["#fff"]}}}, "short text"),
    ],
)
def test_a_cast_that_could_reach_further_is_refused(cast, match):
    with pytest.raises(CastError, match=match):
        cast_steps(cast)


def test_a_cast_file_that_is_not_a_mapping_is_named(tmp_path):
    f = tmp_path / "cast.yaml"
    f.write_text("- teo\n- mara\n")
    with pytest.raises(CastError, match="mapping"):
        cast_steps(f)
    f.write_text("teo: {build: [\n")
    with pytest.raises(CastError, match="not readable YAML"):
        cast_steps(f)


def test_a_cast_file_cannot_grow_on_the_server(tmp_path):
    """Aliases expand: a few hundred bytes of them are gigabytes in memory."""
    f = tmp_path / "cast.yaml"
    f.write_text("a: &a [x, x]\nteo: {mouth_variants: *a}\n")
    with pytest.raises(CastError, match="aliases"):
        cast_steps(f)
    f.write_text("teo: {}\n" + "# padding\n" * 10_000)
    with pytest.raises(CastError, match="bytes"):
        cast_steps(f)


def test_the_cast_options_are_one_table():
    """The pack's allow-list is derived from the cast file's table."""
    from cutan.characters.cast import FOLLOW_UPS, NEW_OPTIONS

    new = P.CAST_OPTIONS["new"]
    assert {k.lstrip("-").replace("-", "_") for k in new} - {"offline", "no_views"} == set(
        NEW_OPTIONS
    ) - {"views"}
    assert {c for c, _, _ in FOLLOW_UPS.values()} <= set(P.CAST_OPTIONS)


def test_the_example_cast_is_its_old_cast_sh_line_for_line():
    """The skill's example moved from cast.sh to cast.yaml: same commands."""
    argv = [s.argv() for s in cast_steps(EXAMPLE / "cast.yaml")]
    assert argv[0][:4] == ["an", "character", "new", "mara"]
    assert "--palette" in argv[1] and "skin=#f1c9a5,hair=#5a3a22,clothing=#d9a62e,accessory=#c0392b,leg=#3a4a6a" in argv[1]


def test_run_cast_makes_the_characters_and_stops_at_a_failure(tmp_path):
    ok, messages = run_cast({"teo": {"build": "squat", "half_lid": 0.5}}, out_dir=str(tmp_path))
    assert ok, messages
    assert (tmp_path / "teo" / "character.json").is_file()
    assert len(messages) == 2 and "created character" in messages[0]
    # a second `new` of the same name fails (no overwrite): the run stops there
    ok, messages = run_cast({"teo": {}, "mara": {}}, out_dir=str(tmp_path))
    assert not ok and len(messages) == 1
    assert not (tmp_path / "mara").exists()


def test_an_character_cast_reports_and_fails_with_a_status(tmp_path):
    f = tmp_path / "cast.yaml"
    f.write_text("teo: {hat: cap}\n")
    out = cast_cli(str(f), out_dir=str(tmp_path / "chars"))
    assert exit_code_of(out) == 0 and "created character" in out
    f.write_text("teo: {colour: red}\n")
    assert exit_code_of(cast_cli(str(f), out_dir=str(tmp_path / "chars"))) != 0


def test_a_pack_with_both_cast_files_is_refused(tmp_path):
    pack = tmp_path / "pack"
    shutil.copytree(EXAMPLE, pack)
    (pack / "cast.sh").write_text("an character new teo --offline\n")
    with pytest.raises(P.PackError, match="both"):
        P.cast_commands(pack)


def test_import_makes_the_project_and_never_overwrites_one(tmp_path):
    project = tmp_path / "umbrella"
    report = P.import_pack(EXAMPLE, project)
    assert report.ok, report.format()
    assert (project / "scene.md").is_file()
    assert (project / "assets" / "characters" / "teo" / "character.json").is_file()
    assert not (project / "cast.yaml").exists(), "the cast is made, not copied"
    assert report.project == project.resolve()
    again = P.import_pack(EXAMPLE, project)
    assert not again.ok and "exists already" in again.errors[0]
    data = report.to_dict()
    assert data.pop("project") == str(project.resolve()), "the import names its project"
    assert str(tmp_path) not in json.dumps(data), "the checks name no path of this machine"


def test_import_dry_run_is_the_check_and_leaves_nothing(tmp_path):
    project = tmp_path / "umbrella"
    report = P.import_pack(EXAMPLE, project, dry_run=True)
    assert report.ok, report.format()
    assert not project.exists()


def test_an_import_defaults_beside_the_pack_and_never_inside_it(tmp_path, monkeypatch):
    pack = tmp_path / "umbrella"
    shutil.copytree(EXAMPLE, pack)
    inside = P.import_pack(pack, pack / "project")
    assert not inside.ok and "inside the pack" in inside.errors[0]
    assert not (pack / "project").exists()
    monkeypatch.chdir(tmp_path)  # where the pack is: the default must not be the pack
    report = P.import_pack(pack)
    assert report.ok, report.format()
    assert report.project == (tmp_path / "umbrella-project").resolve()
