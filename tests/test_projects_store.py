"""The projects store: backend by configuration, the read-through materialisation,
the write half (``push_project``, cutan#91) and where ``an init --id`` puts a project."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import cutan.projects_store as module
from cutan.projects_store import (
    STORE_RECORD,
    ProjectsStoreSettings,
    materialize_project,
    new_project_dir,
    projects_store,
    push_project,
    read_record,
)

S3 = ProjectsStoreSettings(backend="s3")


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
    out = materialize_project("p1", settings=S3, store=store, cache=tmp_path)
    assert (out / "a.txt").read_bytes() == b"aa"
    assert (out / "sub" / "b.txt").read_bytes() == b"b"
    assert not (tmp_path / "p2").exists()
    # The folder says which store it belongs to.
    assert read_record(out)["store"] == S3.coordinates()


def test_a_project_id_is_one_folder_name(tmp_path):
    with pytest.raises(ValueError, match="one folder name"):
        materialize_project("../escape", settings=S3, store={}, cache=tmp_path)
    with pytest.raises(ValueError, match="one folder name"):
        push_project("a/b", folder=tmp_path, settings=S3, store={})
    with pytest.raises(ValueError, match="one folder name"):
        new_project_dir("", default=tmp_path, settings=ProjectsStoreSettings())


# ------------------------------------------------------------ the write half


def _project(tmp_path: Path, name: str = "p1") -> Path:
    """A project folder: sources, a derived shot cache and a run's work dir."""
    folder = tmp_path / "cache" / name
    (folder / "artifacts" / "audio").mkdir(parents=True)
    (folder / "artifacts" / "shot_cache" / "blobs").mkdir(parents=True)
    (folder / ".an" / "render_work" / "runs" / "r1").mkdir(parents=True)
    (folder / "scene.md").write_bytes(b"# scene")
    (folder / "artifacts" / "audio" / "a.wav").write_bytes(b"wav")
    (folder / "artifacts" / "shot_cache" / "blobs" / "x").write_bytes(b"blob")
    (folder / ".an" / "render_work" / "runs" / "r1" / ".live").write_bytes(b"")
    return folder


def test_push_writes_everything_once_then_only_what_changed(tmp_path):
    folder = _project(tmp_path)
    store: dict = {}
    r = push_project("p1", folder=folder, settings=S3, store=store)
    assert r.written == ("artifacts/audio/a.wav", "scene.md")
    assert r.excluded == (
        ".an/render_work/runs/r1/.live",
        "artifacts/shot_cache/blobs/x",
    )
    assert r.unchanged == () and r.deleted == ()
    assert set(store) == {
        "p1/scene.md",
        "p1/artifacts/audio/a.wav",
        f"p1/{STORE_RECORD}",
    }
    assert store["p1/scene.md"] == b"# scene"
    record = json.loads(store[f"p1/{STORE_RECORD}"])
    assert record["store"] == S3.coordinates()
    assert set(record["files"]) == {"scene.md", "artifacts/audio/a.wav"}
    assert record["files"]["scene.md"]["size"] == 7
    assert read_record(folder)["files"] == record["files"]
    assert str(r) == "p1: 2 written, 0 unchanged, 2 kept local, 0 deleted"

    # Nothing changed: nothing is written.
    r2 = push_project("p1", folder=folder, settings=S3, store=store)
    assert r2.written == () and r2.unchanged == ("artifacts/audio/a.wav", "scene.md")

    # An edit that keeps the size is caught by the hash; a new file is written.
    (folder / "scene.md").write_bytes(b"# SCENE")
    (folder / "notes.txt").write_bytes(b"n")
    r3 = push_project("p1", folder=folder, settings=S3, store=store)
    assert r3.written == ("notes.txt", "scene.md")
    assert store["p1/scene.md"] == b"# SCENE"
    assert "scene.md" in json.loads(store[f"p1/{STORE_RECORD}"])["files"]


def test_push_without_a_record_compares_with_the_store(tmp_path):
    """The ad hoc loop's case: the store holds the files but no record."""
    folder = _project(tmp_path)
    store = {"p1/scene.md": b"# scene", "p1/artifacts/audio/a.wav": b"old"}
    r = push_project("p1", folder=folder, settings=S3, store=store)
    assert r.written == ("artifacts/audio/a.wav",)
    assert r.unchanged == ("scene.md",)
    assert store["p1/artifacts/audio/a.wav"] == b"wav"
    assert f"p1/{STORE_RECORD}" in store


