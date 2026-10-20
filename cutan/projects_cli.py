"""``an projects ...`` — a store-backed project from the shell (cutan#91).

Thin string-typed wrappers over :mod:`cutan.projects_store`, dispatched by typer
the same way as ``an character ...`` (the ``cli.projects`` service):

    an projects push <id> [--folder DIR] [--delete-missing]
    an projects pull <id>

Both read the backend from the environment (``CUTAN_PROJECTS_BACKEND=s3``,
``CUTAN_HOME`` forces local). On the local backend a push of the project's own
folder is a no-op, and a pull prints the folder.
"""

from __future__ import annotations

from pathlib import Path

from cutan.projects_store import materialize_project, push_project

__all__ = ["push", "pull"]


def push(project_id: str, folder: str = "", delete_missing: bool = False) -> str:
    """Write what changed in a project folder to the projects store.

    project_id: the project's id (its folder name)
    folder: the folder to push (default: where `an projects pull` / `an init --id` put it)
    delete_missing: also delete the store's keys the folder no longer has (and what stays local: the shot cache, render work), so the store mirrors the folder
    """
    report = push_project(
        project_id,
        folder=Path(folder) if folder else None,
        delete_missing=delete_missing,
    )
    lines = [str(report)]
    lines += [f"  + {rel}" for rel in report.written]
    lines += [f"  - {rel}" for rel in report.deleted]
    return "\n".join(lines)


def pull(project_id: str) -> str:
    """Read a project from the projects store into a real folder, and print the folder.

    project_id: the project's id (its folder name)
    """
    return str(materialize_project(project_id))


_dispatch_funcs = [push, pull]
