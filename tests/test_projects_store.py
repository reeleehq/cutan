"""The projects store: backend by configuration, and the read-through materialisation."""

from cutan.projects_store import (
    ProjectsStoreSettings,
    materialize_project,
    projects_store,
)


def test_cutan_home_forces_local():
    env = {"CUTAN_PROJECTS_BACKEND": "s3", "CUTAN_HOME": "/x"}
    assert ProjectsStoreSettings.from_environ(env).backend == "local"


def test_local_store_and_materialize(tmp_path, monkeypatch):
    monkeypatch.setenv("CUTAN_HOME", str(tmp_path))
    (tmp_path / "projects" / "p1").mkdir(parents=True)
    (tmp_path / "projects" / "p1" / "scene.md").write_bytes(b"hi")
    assert projects_store()["p1/scene.md"] == b"hi"
    assert materialize_project("p1") == tmp_path / "projects" / "p1"


def test_materialize_reads_through_cache(tmp_path):
    store = {"p1/a.txt": b"aa", "p1/sub/b.txt": b"b", "p2/c.txt": b"c"}
    s3 = ProjectsStoreSettings(backend="s3")
    out = materialize_project("p1", settings=s3, store=store, cache=tmp_path)
    assert (out / "a.txt").read_bytes() == b"aa"
    assert (out / "sub" / "b.txt").read_bytes() == b"b"
    assert not (tmp_path / "p2").exists()
