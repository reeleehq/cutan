"""Where a cutan project's files are read from: a disk folder or S3, by configuration.

The library's ``projects`` kind is a mapping ``relative path -> bytes`` (ADR-0024:
``s3://{bucket}/{tenant}/cutan/projects/{rel}`` mirrors ``~/.local/share/cutan/projects/{rel}``
exactly, so both backends hold the same keys). :func:`projects_store` returns that
mapping; :func:`materialize_project` returns a real folder for tools that need files
(ffmpeg, a browser), reading through a cache under ``~/.cache/cutan/projects/``.

Configuration (environment; the first match wins, ``CUTAN_HOME`` always forces local):

- ``CUTAN_HOME`` set: local, under that root (an explicit root beats any S3 setting)
- ``CUTAN_PROJECTS_BACKEND=s3``: S3, with ``CUTAN_S3_BUCKET`` (default ``tw-apps``),
  ``CUTAN_S3_PROFILE`` (default ``tw-server``) and ``CUTAN_S3_TENANT`` (default ``thorwhalen``)
- otherwise: local (the default)
"""

from __future__ import annotations

import os
from collections.abc import MutableMapping
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional

from . import LIBRARY_NAME

PROJECTS_KIND = "projects"
HOME_ENV = "CUTAN_HOME"
BACKEND_ENV = "CUTAN_PROJECTS_BACKEND"
CACHE_ENV = "CUTAN_CACHE"


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


def materialize_project(
    project_id: str,
    *,
    settings: Optional[ProjectsStoreSettings] = None,
    store: Optional[Mapping] = None,
    cache: Optional[Path] = None,
) -> Path:
    """A real folder holding ``project_id``'s files.

    Local backend: the project folder itself, no copy. S3: files are read through
    into the cache and kept; a cached file whose size matches the object's is reused.
    """
    s = settings or ProjectsStoreSettings.from_environ()
    if s.backend == "local" and store is None:
        return _local_root() / project_id
    store = projects_store(s) if store is None else store
    dest = (cache or cache_root()) / project_id
    prefix = f"{project_id}/"
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
    return dest
