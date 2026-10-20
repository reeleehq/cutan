"""Where a cutan project's files are read from and written to: a disk folder or S3, by configuration.

The library's ``projects`` kind is a mapping ``relative path -> bytes`` (ADR-0024:
``s3://{bucket}/{tenant}/cutan/projects/{rel}`` mirrors ``~/.local/share/cutan/projects/{rel}``
exactly, so both backends hold the same keys). :func:`projects_store` returns that
mapping; :func:`materialize_project` returns a real folder for tools that need files
(ffmpeg, a browser), reading through a cache under ``~/.cache/cutan/projects/``;
:func:`push_project` is the write half (cutan#91): it uploads what changed since the
last push, can mirror deletions, and keeps the derived shot cache local.

A folder that belongs to a store carries the record ``.an/projects_store.json``
(:data:`STORE_RECORD`): the store's coordinates and, after a push, each pushed
file's size and sha256. ``an init <id> --id --genre cutout_animation`` creates a
project in the cache folder with that record when the backend is S3
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

from . import LIBRARY_NAME

PROJECTS_KIND = "projects"
HOME_ENV = "CUTAN_HOME"
BACKEND_ENV = "CUTAN_PROJECTS_BACKEND"
CACHE_ENV = "CUTAN_CACHE"

#: The file, relative to a project folder, that says which store the folder
#: belongs to and what was last pushed there (``{"store": …, "files": {rel:
#: {"size", "sha256"}}, "pushed_at"}``). Pushed with the project, so a folder
#: materialised elsewhere knows it too.
STORE_RECORD: str = ".an/projects_store.json"

#: What a push keeps on the machine that made it: derived or transient, keyed
#: by that machine. The shot cache (an#242) re-renders from the project; the
#: render work dirs are a run's scratch. Each entry is a folder prefix or a file.
DEFAULT_PUSH_EXCLUDES: tuple[str, ...] = ("artifacts/shot_cache/", ".an/render_work/")

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
    """The projects as ``{relative path: bytes}``, over disk or S3 per ``settings``."""
    s = settings or ProjectsStoreSettings.from_environ()
    if s.backend == "s3":
        from s3dol import s3_store

        return s3_store(s.bucket, prefix=s.prefix, profile=s.profile)
    from dol import Files

    root = _local_root()
    root.mkdir(parents=True, exist_ok=True)
    return Files(str(root))


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


# ----------------------------------------------------------------- the record


def read_record(folder: Path) -> dict:
    """The folder's :data:`STORE_RECORD`, ``{}`` when it has none or it is unreadable."""
    path = Path(folder) / STORE_RECORD
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return doc if isinstance(doc, dict) else {}


def _write_record(folder: Path, record: dict) -> bytes:
    path = Path(folder) / STORE_RECORD
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(record, indent=2, sort_keys=True) + "\n").encode("utf-8")
    path.write_bytes(data)
    return data


def _record_store(folder: Path, s: ProjectsStoreSettings) -> None:
    """Say which store ``folder`` belongs to, keeping what else the record holds."""
    record = read_record(folder)
    if record.get("store") == s.coordinates():
        return
    _write_record(folder, {**record, "store": s.coordinates()})


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
    into the cache and kept; a cached file whose size matches the object's is reused,
    and the folder records the store it belongs to (:data:`STORE_RECORD`).
    """
    s = settings or ProjectsStoreSettings.from_environ()
    prefix = _project_prefix(project_id)
    dest = _folder_for(project_id, s, store, cache)
    if s.backend == "local" and store is None:
        return dest
    store = projects_store(s) if store is None else store
    for key in store:
        if not key.startswith(prefix):
            continue
        target = dest / key[len(prefix) :]
        data = store[key]
        if target.is_file() and target.stat().st_size == len(data):
            continue
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
    reads.
    """
    s = settings or ProjectsStoreSettings.from_environ()
    if s.backend == "local" and store is None:
        _project_prefix(project_id)
        return Path(default) if default is not None else _local_root() / project_id
    return materialize_project(project_id, settings=s, store=store, cache=cache)


# ----------------------------------------------------------------- write half


