# cutan.pack_cli

`an pack ...` — a production pack into a project (cutan#87).

Thin string-typed wrapper over [`cutan.pack.import_pack()`](cutan.pack.html.md#cutan.pack.import_pack), dispatched by typer
the same way as `an character ...` (the `cli.pack` service):

> an pack import PACK [–project DIR] [–dry-run] [–json]

`--dry-run` checks the pack on a scratch project and deletes it (what the
`cutan-production-pack` skill’s `validate_pack.py` runs); without it the
project is made at `DIR` (default: `<pack name>-project`, here) and kept.

### Functions

| [`import_`](#cutan.pack_cli.import_)(pack[, project, dry_run, json])   | Turn a production pack into a project: init it, copy the pack in, make the cast, lay redrawn parts over the factory's, and validate everything.   |
|--------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------|

### cutan.pack_cli.import_(pack, project='', dry_run=False, json=False)

Turn a production pack into a project: init it, copy the pack in, make the cast, lay redrawn parts over the factory’s, and validate everything.

pack: the production pack folder (scene.md, cast.yaml or cast.sh, assets/, PRODUCTION.md)
project: the new project’s folder (default: <pack name>-project, in the current folder); it must not exist
dry_run: only check: build a scratch project and delete it
json: print the report as JSON

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)