def test_delete_missing_mirrors_the_pushed_set(tmp_path):
    folder = _project(tmp_path)
    store = {
        "p1/old.txt": b"x",
        "p1/artifacts/shot_cache/blobs/y": b"y",  # uploaded by hand, derived
        "p2/keep.txt": b"k",
    }
    r = push_project("p1", folder=folder, settings=S3, store=store)
    assert r.deleted == () and "p1/old.txt" in store
    r = push_project("p1", folder=folder, settings=S3, store=store, delete_missing=True)
    assert r.deleted == ("artifacts/shot_cache/blobs/y", "old.txt")
    assert "p2/keep.txt" in store
    assert set(store) == {
        "p1/scene.md",
        "p1/artifacts/audio/a.wav",
        f"p1/{STORE_RECORD}",
        "p2/keep.txt",
    }


def test_push_needs_a_folder(tmp_path):
    with pytest.raises(FileNotFoundError, match="no project folder"):
        push_project("p1", folder=tmp_path / "nope", settings=S3, store={})


def test_exclude_is_a_seam(tmp_path):
    folder = _project(tmp_path)
    store: dict = {}
    r = push_project(
        "p1", folder=folder, settings=S3, store=store, exclude=("scene.md",)
    )
    assert r.excluded == ("scene.md",)
    assert "p1/artifacts/shot_cache/blobs/x" in store


def test_push_then_materialize_elsewhere_round_trips(tmp_path):
    folder = _project(tmp_path)
    store: dict = {}
    push_project("p1", folder=folder, settings=S3, store=store)
    out = materialize_project("p1", settings=S3, store=store, cache=tmp_path / "other")
    assert (out / "scene.md").read_bytes() == b"# scene"
    assert (out / "artifacts" / "audio" / "a.wav").read_bytes() == b"wav"
    assert not (out / "artifacts" / "shot_cache").exists()
    # The record travelled: a push from the other folder writes nothing.
    r = push_project("p1", folder=out, settings=S3, store=store)
    assert r.written == ()


def test_local_push_of_the_project_folder_is_a_noop(tmp_path, monkeypatch):
    monkeypatch.setenv("CUTAN_HOME", str(tmp_path))
    folder = tmp_path / "projects" / "p1"
    folder.mkdir(parents=True)
    (folder / "scene.md").write_bytes(b"hi")
    r = push_project("p1")
    assert r.folder == folder and r.written == () and r.unchanged == ("scene.md",)
    assert read_record(folder)["store"] == {"backend": "local"}


# ------------------------------------------------------------ an init --id


def test_new_project_dir_is_the_default_on_the_local_backend(tmp_path):
    local = ProjectsStoreSettings()
    assert (
        new_project_dir("p1", default=tmp_path / "d", settings=local) == tmp_path / "d"
    )


def test_new_project_dir_on_s3_is_the_cache_folder_with_a_record(tmp_path):
    store = {"p1/scene.md": b"existing"}
    out = new_project_dir(
        "p1", default=tmp_path / "d", settings=S3, store=store, cache=tmp_path / "cache"
    )
    assert out == tmp_path / "cache" / "p1"
    assert (out / "scene.md").read_bytes() == b"existing"  # read through first
    assert read_record(out)["store"]["bucket"] == "tw-apps"
    new = new_project_dir(
        "p9", default=tmp_path / "d", settings=S3, store=store, cache=tmp_path / "cache"
    )
    assert new == tmp_path / "cache" / "p9" and new.is_dir()
    assert read_record(new) == {"store": S3.coordinates()}


def test_an_init_by_id_on_s3_lands_in_the_cache_and_is_pushable(tmp_path, monkeypatch):
    """Through `an init <id> --id --genre cutout_animation` (the `projects.dir.cutan`
    service, an API level 7), with the S3 store replaced by a dict."""
    from an.tools import init as init_cli

    monkeypatch.delenv("CUTAN_HOME", raising=False)
    monkeypatch.setenv("CUTAN_PROJECTS_BACKEND", "s3")
    monkeypatch.setenv("CUTAN_CACHE", str(tmp_path / "cache"))
    store: dict = {}
    monkeypatch.setattr(module, "projects_store", lambda settings=None: store)

    out = init_cli("alice-and-bob", id=True, genre="cutout_animation")
    folder = tmp_path / "cache" / "projects" / "alice-and-bob"
    assert out.endswith(str(folder.resolve()))
    assert (folder / "scene.md").is_file()
    assert read_record(folder)["store"]["prefix"] == S3.prefix
    assert store == {}  # init writes locally; the push is explicit

    r = push_project("alice-and-bob")
    assert r.folder == folder and "scene.md" in r.written
    assert store["alice-and-bob/scene.md"] == (folder / "scene.md").read_bytes()
    # A second `an init` of the same id refuses to clobber the project.
    with pytest.raises(FileExistsError):
        init_cli("alice-and-bob", id=True, genre="cutout_animation")