@dataclass(frozen=True)
class PushReport:
    """What one :func:`push_project` did."""

    project_id: str
    folder: Path
    written: tuple[str, ...]
    unchanged: tuple[str, ...]
    excluded: tuple[str, ...]
    deleted: tuple[str, ...]

    def __str__(self) -> str:
        return (
            f"{self.project_id}: {len(self.written)} written, "
            f"{len(self.unchanged)} unchanged, {len(self.excluded)} kept local, "
            f"{len(self.deleted)} deleted"
        )


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


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _manifest_of(store: Mapping, key: str, folder: Path) -> dict:
    """The last push's ``{rel: {size, sha256}}``: the store's record, else the folder's."""
    try:
        data = store[key]
    except KeyError:
        data = None
    if data is not None:
        try:
            doc = json.loads(bytes(data).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            doc = {}
        if isinstance(doc, dict):
            return doc.get("files") or {}
    return read_record(folder).get("files") or {}


def push_project(
    project_id: str,
    *,
    folder: Optional[Path] = None,
    settings: Optional[ProjectsStoreSettings] = None,
    store: Optional[MutableMapping] = None,
    delete_missing: bool = False,
    exclude: Iterable[str] = DEFAULT_PUSH_EXCLUDES,
    cache: Optional[Path] = None,
) -> PushReport:
    """Write ``folder``'s files to the store under ``project_id/``: the inverse of
    :func:`materialize_project` (cutan#91).

    ``folder`` defaults to where :func:`materialize_project` puts the project (the
    cache folder on S3; the project folder itself locally, where a push is a no-op).
    Only changed files are written: a file whose size and sha256 match the last
    push's record (the store's copy of :data:`STORE_RECORD`, else the folder's) is
    skipped without a read; a file the record does not know is compared with the
    store's bytes when the key exists. ``exclude`` names what stays local
    (:data:`DEFAULT_PUSH_EXCLUDES`). ``delete_missing`` makes the store's
    ``project_id/`` prefix mirror what was pushed: keys the folder no longer has,
    and keys the exclude rule keeps local, are deleted. The record is then
    written to the folder and to the store.
    """
    s = settings or ProjectsStoreSettings.from_environ()
    prefix = _project_prefix(project_id)
    store = projects_store(s) if store is None else store
    folder = (
        Path(folder) if folder is not None else _folder_for(project_id, s, None, cache)
    )
    if not folder.is_dir():
        raise FileNotFoundError(f"no project folder to push at {folder}")
    excluded = _excluder(exclude)
    record_key = prefix + STORE_RECORD
    existing = {key for key in store if key.startswith(prefix)}
    known = _manifest_of(store, record_key, folder)

    written: list[str] = []
    unchanged: list[str] = []
    kept: list[str] = []
    files: dict[str, dict] = {}
    for path in sorted(p for p in folder.rglob("*") if p.is_file()):
        rel = path.relative_to(folder).as_posix()
        if rel == STORE_RECORD:
            continue
        if excluded(rel):
            kept.append(rel)
            continue
        size = path.stat().st_size
        entry = known.get(rel) or {}
        key = prefix + rel
        digest = None
        if entry.get("size") == size:
            digest = _file_digest(path)
            if entry.get("sha256") == digest:
                files[rel] = {"size": size, "sha256": digest}
                unchanged.append(rel)
                continue
        data = path.read_bytes()
        digest = digest or _sha256(data)
        files[rel] = {"size": size, "sha256": digest}
        if not entry and key in existing:
            current = store[key]
            if len(current) == size and _sha256(current) == digest:
                unchanged.append(rel)
                continue
        store[key] = data
        written.append(rel)

    deleted: list[str] = []
    if delete_missing:
        wanted = {prefix + rel for rel in files} | {record_key}
        for key in sorted(existing - wanted):
            del store[key]
            deleted.append(key[len(prefix) :])

    record = {
        **read_record(folder),
        "store": s.coordinates(),
        "files": files,
        "pushed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    data = _write_record(folder, record)
    if written or deleted or record_key not in existing or files != known:
        store[record_key] = data
    return PushReport(
        project_id=project_id,
        folder=folder,
        written=tuple(written),
        unchanged=tuple(unchanged),
        excluded=tuple(kept),
        deleted=tuple(deleted),
    )
