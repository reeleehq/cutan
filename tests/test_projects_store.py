"""The projects store: backend by configuration, the read-through materialisation,
the write half (``push_project``, cutan#91) and where ``an init --id`` puts a project."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import cutan.projects_store as module
from cutan import PROJECT_STORE_RECORD
from cutan.projects_store import (
    DEFAULT_PUSH_EXCLUDES,
    STORE_RECORD,
    ProjectsStoreSettings,
    materialize_project,
    new_project_dir,
    projects_store,
    push_project,
    read_record,
)

S3 = ProjectsStoreSettings(backend="s3")
RECORD = f"p1/{STORE_RECORD}"


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
    store = {"p1/a.txt": b"aa", "p1/sub/b.txt": b"b", "p2/c.txt": b"c", "p1/sub/": b""}
    out = materialize_project("p1", settings=S3, store=store, cache=tmp_path)
    assert (out / "a.txt").read_bytes() == b"aa"
    assert (out / "sub" / "b.txt").read_bytes() == b"b"
    assert not (tmp_path / "p2").exists()
    # The folder says which store it belongs to; a directory marker is not a file.
    assert read_record(out)["store"] == S3.coordinates()
    assert not (out / "sub").is_file()


def test_a_project_id_is_one_folder_name(tmp_path):
    with pytest.raises(ValueError, match="one folder name"):
        materialize_project("../escape", settings=S3, store={}, cache=tmp_path)
    with pytest.raises(ValueError, match="one folder name"):
        push_project("a/b", folder=tmp_path, settings=S3, store={})
    with pytest.raises(ValueError, match="one folder name"):
        new_project_dir("", default=tmp_path, settings=ProjectsStoreSettings())


def test_the_record_is_a_persisted_identifier():
    assert STORE_RECORD == PROJECT_STORE_RECORD == ".an/projects_store.json"


def test_the_default_excludes_cover_what_an_keeps_out_of_git():
    from an.project import PROJECT_GITIGNORE

    assert set(PROJECT_GITIGNORE) <= set(DEFAULT_PUSH_EXCLUDES)
    assert {"artifacts/shot_cache/", ".an/render_work/", ".git/"} <= set(
        DEFAULT_PUSH_EXCLUDES
    )


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


def _push(project_id, folder, store, **kw):
    return push_project(project_id, folder=folder, settings=S3, store=store, **kw)


def test_push_writes_everything_once_then_only_what_changed(tmp_path):
    folder = _project(tmp_path)
    store: dict = {}
    r = _push("p1", folder, store)
    assert r.written == ("artifacts/audio/a.wav", "scene.md")
    assert r.excluded == (
        ".an/render_work/runs/r1/.live",
        "artifacts/shot_cache/blobs/x",
    )
    assert r.unchanged == () and r.deleted == () and r.stale == () and r.conflicts == ()
    assert set(store) == {"p1/scene.md", "p1/artifacts/audio/a.wav", RECORD}
    assert store["p1/scene.md"] == b"# scene"
    record = json.loads(store[RECORD])
    assert record["store"] == S3.coordinates()
    assert set(record["files"]) == {"scene.md", "artifacts/audio/a.wav"}
    assert record["files"]["scene.md"]["size"] == 7
    assert read_record(folder)["files"] == record["files"]
    assert str(r) == "p1: 2 written, 0 unchanged, 2 kept local, 0 deleted"

    # Nothing changed: nothing is written, and neither record is rewritten.
    before = (store[RECORD], (folder / STORE_RECORD).read_bytes())
    r2 = _push("p1", folder, store)
    assert r2.written == () and r2.unchanged == ("artifacts/audio/a.wav", "scene.md")
    assert (store[RECORD], (folder / STORE_RECORD).read_bytes()) == before

    # An edit that keeps the size is caught by the hash; a new file is written.
    (folder / "scene.md").write_bytes(b"# SCENE")
    (folder / "notes.txt").write_bytes(b"n")
    r3 = _push("p1", folder, store)
    assert r3.written == ("notes.txt", "scene.md")
    assert store["p1/scene.md"] == b"# SCENE"
    assert "notes.txt" in json.loads(store[RECORD])["files"]


def test_push_without_a_record_compares_with_the_store(tmp_path):
    """The ad hoc loop's case: the store holds the files but no record, so the
    folder's differences win."""
    folder = _project(tmp_path)
    store = {"p1/scene.md": b"# scene", "p1/artifacts/audio/a.wav": b"old"}
    r = _push("p1", folder, store)
    assert r.written == ("artifacts/audio/a.wav",)
    assert r.unchanged == ("scene.md",)
    assert store["p1/artifacts/audio/a.wav"] == b"wav"
    assert RECORD in store


def test_a_file_the_store_lost_is_restored(tmp_path):
    folder = _project(tmp_path)
    store: dict = {}
    _push("p1", folder, store)
    del store["p1/scene.md"]
    assert _push("p1", folder, store).written == ("scene.md",)


def _two_machines(tmp_path):
    """A pushed by machine A; B pulls it into its own cache."""
    a = _project(tmp_path)
    store: dict = {}
    _push("p1", a, store)
    b = materialize_project("p1", settings=S3, store=store, cache=tmp_path / "B")
    assert (b / "scene.md").read_bytes() == b"# scene"
    assert read_record(b)["files"] == json.loads(store[RECORD])["files"]
    return a, b, store


