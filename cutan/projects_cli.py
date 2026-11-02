"""``an projects ...`` — a store-backed project from the shell (cutan#91).

Thin string-typed wrappers over :mod:`cutan.projects_store`, dispatched by typer
the same way as ``an character ...`` (the ``cli.projects`` service):

    an projects push <id> [--folder DIR] [--delete-missing]
    an projects pull <id>
    an projects prune <id> [--dry-run]

Both read the backend from the environment (``CUTAN_PROJECTS_BACKEND=s3``,
``CUTAN_HOME`` forces local). On the local backend a push of the project's own
folder is a no-op, and a pull prints the folder.
"""

from __future__ import annotations

from pathlib import Path

from cutan.projects_store import (
    ProjectsStoreSettings,
    materialize_project,
    prune_project,
    push_project,
)

__all__ = ["push", "pull", "prune"]


def push(
    project_id: str, folder: str = "", delete_missing: bool = False, force: bool = False
) -> str:
    """Write what changed in a project folder to the projects store.

    project_id: the project's id (its folder name)
    folder: the folder to push (default: where `an projects pull` / `an init --id` put it)
    delete_missing: also delete the store's keys the folder no longer has (never what the folder keeps local: the shot cache, render work)
    force: also write files the store changed since this folder last synced (stale or in conflict), and delete keys it gained
    """
    report = push_project(
        project_id,
        folder=Path(folder) if folder else None,
        delete_missing=delete_missing,
        force=force,
    )
    lines = [str(report)]
    lines += [f"  + {rel}" for rel in report.written]
    lines += [f"  - {rel}" for rel in report.deleted]
    lines += [f"  ! stale (pull first): {rel}" for rel in report.stale]
    lines += [f"  ! conflict (--force overwrites): {rel}" for rel in report.conflicts]
    return "\n".join(lines)


def pull(project_id: str) -> str:
    """Read a project from the projects store into a real folder, and print the folder.

    project_id: the project's id (its folder name)
    """
    return str(materialize_project(project_id))


def prune(project_id: str, dry_run: bool = False) -> str:
    """Delete the store's copies of what an keeps out of git (render reports, probes, the options manifests' file locks: pushed before the excludes covered them), so no pull brings them back.

    project_id: the project's id (its folder name)
    dry_run: only list what would be deleted
    """
    if ProjectsStoreSettings.from_environ().backend == "local":
        return "local backend: the store is the project folder itself; nothing to prune"
    gone = prune_project(project_id, dry_run=dry_run)
    if not gone:
        return "nothing to prune"
    head = "would delete" if dry_run else "deleted"
    return "\n".join([f"{head} {len(gone)} file(s):", *(f"  - {rel}" for rel in gone)])


_dispatch_funcs = [push, pull, prune]
