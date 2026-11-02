"""``an pack ...`` — a production pack into a project (cutan#87).

Thin string-typed wrapper over :func:`cutan.pack.import_pack`, dispatched by typer
the same way as ``an character ...`` (the ``cli.pack`` service):

    an pack import PACK [--project DIR] [--dry-run] [--json]

``--dry-run`` checks the pack on a scratch project and deletes it (what the
``cutan-production-pack`` skill's ``validate_pack.py`` runs); without it the
project is made at ``DIR`` (default: ``<pack name>-project``, here) and kept.
"""

from __future__ import annotations

__all__ = ["import_"]


def import_(pack: str, project: str = "", dry_run: bool = False, json: bool = False) -> str:
    """Turn a production pack into a project: init it, copy the pack in, make the cast, lay redrawn parts over the factory's, and validate everything.

    pack: the production pack folder (scene.md, cast.yaml or cast.sh, assets/, PRODUCTION.md)
    project: the new project's folder (default: <pack name>-project, in the current folder); it must not exist
    dry_run: only check: build a scratch project and delete it
    json: print the report as JSON
    """
    import json as _json

    from an.cli_status import failed

    from cutan.pack import import_pack

    report = import_pack(pack, project or None, dry_run=dry_run)
    text = _json.dumps(report.to_dict(), indent=2) if json else report.format()
    if report.project is not None and not json:
        text += f"\n\nproject: {report.project}"
    return text if report.ok else failed(text)


import_.__name__ = "import"  # the command is `an pack import` (`import` is a keyword)

_dispatch_funcs = [import_]
