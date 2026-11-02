# cutan.projects_cli

`an projects ...` — a store-backed project from the shell (cutan#91).

Thin string-typed wrappers over [`cutan.projects_store`](cutan.projects_store.html.md#module-cutan.projects_store), dispatched by typer
the same way as `an character ...` (the `cli.projects` service):

> an projects push <id> [–folder DIR] [–delete-missing]
> an projects pull <id>
> an projects prune <id> [–dry-run]

Both read the backend from the environment (`CUTAN_PROJECTS_BACKEND=s3`,
`CUTAN_HOME` forces local). On the local backend a push of the project’s own
folder is a no-op, and a pull prints the folder.

### Functions

| [`push`](#cutan.projects_cli.push)(project_id[, folder, delete_missing, force])   | Write what changed in a project folder to the projects store.                                                                                                                            |
|------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`pull`](#cutan.projects_cli.pull)(project_id)                                    | Read a project from the projects store into a real folder, and print the folder.                                                                                                         |
| [`prune`](#cutan.projects_cli.prune)(project_id[, dry_run])                        | Delete the store's copies of what an keeps out of git (render reports, probes, the options manifests' file locks: pushed before the excludes covered them), so no pull brings them back. |

### cutan.projects_cli.prune(project_id, dry_run=False)

Delete the store’s copies of what an keeps out of git (render reports, probes, the options manifests’ file locks: pushed before the excludes covered them), so no pull brings them back.

project_id: the project’s id (its folder name)
dry_run: only list what would be deleted

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### cutan.projects_cli.pull(project_id)

Read a project from the projects store into a real folder, and print the folder.

project_id: the project’s id (its folder name)

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### cutan.projects_cli.push(project_id, folder='', delete_missing=False, force=False)

Write what changed in a project folder to the projects store.

project_id: the project’s id (its folder name)
folder: the folder to push (default: where `an projects pull` / `an init --id` put it)
delete_missing: also delete the store’s keys the folder no longer has (never what the folder keeps local: the shot cache, render work)
force: also write files the store changed since this folder last synced (stale or in conflict), and delete keys it gained

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)
