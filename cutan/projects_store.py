"""Where a cutan project's files are read from and written to: a disk folder or S3, by configuration.

The library's ``projects`` kind is a mapping ``relative path -> bytes`` (ADR-0024:
``s3://{bucket}/{tenant}/cutan/projects/{rel}`` mirrors ``~/.local/share/cutan/projects/{rel}``
exactly, so both backends hold the same keys). :func:`projects_store` returns that
mapping; :func:`materialize_project` returns a real folder for tools that need files
(ffmpeg, a browser), reading through a cache under ``~/.cache/cutan/projects/``;
:func:`push_project` is the write half (cutan#91): it writes what changed since the
folder last synced, never over a newer version another machine pushed, can delete
what the folder no longer has, and keeps derived output local.

A folder that belongs to a store carries the record ``.an/projects_store.json``
(:data:`STORE_RECORD`): the store's coordinates and, per file, the size and sha256
the folder last synced (``files``). The record is pushed with the project, so the
store's copy says what the store holds and the folder's copy is the base a push
compares both sides against (a three-way comparison: a file the folder did not
change is never pushed over one the store changed, and a file both changed is a
conflict that only ``force`` writes). ``an init <id> --id --genre cutout_animation``
creates a project in the cache folder with that record when the backend is S3
(:func:`new_project_dir`, the ``projects.dir.cutan`` service of ``an`` API level 7).

Configuration (environment; the first match wins, ``CUTAN_HOME`` always forces local):

- ``CUTAN_HOME`` set: local, under that root (an explicit root beats any S3 setting)
- ``CUTAN_PROJECTS_BACKEND=s3``: S3, with ``CUTAN_S3_BUCKET`` (default ``tw-apps``),
  ``CUTAN_S3_PROFILE`` (default ``tw-server``) and ``CUTAN_S3_TENANT`` (default ``thorwhalen``)
- otherwise: local (the default)
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import MutableMapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping, Optional

from . import LIBRARY_NAME, PROJECT_STORE_RECORD

PROJECTS_KIND = "projects"
HOME_ENV = "CUTAN_HOME"
BACKEND_ENV = "CUTAN_PROJECTS_BACKEND"
CACHE_ENV = "CUTAN_CACHE"

#: The record's path inside a project folder (:data:`cutan.PROJECT_STORE_RECORD`).
STORE_RECORD: str = PROJECT_STORE_RECORD

#: What a push keeps on the machine that made it: derived or transient output,
#: keyed by that machine or re-made from the project. The shot cache (an#242) and
#: the shot archive re-render from the project; the render work dirs are a run's
#: scratch; render reports and probes are what ``an init`` keeps out of git
#: (``an.project.PROJECT_GITIGNORE``, held equal by a test); a repository is
#: not project content. Each entry is a folder prefix (ending in ``/``) or a file.
DEFAULT_PUSH_EXCLUDES: tuple[str, ...] = (
    ".git/",
    ".an/render_work/",
    "artifacts/shot_cache/",
    "artifacts/shots/",
    "artifacts/render_reports/",
    "artifacts/probes/",
)

#: A project id is one folder name (the rule of ``an.library.root.project_dir``).
_PROJECT_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


@dataclass(frozen=True)
class ProjectsStoreSettings:
    """Which backend holds the projects, and its S3 coordinates."""

    backend: str = "local"
    bucket: str = "tw-apps"
    profile: Optional[str] = "tw-server"
    tenant: str = "thorwhalen"

    @property
    def prefix(self) -> str:
        return f"{self.tenant}/{LIBRARY_NAME}/{PROJECTS_KIND}/"

    def coordinates(self) -> dict:
        """What a project folder records about its store (no credentials, no profile).

        >>> ProjectsStoreSettings().coordinates()["backend"]
        'local'
        """
        if self.backend == "local":
            return {"backend": "local"}
        return {
            "backend": self.backend,
            "bucket": self.bucket,
            "tenant": self.tenant,
            "prefix": self.prefix,
        }

    @classmethod
    def from_environ(cls, environ: Optional[Mapping[str, str]] = None):
        """
        >>> ProjectsStoreSettings.from_environ({}).backend
        'local'
        >>> ProjectsStoreSettings.from_environ({"CUTAN_PROJECTS_BACKEND": "s3"}).backend
        's3'
        >>> env = {"CUTAN_PROJECTS_BACKEND": "s3", "CUTAN_HOME": "/x"}
        >>> ProjectsStoreSettings.from_environ(env).backend
        'local'
        """
        env = os.environ if environ is None else environ
        backend = "local" if env.get(HOME_ENV) else env.get(BACKEND_ENV, "local")
        if backend not in ("local", "s3"):
            raise ValueError(f"{BACKEND_ENV} must be 'local' or 's3', got {backend!r}")
        d = cls()
        return cls(
            backend=backend,
            bucket=env.get("CUTAN_S3_BUCKET", d.bucket),
            profile=env.get("CUTAN_S3_PROFILE", d.profile),
            tenant=env.get("CUTAN_S3_TENANT", d.tenant),
        )


def _local_root() -> Path:
    from an.library.root import library_root

    return library_root(package=LIBRARY_NAME) / PROJECTS_KIND


def projects_store(settings: Optional[ProjectsStoreSettings] = None) -> MutableMapping:
    """The projects as ``{relative path: bytes}``, over disk or S3 per ``settings``.

    The local store creates a key's folders on write, so a project pushed into it
    from a folder elsewhere lands whole.
    """
    s = settings or ProjectsStoreSettings.from_environ()
    if s.backend == "s3":
        from s3dol import s3_store

        return s3_store(s.bucket, prefix=s.prefix, profile=s.profile)
    from dol import Files, mk_dirs_if_missing

    root = _local_root()
    root.mkdir(parents=True, exist_ok=True)
    return mk_dirs_if_missing(Files(str(root)))


def cache_root() -> Path:
    return (
        Path(os.environ.get(CACHE_ENV) or Path.home() / ".cache" / LIBRARY_NAME)
        / PROJECTS_KIND
    )


def _project_prefix(project_id: str) -> str:
    """``"<id>/"``, refusing an id that is not one folder name.

    >>> _project_prefix("alice-and-bob")
    'alice-and-bob/'
    >>> _project_prefix("../escape")  # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    ValueError: ...
    """
    if not _PROJECT_ID.fullmatch(project_id or ""):
        raise ValueError(
            f"project id {project_id!r} must be one folder name "
            "(letters, digits, '.', '_' or '-'; no path separators)"
        )
    return f"{project_id}/"


def _folder_for(
    project_id: str,
    s: ProjectsStoreSettings,
    store: Optional[Mapping],
    cache: Optional[Path],
) -> Path:
    """The local backend's project folder itself, else the cache folder."""
    if s.backend == "local" and store is None:
        return _local_root() / project_id
    return (cache or cache_root()) / project_id


