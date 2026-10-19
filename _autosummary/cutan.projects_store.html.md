# cutan.projects_store

Where a cutan project’s files are read from: a disk folder or S3, by configuration.

The library’s `projects` kind is a mapping `relative path -> bytes` (ADR-0024:
`s3://{bucket}/{tenant}/cutan/projects/{rel}` mirrors `~/.local/share/cutan/projects/{rel}`
exactly, so both backends hold the same keys). [`projects_store()`](#cutan.projects_store.projects_store) returns that
mapping; [`materialize_project()`](#cutan.projects_store.materialize_project) returns a real folder for tools that need files
(ffmpeg, a browser), reading through a cache under `~/.cache/cutan/projects/`.

Configuration (environment; the first match wins, `CUTAN_HOME` always forces local):

- `CUTAN_HOME` set: local, under that root (an explicit root beats any S3 setting)
- `CUTAN_PROJECTS_BACKEND=s3`: S3, with `CUTAN_S3_BUCKET` (default `tw-apps`),
  `CUTAN_S3_PROFILE` (default `tw-server`) and `CUTAN_S3_TENANT` (default `thorwhalen`)
- otherwise: local (the default)

### Functions

| `cache_root`()                                                                              |                                                                           |
|---------------------------------------------------------------------------------------------|---------------------------------------------------------------------------|
| [`materialize_project`](#cutan.projects_store.materialize_project)(project_id, \*[, ...]) | A real folder holding `project_id`'s files.                               |
| [`projects_store`](#cutan.projects_store.projects_store)([settings])                 | The projects as `{relative path: bytes}`, over disk or S3 per `settings`. |

### Classes

| [`ProjectsStoreSettings`](#cutan.projects_store.ProjectsStoreSettings)([backend, bucket, ...])   | Which backend holds the projects, and its S3 coordinates.   |
|--------------------------------------------------------------------------------------------------|-------------------------------------------------------------|

### *class* cutan.projects_store.ProjectsStoreSettings(backend='local', bucket='tw-apps', profile='tw-server', tenant='thorwhalen')

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Which backend holds the projects, and its S3 coordinates.

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

### cutan.projects_store.materialize_project(project_id, , settings=None, store=None, cache=None)

A real folder holding `project_id`’s files.

Local backend: the project folder itself, no copy. S3: files are read through
into the cache and kept; a cached file whose size matches the object’s is reused.

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

### cutan.projects_store.projects_store(settings=None)

The projects as `{relative path: bytes}`, over disk or S3 per `settings`.

* **Return type:**
  [`MutableMapping`](https://docs.python.org/3/library/collections.abc.html#collections.abc.MutableMapping)
