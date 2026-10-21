# cutan.projects_store

Where a cutan project’s files are read from and written to: a disk folder or S3, by configuration.

The library’s `projects` kind is a mapping `relative path -> bytes` (ADR-0024:
`s3://{bucket}/{tenant}/cutan/projects/{rel}` mirrors `~/.local/share/cutan/projects/{rel}`
exactly, so both backends hold the same keys). [`projects_store()`](#cutan.projects_store.projects_store) returns that
mapping; [`materialize_project()`](#cutan.projects_store.materialize_project) returns a real folder for tools that need files
(ffmpeg, a browser), reading through a cache under `~/.cache/cutan/projects/`;
[`push_project()`](#cutan.projects_store.push_project) is the write half (cutan#91): it writes what changed since the
folder last synced, never over a newer version another machine pushed, can delete
what the folder no longer has, and keeps derived output local.

A folder that belongs to a store carries the record `.an/projects_store.json`
([`STORE_RECORD`](#cutan.projects_store.STORE_RECORD)): the store’s coordinates and, per file, the size and sha256
the folder last synced (`files`). The record is pushed with the project, so the
store’s copy says what the store holds and the folder’s copy is the base a push
compares both sides against (a three-way comparison: a file the folder did not
change is never pushed over one the store changed, and a file both changed is a
conflict that only `force` writes). `an init <id> --id --genre cutout_animation`
creates a project in the cache folder with that record when the backend is S3
([`new_project_dir()`](#cutan.projects_store.new_project_dir), the `projects.dir.cutan` service of `an` API level 7).

Configuration (environment; the first match wins, `CUTAN_HOME` always forces local):

- `CUTAN_HOME` set: local, under that root (an explicit root beats any S3 setting)
- `CUTAN_PROJECTS_BACKEND=s3`: S3, with `CUTAN_S3_BUCKET` (default `tw-apps`),
  `CUTAN_S3_PROFILE` (default `tw-server`) and `CUTAN_S3_TENANT` (default `thorwhalen`)
- otherwise: local (the default)

### Module Attributes

| [`STORE_RECORD`](#cutan.projects_store.STORE_RECORD)          | The record's path inside a project folder ([`cutan.PROJECT_STORE_RECORD`](cutan.html.md#cutan.PROJECT_STORE_RECORD)).   |
|------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`DEFAULT_PUSH_EXCLUDES`](#cutan.projects_store.DEFAULT_PUSH_EXCLUDES) | derived or transient output, keyed by that machine or re-made from the project.                                                                       |

### Functions

| `cache_root`()                                                                                   |                                                                                                                                                            |
|--------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`materialize_project`](#cutan.projects_store.materialize_project)(project_id, \*[, ...])      | A real folder holding `project_id`'s files.                                                                                                                |
| [`new_project_dir`](#cutan.projects_store.new_project_dir)(project_id, \*[, default, ...]) | Where `an init <id> --id --genre cutout_animation` creates the project.                                                                                    |
| [`projects_store`](#cutan.projects_store.projects_store)([settings])                      | The projects as `{relative path: bytes}`, over disk or S3 per `settings`.                                                                                  |
| [`push_project`](#cutan.projects_store.push_project)(project_id, \*[, folder, ...])     | Write `folder`'s files to the store under `project_id/`: the inverse of [`materialize_project()`](#cutan.projects_store.materialize_project) (cutan#91). |
| [`read_record`](#cutan.projects_store.read_record)(folder)                             | The folder's [`STORE_RECORD`](#cutan.projects_store.STORE_RECORD), `{}` when it has none or it is unreadable.                                     |

### Classes

| [`ProjectsStoreSettings`](#cutan.projects_store.ProjectsStoreSettings)([backend, bucket, ...])   | Which backend holds the projects, and its S3 coordinates.                                        |
|--------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------|
| [`PushReport`](#cutan.projects_store.PushReport)(project_id, folder, written, ...)    | What one [`push_project()`](#cutan.projects_store.push_project) did, as relative paths. |

### cutan.projects_store.DEFAULT_PUSH_EXCLUDES *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), ...]* *= ('.git/', '.an/render_work/', 'artifacts/shot_cache/', 'artifacts/shots/', 'artifacts/render_reports/', 'artifacts/probes/')*

derived or transient output,
keyed by that machine or re-made from the project. The shot cache (an#242) and
the shot archive re-render from the project; the render work dirs are a run’s
scratch; render reports and probes are what `an init` keeps out of git
(`an.project.PROJECT_GITIGNORE`, held equal by a test); a repository is
not project content. Each entry is a folder prefix (ending in `/`) or a file.

* **Type:**
  What a push keeps on the machine that made it

### *class* cutan.projects_store.ProjectsStoreSettings(backend='local', bucket='tw-apps', profile='tw-server', tenant='thorwhalen')

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Which backend holds the projects, and its S3 coordinates.

#### coordinates()

What a project folder records about its store (no credentials, no profile).

```pycon
>>> ProjectsStoreSettings().coordinates()["backend"]
'local'
```

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

#### *classmethod* from_environ(environ=None)

```pycon
>>> ProjectsStoreSettings.from_environ({}).backend
'local'
>>> ProjectsStoreSettings.from_environ({"CUTAN_PROJECTS_BACKEND": "s3"}).backend
's3'
>>> env = {"CUTAN_PROJECTS_BACKEND": "s3", "CUTAN_HOME": "/x"}
>>> ProjectsStoreSettings.from_environ(env).backend
'local'
```

### *class* cutan.projects_store.PushReport(project_id, folder, written, unchanged, excluded, deleted, stale=(), conflicts=())

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

What one [`push_project()`](#cutan.projects_store.push_project) did, as relative paths.

`stale`: files the folder did not change but the store did (or dropped)
since the folder last synced, so they were not pushed: pull first.
`conflicts`: files both sides changed, not pushed without `force`.

### cutan.projects_store.STORE_RECORD *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= '.an/projects_store.json'*

The record’s path inside a project folder ([`cutan.PROJECT_STORE_RECORD`](cutan.html.md#cutan.PROJECT_STORE_RECORD)).

### cutan.projects_store.materialize_project(project_id, , settings=None, store=None, cache=None)

A real folder holding `project_id`’s files.

Local backend: the project folder itself, no copy. S3: files are read through
into the cache and kept, and the folder records the store it belongs to
([`STORE_RECORD`](#cutan.projects_store.STORE_RECORD)). A cached file is reused when its sha256 is the one
the store’s record holds for it (a file the record does not know: when its
size matches the object’s). The store wins: a cached file that differs is
overwritten, so push a folder’s changes before pulling into it.

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

### cutan.projects_store.new_project_dir(project_id, , default=None, settings=None, store=None, cache=None)

Where `an init <id> --id --genre cutout_animation` creates the project.

The `projects.dir.cutan` service (`an` API level 7): the core computes
its own default (`<root>/projects/<id>`) and hands it over as `default`.
Local backend: that default. S3: the cache folder, with what the store
already holds under the id read through first (so `an init` sees an
existing project’s `scene.md` and refuses to clobber it) and the record
that the folder belongs to the store, which a later [`push_project()`](#cutan.projects_store.push_project)
reads. Nothing is uploaded: the push is explicit.

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

### cutan.projects_store.projects_store(settings=None)

The projects as `{relative path: bytes}`, over disk or S3 per `settings`.

The local store creates a key’s folders on write, so a project pushed into it
from a folder elsewhere lands whole.

* **Return type:**
  [`MutableMapping`](https://docs.python.org/3/library/collections.abc.html#collections.abc.MutableMapping)

### cutan.projects_store.push_project(project_id, , folder=None, settings=None, store=None, delete_missing=False, exclude=('.git/', '.an/render_work/', 'artifacts/shot_cache/', 'artifacts/shots/', 'artifacts/render_reports/', 'artifacts/probes/'), force=False, cache=None)

Write `folder`’s files to the store under `project_id/`: the inverse of
[`materialize_project()`](#cutan.projects_store.materialize_project) (cutan#91).

`folder` defaults to where [`materialize_project()`](#cutan.projects_store.materialize_project) puts the project: the
cache folder on S3, the project folder itself locally (which is the store’s
own copy, so that push does nothing). Each file is compared three ways: with
the store’s record of it (the store’s copy of [`STORE_RECORD`](#cutan.projects_store.STORE_RECORD)) and with
the folder’s record (the base: what the folder last pulled or pushed; with
no base, the store’s record stands in, so a first push from a folder with no
history writes its differences). A file equal to the store’s is unchanged;
one the folder changed and the store did not is written; one the folder did
not change but the store did is `stale` and left alone; one both changed
is a `conflict`, written only with `force`. A file the records do not
know is compared with the store’s bytes when the key exists. `exclude`
names what stays local ([`DEFAULT_PUSH_EXCLUDES`](#cutan.projects_store.DEFAULT_PUSH_EXCLUDES)); `delete_missing`
deletes the store’s keys the folder no longer has (a key the store gained or
changed since the base is kept, unless `force`); excluded files the folder
still has are never deleted. The record is then written to the folder and,
when anything changed, to the store.

* **Return type:**
  [`PushReport`](#cutan.projects_store.PushReport)

### cutan.projects_store.read_record(folder)

The folder’s [`STORE_RECORD`](#cutan.projects_store.STORE_RECORD), `{}` when it has none or it is unreadable.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)
