"""The nw genre declaration stays honest and stays optional.

Both properties are load-bearing for hosts that catalog the federation's genres:
``import an`` must not drag in nw (so a host without nw can still use ``an``), and
the declared genre must not claim an engine it does not have.
"""

import importlib.util
import subprocess
import sys

import pytest

#: Two of the three tests here need nw — `an/genre.py` builds an `nw.Genre`, so
#: even importing `cutan.nw` requires it. Exactly ONE does not, and it is the one
#: that matters most to a host *without* nw: the subprocess check that `import an`
#: gains no hard nw dependency.
#:
#: So the gate goes on the tests, not on the module. A module-level
#: `importorskip("nw")` — which is what this file used to have — would abort the
#: import and take the boundary guard down with it, which is how it came never to
#: have run in CI. See tests/test_browser_gate.py (an#22).
needs_nw = pytest.mark.skipif(
    importlib.util.find_spec("nw") is None, reason="nw not installed"
)


def _has_mapping_store() -> bool:
    try:
        from lacing.store import MappingStore  # noqa: F401
    except ImportError:
        return False
    return importlib.util.find_spec("nw.storage") is not None


#: Creating a project needs nw's storage seam and lacing's MappingStore (nw#101).
needs_storage = pytest.mark.skipif(
    importlib.util.find_spec("nw") is None or not _has_mapping_store(),
    reason="needs nw.storage and lacing.store.MappingStore",
)


def test_importing_an_does_not_import_nw():
    """``an`` gains no hard nw dependency from the genre module.

    Checked in a subprocess because another test in this file imports nw, so an
    in-process ``sys.modules`` check would pass for the wrong reason.
    """
    code = "import an, sys; assert 'nw' not in sys.modules"
    assert subprocess.run([sys.executable, "-c", code]).returncode == 0


@needs_nw
def test_genre_is_available_and_ready():
    from cutan.nw import CUTOUT_ANIMATION

    assert CUTOUT_ANIMATION.status == "available"
    # Engine-less at the nw level (like muvid's genres): offered through ops, so
    # it must not declare Transform or strategy names that do not resolve.
    assert CUTOUT_ANIMATION.transform_names == ()
    assert CUTOUT_ANIMATION.strategy_names == ()
    assert CUTOUT_ANIMATION.is_ready()


@needs_nw
def test_genre_registers_under_its_slug():
    import nw

    from cutan.nw import CUTOUT_ANIMATION, CUTOUT_ANIMATION_SLUG

    assert nw.get_genre(CUTOUT_ANIMATION_SLUG) is CUTOUT_ANIMATION


@needs_storage
def test_a_host_creates_a_project_where_it_asks_and_reopens_it_by_path(tmp_path):
    import nw

    from cutan.nw import CUTOUT_ANIMATION_SLUG, GRAPH_SUBPATH

    nw.create_genre_project(
        CUTOUT_ANIMATION_SLUG, "u@x", "p1", title="T", projects_dir=tmp_path
    )
    root = tmp_path / "p1"
    assert (root / "an.toml").is_file() and (root / "project.json").is_file()
    # nw's graph lives in the project's dol store, not in a SQLite file beside it.
    assert not list(root.glob("*.sqlite"))
    assert any(root.joinpath(*GRAPH_SUBPATH).iterdir())
    # A host that knows only the path reaches the same graph and genre.
    proj = nw.Project(root)
    assert isinstance(proj.storage, nw.MappingStorage)
    assert proj.resolved_genre()["genre"] == CUTOUT_ANIMATION_SLUG
    assert nw.genre_op(CUTOUT_ANIMATION_SLUG, "status").run(proj, {})["films"] == []


@needs_storage
def test_render_records_a_film_that_goes_stale_when_the_scene_changes(
    tmp_path, monkeypatch
):
    import an.render

    import nw
    from cutan.nw import CUTOUT_ANIMATION_SLUG

    def fake_render(project_dir, *, output_name, **_):
        out = tmp_path / "p" / "output" / f"{output_name}.mp4"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"not really an mp4")
        return out

    monkeypatch.setattr(an.render, "render_project", fake_render)
    nw.create_genre_project(CUTOUT_ANIMATION_SLUG, "u@x", "p", projects_dir=tmp_path)
    proj = nw.Project(tmp_path / "p")
    status = nw.genre_op(CUTOUT_ANIMATION_SLUG, "status")

    result = nw.genre_op(CUTOUT_ANIMATION_SLUG, "render").run(proj, {})
    assert result["path"] == "output/main.mp4"
    assert status.run(proj, {})["films"] == [
        {"output_name": "main", "path": "output/main.mp4", "stale": False}
    ]

    scene = tmp_path / "p" / "scene.md"
    scene.write_text(scene.read_text() + "\n<!-- edited -->\n")
    assert status.run(proj, {})["films"][0]["stale"] is True
    nw.genre_op(CUTOUT_ANIMATION_SLUG, "render").run(proj, {})
    assert [f["stale"] for f in status.run(proj, {})["films"]] == [False]