def test_a_push_never_overwrites_what_another_machine_pushed(tmp_path):
    a, b, store = _two_machines(tmp_path)
    (b / "scene.md").write_bytes(b"# SCENE")  # the same size: the hash tells
    assert _push("p1", b, store).written == ("scene.md",)
    # A did not change its copy: the store's newer one stands, and A is told.
    r = _push("p1", a, store)
    assert r.stale == ("scene.md",) and r.written == ()
    assert store["p1/scene.md"] == b"# SCENE"
    assert "stale (pull first)" in str(r)
    assert _push("p1", a, store).stale == ("scene.md",)  # still, until A pulls
    # A pulls: the same-size edit comes down by its sha, and A's base moves on.
    materialize_project("p1", settings=S3, store=store, cache=tmp_path / "cache")
    assert (a / "scene.md").read_bytes() == b"# SCENE"
    r = _push("p1", a, store)
    assert r.stale == () and r.written == ()


def test_a_file_both_sides_changed_is_a_conflict_until_forced(tmp_path):
    a, b, store = _two_machines(tmp_path)
    (b / "scene.md").write_bytes(b"# from B")
    _push("p1", b, store)
    (a / "scene.md").write_bytes(b"# from A")
    r = _push("p1", a, store)
    assert r.conflicts == ("scene.md",) and r.written == ()
    assert store["p1/scene.md"] == b"# from B"
    assert "in conflict" in str(r)
    r = _push("p1", a, store, force=True)
    assert r.written == ("scene.md",) and store["p1/scene.md"] == b"# from A"


def test_delete_missing_deletes_what_the_folder_no_longer_has(tmp_path):
    folder = _project(tmp_path)
    store = {
        "p1/old.txt": b"x",
        "p1/artifacts/shot_cache/blobs/x": b"blob",  # uploaded by hand; the folder has it
        "p1/artifacts/shot_cache/blobs/gone": b"g",  # ...and this one it does not
        "p2/keep.txt": b"k",
        "p1/": b"",
    }
    r = _push("p1", folder, store)
    assert r.deleted == () and "p1/old.txt" in store
    r = _push("p1", folder, store, delete_missing=True)
    assert r.deleted == ("artifacts/shot_cache/blobs/gone", "old.txt")
    assert set(store) == {
        "p1/scene.md",
        "p1/artifacts/audio/a.wav",
        "p1/artifacts/shot_cache/blobs/x",  # excluded from the push, kept by the folder
        RECORD,
        "p2/keep.txt",
        "p1/",
    }


def test_delete_missing_keeps_what_the_store_gained_since_the_base(tmp_path):
    a, b, store = _two_machines(tmp_path)
    (b / "new.txt").write_bytes(b"new")
    (b / "artifacts" / "audio" / "a.wav").write_bytes(b"wav2")
    _push("p1", b, store)
    (a / "artifacts" / "audio" / "a.wav").unlink()
    r = _push("p1", a, store, delete_missing=True)
    assert r.deleted == () and set(r.stale) == {"new.txt", "artifacts/audio/a.wav"}
    assert "p1/new.txt" in store and store["p1/artifacts/audio/a.wav"] == b"wav2"
    r = _push("p1", a, store, delete_missing=True, force=True)
    assert set(r.deleted) == {"new.txt", "artifacts/audio/a.wav"}


def test_exclude_is_a_seam_and_never_a_reason_to_delete(tmp_path):
    folder = _project(tmp_path)
    store: dict = {}
    r = _push("p1", folder, store, exclude=("scene.md",))
    assert r.excluded == ("scene.md",)
    assert "p1/artifacts/shot_cache/blobs/x" in store
    r = _push("p1", folder, store, delete_missing=True)
    assert r.deleted == () and "p1/artifacts/shot_cache/blobs/x" in store


def test_push_needs_a_folder(tmp_path):
    with pytest.raises(FileNotFoundError, match="no project folder"):
        push_project("p1", folder=tmp_path / "nope", settings=S3, store={})


def test_push_then_materialize_elsewhere_round_trips(tmp_path):
    folder = _project(tmp_path)
    store: dict = {}
    _push("p1", folder, store)
    out = materialize_project("p1", settings=S3, store=store, cache=tmp_path / "other")
    assert (out / "scene.md").read_bytes() == b"# scene"
    assert (out / "artifacts" / "audio" / "a.wav").read_bytes() == b"wav"
    assert not (out / "artifacts" / "shot_cache").exists()
    # The record travelled: a push from the other folder writes nothing.
    assert _push("p1", out, store).written == ()


def test_the_local_backend(tmp_path, monkeypatch):
    monkeypatch.setenv("CUTAN_HOME", str(tmp_path))
    own = tmp_path / "projects" / "p1"
    (own / "artifacts" / "shot_cache").mkdir(parents=True)
    (own / "scene.md").write_bytes(b"hi")
    (own / "artifacts" / "shot_cache" / "x").write_bytes(b"blob")
    # The project's own folder is the store's copy: a push, even a mirroring
    # one, touches nothing and writes no record.
    r = push_project("p1", delete_missing=True)
    assert r.folder == own and r.written == () and r.deleted == ()
    assert r.unchanged == ("scene.md",) and r.excluded == ("artifacts/shot_cache/x",)
    assert (own / "artifacts" / "shot_cache" / "x").is_file()
    assert not (own / STORE_RECORD).exists()
    # A folder elsewhere lands whole, folders made as needed.
    elsewhere = _project(tmp_path, "p2")
    r = push_project("p2", folder=elsewhere)
    assert r.written == ("artifacts/audio/a.wav", "scene.md")
    assert (
        tmp_path / "projects" / "p2" / "artifacts" / "audio" / "a.wav"
    ).read_bytes() == b"wav"
    assert not (tmp_path / "projects" / "p2" / "artifacts" / "shot_cache").exists()
    assert (
        read_record(tmp_path / "projects" / "p2")["files"]
        == read_record(elsewhere)["files"]
    )
    assert push_project("p2", folder=elsewhere).written == ()


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
