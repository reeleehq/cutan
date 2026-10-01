# cutan

cutan: cut-out animation, as a genre package on the `an` core.

`an` is the core of structured animation (scene documents, the timing kernel,
renderers, audio, storage, verification). A *genre* adds what one kind of
animation needs and registers it with the core; `cutan` is the first genre to
leave `an`: rigged characters, faces and expressions, lip-sync visemes, swap
sets and views, cut-out styles and impacts (ADR 0001 in `an`’s
`misc/docs/adr/`, tracked by an#225 under the epic an#231).

**Status: scaffold.** The cut-out code still lives inside `an` and is
moved here in batches, expand -> migrate -> contract: each module arrives here,
`an` keeps a deprecation re-export for one release, then drops it. Until the
genre object itself moves, `an` ships it and this package registers nothing.

The identifiers below are the genre’s **persisted** names (ADR 0001 decision 9):
they are written into documents, stores and entry-point metadata, and none of
them changes when code moves between distributions.

```pycon
>>> GENRE_NAME
'cutout_animation'
>>> ENTRY_POINT_GROUP, ENTRY_POINT_NAME
('an.genres', 'cutout_animation')
>>> RENDERER_NAME, LIBRARY_NAME
('cutout', 'cutan')
```

### Module Attributes

| [`GENRE_NAME`](#cutan.GENRE_NAME)        | the `an.genres` entry-point name and the `nw` genre id.                                                                                  |
|--------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------|
| [`ENTRY_POINT_GROUP`](#cutan.ENTRY_POINT_GROUP) | The entry-point group `an.genres.load()` reads.                                                                                          |
| [`ENTRY_POINT_NAME`](#cutan.ENTRY_POINT_NAME)  | the SAME name `an` declares today, so the handover is by name.                                                                           |
| [`ENTRY_POINT_VALUE`](#cutan.ENTRY_POINT_VALUE) | Where the entry point will point once the genre object lives here.                                                                       |
| [`RENDERER_NAME`](#cutan.RENDERER_NAME)     | The persisted renderer name of cut-out shots (`an.stage` claims it).                                                                     |
| [`LIBRARY_NAME`](#cutan.LIBRARY_NAME)      | The package whose data root holds the genre's asset library and projects (`~/.local/share/cutan` by default; `CUTAN_HOME` overrides it). |

### cutan.ENTRY_POINT_GROUP *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'an.genres'*

The entry-point group `an.genres.load()` reads.

### cutan.ENTRY_POINT_NAME *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'cutout_animation'*

the SAME name `an`
declares today, so the handover is by name. `an.genres` de-duplicates by
entry-point name with `an`’s in-distribution declaration first, so while
`an` still ships the genre, a declaration here is shadowed, never doubled.

* **Type:**
  The entry-point name this distribution will declare

### cutan.ENTRY_POINT_VALUE *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'cutan.genre:CUTOUT'*

Where the entry point will point once the genre object lives here.

### cutan.GENRE_NAME *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'cutout_animation'*

the `an.genres` entry-point name and the `nw` genre id.

* **Type:**
  The genre’s slug

### cutan.LIBRARY_NAME *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'cutan'*

The package whose data root holds the genre’s asset library and projects
(`~/.local/share/cutan` by default; `CUTAN_HOME` overrides it).

### cutan.RENDERER_NAME *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'cutout'*

The persisted renderer name of cut-out shots (`an.stage` claims it).
