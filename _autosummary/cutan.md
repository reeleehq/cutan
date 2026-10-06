# cutan

cutan: cut-out animation, as a genre package on the `an` core.

`an` is the core of structured animation (scene documents, the timing kernel,
renderers, audio, storage, verification). A *genre* adds what one kind of
animation needs and registers it with the core; `cutan` is the first genre to
leave `an`: rigged characters, faces and expressions, lip-sync visemes, swap
sets and views, cut-out styles and impacts (ADR 0001 in `an`’s
`misc/docs/adr/`, tracked by an#225 under the epic an#231).

Rigged characters (`cutan.characters`), faces (`cutan.expression`), impacts
(`cutan.impacts`), the cut-out compile passes (`cutan.compile`), lip-sync
providers (`cutan.audio`), the style lint (`cutan.verify`) and the genre object
(`cutan.genre`) lived inside `an` until the P8 move (an#225); `an` keeps
warning aliases at the old import paths. Install it with `pip install "an[cutout]"`;
`an` finds it through the `an.genres` entry point.

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

| [`GENRE_NAME`](#cutan.GENRE_NAME)            | the `an.genres` entry-point name and the `nw` genre id.                                                                                                                                 |
|------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`ENTRY_POINT_GROUP`](#cutan.ENTRY_POINT_GROUP)     | The entry-point group `an.genres.load()` reads.                                                                                                                                         |
| [`ENTRY_POINT_NAME`](#cutan.ENTRY_POINT_NAME)      | the name `an` used to declare for the in-distribution genre, so the handover was by name.                                                                                               |
| [`ENTRY_POINT_VALUE`](#cutan.ENTRY_POINT_VALUE)     | Where the entry point points.                                                                                                                                                           |
| [`RENDERER_NAME`](#cutan.RENDERER_NAME)         | The persisted renderer name of cut-out shots (`an.stage` claims it).                                                                                                                    |
| [`LIBRARY_NAME`](#cutan.LIBRARY_NAME)          | The package whose data root holds the genre's asset library and projects (`~/.local/share/cutan` by default; `CUTAN_HOME` overrides it).                                                |
| [`REQUIRED_AN_API_LEVEL`](#cutan.REQUIRED_AN_API_LEVEL) | The lowest `an.genres.API_LEVEL` this `cutan` runs against ("the lowest `an` it supports", ADR 0001 decision 8, said without a version pin: `an`'s version is assigned by CI at merge). |

### Functions

| [`require_an`](#cutan.require_an)()     | Refuse, with an upgrade hint, to load against an `an` older than this `cutan` needs.   |
|-------------------------------------------------------------------|----------------------------------------------------------------------------------------|
| [`style_spec`](#cutan.style_spec)(name) | The style spec `name`, parsed: a new dict on every call.                               |
| [`style_specs`](#cutan.style_specs)()    | The names of the style specs that ship with `cutan`, sorted.                           |

### cutan.ENTRY_POINT_GROUP *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'an.genres'*

The entry-point group `an.genres.load()` reads.

### cutan.ENTRY_POINT_NAME *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'cutout_animation'*

the name
`an` used to declare for the in-distribution genre, so the handover was by name.

* **Type:**
  The entry-point name this distribution declares (`pyproject.toml`)

### cutan.ENTRY_POINT_VALUE *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'cutan.genre:CUTOUT'*

Where the entry point points.

### cutan.GENRE_NAME *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'cutout_animation'*

the `an.genres` entry-point name and the `nw` genre id.

* **Type:**
  The genre’s slug

### cutan.LIBRARY_NAME *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'cutan'*

The package whose data root holds the genre’s asset library and projects
(`~/.local/share/cutan` by default; `CUTAN_HOME` overrides it).

### cutan.RENDERER_NAME *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'cutout'*

The persisted renderer name of cut-out shots (`an.stage` claims it).

### cutan.REQUIRED_AN_API_LEVEL *: [int](https://docs.python.org/3/builtins/functions.html#int)* *= 6*

The lowest `an.genres.API_LEVEL` this `cutan` runs against (“the lowest `an`
it supports”, ADR 0001 decision 8, said without a version pin: `an`’s version is
assigned by CI at merge). Level 2 is the move itself: `Genre.services`,
`ActionKind.lowering`, `EntityKind.swap_declaration` and `an.stage.rig`.
Level 3 is the public rig builder (an#338): `an.stage.rig.build_rig_subtree`,
`rig_origin`, `RigDocument` and `omit_unset_rig_fields`. Level 4 is the rest
pose (an#339): `register_rest_pose_migration` and `rig_rest_problems`. Level 5
is nested chains (an#340): `build_rig_subtree(skip_slots=)`, `slot_parent_chain`,
`slot_node_paths`, `rig_affordances`, `RigError`.
Level 6: `rest_pose_protection` (an#407), which `validate_character` says aloud.

### cutan.require_an()

Refuse, with an upgrade hint, to load against an `an` older than this `cutan` needs.

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

```pycon
>>> require_an()
```

### cutan.style_spec(name)

The style spec `name`, parsed: a new dict on every call.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### cutan.style_specs()

The names of the style specs that ship with `cutan`, sorted.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

### Modules

| [`audio`](cutan.audio.md#module-cutan.audio)           | The cut-out genre's lip-sync providers: letters, Rhubarb and word timings to mouth shapes.                 |
|-------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------|
| [`bench`](cutan.bench.md#module-cutan.bench)           | The cut-out genre's bench corpus: eight scenes that use characters, and their goldens.                     |
| [`carve`](cutan.carve.md#module-cutan.carve)           | Carve: a photo or a video frame in, a matted, normalised, provenance-carrying cut-out part out (cutan#10). |
| [`characters`](cutan.characters.md#module-cutan.characters) | Character art system: Spine-shaped descriptor + SVG sidecars.                                              |
| [`compile`](cutan.compile.md#module-cutan.compile)       | The cut-out genre's compile passes, their lowering hooks and the visuals of its runtime.                   |
| [`conftest`](cutan.conftest.md#module-cutan.conftest)     | Doctest collection for `cutan`: `nw` is an optional dependency of `cutan.nw` only.                         |
| [`expression`](cutan.expression.md#module-cutan.expression) | Facial expression for the cutout face (an#98, epic #9 Wave 6).                                             |
| [`genre`](cutan.genre.md#module-cutan.genre)           | The cut-out animation genre, declared as one object.                                                       |
| [`impacts`](cutan.impacts.md#module-cutan.impacts)       | Synthetic impact clips with exact ground truth, for scoring sub-frame timing.                              |
| [`library`](cutan.library.md#module-cutan.library)       | The character analyser: legs, arms, views and mouth chart, derived from the rig.                           |
| [`motion`](cutan.motion.md#module-cutan.motion)         | The cut-out genre's motion presets: moves that name a rig's parts or swap its views.                       |
| [`runtime`](cutan.runtime.md#module-cutan.runtime)       | JavaScript the cut-out genre adds to the stage runtime (`visuals.js`: the mouth and eye).                  |
| [`styles`](cutan.styles.md#module-cutan.styles)         | The named cut-out style specs, shipped as package data (cutan#4).                                          |
| [`verify`](cutan.verify.md#module-cutan.verify)         | The cut-out style lint: measures a render against a named style spec.                                      |