def _keys_under(store: Mapping, prefix: str) -> set[str]:
    """The store's keys under ``prefix``, less directory markers (a key ending in
    ``/``, which a console's "create folder" leaves and ``s3dol`` lists)."""
    return {k for k in store if k.startswith(prefix) and not k.endswith("/")}


# ----------------------------------------------------------------- the record


def read_record(folder: Path) -> dict:
    """The folder's :data:`STORE_RECORD`, ``{}`` when it has none or it is unreadable."""
    path = Path(folder) / STORE_RECORD
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return doc if isinstance(doc, dict) else {}


def _record_bytes(record: dict) -> bytes:
    return (json.dumps(record, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _write_record(folder: Path, record: dict) -> bytes:
    path = Path(folder) / STORE_RECORD
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _record_bytes(record)
    path.write_bytes(data)
    return data


def _record_store(folder: Path, s: ProjectsStoreSettings) -> None:
    """Say which store ``folder`` belongs to, keeping what else the record holds."""
    record = read_record(folder)
    if record.get("store") == s.coordinates():
        return
    _write_record(folder, {**record, "store": s.coordinates()})


def _store_record(store: Mapping, key: str) -> dict:
    """The store's copy of the record, ``{}`` when it has none or it is unreadable."""
    try:
        data = store[key]
    except (KeyError, OSError):
        return {}
    try:
        doc = json.loads(bytes(data).decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return {}
    return doc if isinstance(doc, dict) else {}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ----------------------------------------------------------------- read half


def materialize_project(
    project_id: str,
    *,
    settings: Optional[ProjectsStoreSettings] = None,
    store: Optional[Mapping] = None,
    cache: Optional[Path] = None,
) -> Path:
    """A real folder holding ``project_id``'s files.

    Local backend: the project folder itself, no copy. S3: files are read through
    into the cache and kept, and the folder records the store it belongs to
    (:data:`STORE_RECORD`). A cached file is reused when its sha256 is the one
    the store's record holds for it (a file the record does not know: when its
    size matches the object's). The store wins: a cached file that differs is
    overwritten, so push a folder's changes before pulling into it.
    """
    s = settings or ProjectsStoreSettings.from_environ()
    prefix = _project_prefix(project_id)
    dest = _folder_for(project_id, s, store, cache)
    if s.backend == "local" and store is None:
        return dest
    store = projects_store(s) if store is None else store
    remote = _store_record(store, prefix + STORE_RECORD).get("files") or {}
    for key in sorted(_keys_under(store, prefix)):
        rel = key[len(prefix) :]
        target = dest / rel
        if target.is_file() and rel != STORE_RECORD:  # the record is always refreshed
            want = (remote.get(rel) or {}).get("sha256")
            if want is not None:
                if _file_digest(target) == want:
                    continue
                data = store[key]
            else:
                data = store[key]
                if target.stat().st_size == len(data):
                    continue
        else:
            data = store[key]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    dest.mkdir(parents=True, exist_ok=True)
    _record_store(dest, s)
    return dest


def new_project_dir(
    project_id: str,
    *,
    default: Optional[Path] = None,
    settings: Optional[ProjectsStoreSettings] = None,
    store: Optional[Mapping] = None,
    cache: Optional[Path] = None,
) -> Path:
    """Where ``an init <id> --id --genre cutout_animation`` creates the project.

    The ``projects.dir.cutan`` service (``an`` API level 7): the core computes
    its own default (``<root>/projects/<id>``) and hands it over as ``default``.
    Local backend: that default. S3: the cache folder, with what the store
    already holds under the id read through first (so ``an init`` sees an
    existing project's ``scene.md`` and refuses to clobber it) and the record
    that the folder belongs to the store, which a later :func:`push_project`
    reads. Nothing is uploaded: the push is explicit.
    """
    s = settings or ProjectsStoreSettings.from_environ()
    if s.backend == "local" and store is None:
        _project_prefix(project_id)
        return Path(default) if default is not None else _local_root() / project_id
    return materialize_project(project_id, settings=s, store=store, cache=cache)


# ----------------------------------------------------------------- write half


@dataclass(frozen=True)
class PushReport:
    """What one :func:`push_project` did, as relative paths.

    ``stale``: files the folder did not change but the store did (or dropped)
    since the folder last synced, so they were not pushed: pull first.
    ``conflicts``: files both sides changed, not pushed without ``force``.
    """

    project_id: str
    folder: Path
    written: tuple[str, ...]
    unchanged: tuple[str, ...]
    excluded: tuple[str, ...]
    deleted: tuple[str, ...]
    stale: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()

    def __str__(self) -> str:
        text = (
            f"{self.project_id}: {len(self.written)} written, "
            f"{len(self.unchanged)} unchanged, {len(self.excluded)} kept local, "
            f"{len(self.deleted)} deleted"
        )
        if self.stale:
            text += f", {len(self.stale)} stale (pull first)"
        if self.conflicts:
            text += f", {len(self.conflicts)} in conflict (force to overwrite)"
        return text


def _excluder(exclude: Iterable[str]):
    """``rel -> bool``: whether an entry (a folder prefix ending in ``/``, or a file) covers it.

    >>> keep = _excluder(("artifacts/shot_cache/", "notes.txt"))
    >>> keep("artifacts/shot_cache/blobs/x"), keep("notes.txt"), keep("artifacts/audio/a.wav")
    (True, True, False)
    """
    folders = tuple(e for e in exclude if e.endswith("/"))
    files = frozenset(e for e in exclude if not e.endswith("/"))

    def excluded(rel: str) -> bool:
        return rel in files or any(rel.startswith(f) for f in folders)

    return excluded


def _same(a: Optional[dict], b: Optional[dict]) -> bool:
    """Two record entries name the same bytes (by sha256)."""
    return a is not None and b is not None and a.get("sha256") == b.get("sha256")


def push_project(
    project_id: str,
    *,
    folder: Optional[Path] = None,
    settings: Optional[ProjectsStoreSettings] = None,
    store: Optional[MutableMapping] = None,
    delete_missing: bool = False,
    exclude: Iterable[str] = DEFAULT_PUSH_EXCLUDES,
    force: bool = False,
    cache: Optional[Path] = None,
) -> PushReport:
    """Write ``folder``'s files to the store under ``project_id/``: the inverse of
    :func:`materialize_project` (cutan#91).

    ``folder`` defaults to where :func:`materialize_project` puts the project: the
    cache folder on S3, the project folder itself locally (which is the store's
    own copy, so that push does nothing). Each file is compared three ways: with
    the store's record of it (the store's copy of :data:`STORE_RECORD`) and with
    the folder's record (the base: what the folder last pulled or pushed; with
    no base, the store's record stands in, so a first push from a folder with no
    history writes its differences). A file equal to the store's is unchanged;
    one the folder changed and the store did not is written; one the folder did
    not change but the store did is ``stale`` and left alone; one both changed
    is a ``conflict``, written only with ``force``. A file the records do not
    know is compared with the store's bytes when the key exists. ``exclude``
    names what stays local (:data:`DEFAULT_PUSH_EXCLUDES`); ``delete_missing``
    deletes the store's keys the folder no longer has (a key the store gained or
    changed since the base is kept, unless ``force``); excluded files the folder
    still has are never deleted. The record is then written to the folder and,
    when anything changed, to the store.
    """
    s = settings or ProjectsStoreSettings.from_environ()
    prefix = _project_prefix(project_id)
    own_folder = s.backend == "local" and store is None
    store = projects_store(s) if store is None else store
    folder = (
        Path(folder) if folder is not None else _folder_for(project_id, s, None, cache)
    )
    if not folder.is_dir():
        raise FileNotFoundError(f"no project folder to push at {folder}")
    excluded = _excluder(exclude)
    local_files = sorted(p for p in folder.rglob("*") if p.is_file())
    rels = [p.relative_to(folder).as_posix() for p in local_files]
    if own_folder and folder.resolve() == (_local_root() / project_id).resolve():
        # The folder IS the store's copy of the project: nothing to push, and
        # nothing to delete (its derived output is not "missing" from itself).
        kept = tuple(r for r in rels if excluded(r))
        same = tuple(r for r in rels if r != STORE_RECORD and not excluded(r))
        return PushReport(project_id, folder, (), same, kept, ())

    record_key = prefix + STORE_RECORD
    existing = _keys_under(store, prefix)
    local_record = read_record(folder)
    remote_doc = _store_record(store, record_key)
    remote: dict = remote_doc.get("files") or {}
    base: dict = local_record.get("files") or remote
    has_base = bool(local_record.get("files"))

    written: list[str] = []
    unchanged: list[str] = []
    kept: list[str] = []
    stale: list[str] = []
    conflicts: list[str] = []
    synced: dict[str, dict] = {}  # what this folder now agrees with the store on
    for path, rel in zip(local_files, rels):
        if rel == STORE_RECORD:
            continue
        if excluded(rel):
            kept.append(rel)
            continue
        key = prefix + rel
        size = path.stat().st_size
        local = {"size": size, "sha256": _file_digest(path)}
        r, b = remote.get(rel), base.get(rel)
        if _same(r, local) and (key in existing or key in store):
            synced[rel] = local
            unchanged.append(rel)
            continue
        if r is None and b is None and key in existing:
            # Uploaded by hand (no record knows it): compare the bytes.
            current = store[key]
            if len(current) == size and _sha256(current) == local["sha256"]:
                synced[rel] = local
                unchanged.append(rel)
                continue
        if b is not None and _same(b, local) and not _same(r, b) and not force:
            stale.append(rel)  # the store moved past this folder's copy
            continue
        both_changed = has_base and not _same(b, local) and not _same(r, b)
        if both_changed and r is not None and not force:
            conflicts.append(rel)
            continue
        store[key] = path.read_bytes()
        synced[rel] = local
        written.append(rel)

    deleted: list[str] = []
    if delete_missing:
        here = set(rels)
        for key in sorted(existing):
            rel = key[len(prefix) :]
            if rel == STORE_RECORD or rel in here:
                continue
            r, b = remote.get(rel), base.get(rel)
            if has_base and r is not None and not _same(r, b) and not force:
                stale.append(rel)  # the store gained or changed it since the base
                continue
            del store[key]
            deleted.append(rel)

    # Two records: the store's says what the store holds; the folder's says what
    # the folder synced (its base), which differs by exactly the stale and
    # conflicting files, left at the base entry the folder still agrees with.
    store_files = {rel: e for rel, e in remote.items() if rel not in deleted}
    store_files.update(synced)
    base_files = {rel: e for rel, e in base.items() if rel not in deleted}
    base_files.update(synced)
    changed = bool(written or deleted) or not remote_doc or store_files != remote
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if changed:
        store[record_key] = _record_bytes(
            {
                **remote_doc,
                "store": s.coordinates(),
                "files": store_files,
                "pushed_at": now,
            }
        )
    local_doc = {**local_record, "store": s.coordinates(), "files": base_files}
    if changed:
        local_doc["pushed_at"] = now
    if local_doc != local_record:
        _write_record(folder, local_doc)
    return PushReport(
        project_id=project_id,
        folder=folder,
        written=tuple(written),
        unchanged=tuple(unchanged),
        excluded=tuple(kept),
        deleted=tuple(deleted),
        stale=tuple(stale),
        conflicts=tuple(conflicts),
    )
