# cutan.styles

The named cut-out style specs, shipped as package data (cutan#4).

A style spec is one YAML document per named look (`south_park`,
`oversimplified`, `kurzgesagt`, `gilliam`, `reiniger`, `norstein`):
`live` settings that map onto shipped `an` features, `targets` the style
lint measures a render against, `prosody_targets` for voice acting, and
`guidance` for what the style needs beyond them. The `cutan-style` skill is
the procedure that applies one; this module is where the specs live, so code
and agents load a spec by its name rather than through a path into a skill
folder.

```pycon
>>> 'south_park' in style_specs()
True
>>> spec = style_spec('south_park')
>>> spec['style'], spec['cost_class']
('south_park', 'low')
>>> style_spec_path('south_park').name
'south_park.yaml'
```

Each call returns a fresh dict, so a caller may change it freely:

```pycon
>>> style_spec('south_park') is style_spec('south_park')
False
```

An unknown name is refused with the names there are (a `KeyError`):

```pycon
>>> try:
...     style_spec('pixar')
... except KeyError as e:
...     print(e)
no style spec named 'pixar'; the specs are: gilliam, kurzgesagt, norstein, oversimplified, reiniger, south_park
```

**A spec changes between releases** (targets re-measured, roles re-cast), and
whatever a production copied out of one (a StylePack, a voice document with
resolved targets, a kit) is a snapshot of the version it was copied from.
[`style_spec_digest()`](#cutan.styles.style_spec_digest) names that version: record it beside the copy, and
compare it with the installed spec’s to know whether the copy is current.

```pycon
>>> len(style_spec_digest('south_park'))
64
```

[`resolve_style_spec()`](#cutan.styles.resolve_style_spec) is the one place a *reference* to a spec becomes a
spec: a mapping (passed through), a path to a YAML file, or a style’s name.

`python -m cutan.styles` lists the specs, `python -m cutan.styles NAME`
prints one, and `python -m cutan.styles NAME --path` prints its file’s path
(for a tool that wants a path, such as `an.verify.prosody --targets`).

### Module Attributes

| [`STYLE_SPEC_SUFFIX`](#cutan.styles.STYLE_SPEC_SUFFIX)         | The file suffix of a style spec in this package.                                                        |
|----------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------|
| [`STYLE_SPEC_SCHEMA_VERSION`](#cutan.styles.STYLE_SPEC_SCHEMA_VERSION) | bumped when a key's meaning changes, so a reader of a spec copied elsewhere knows which shape it holds. |

### Functions

| [`resolve_style_spec`](#cutan.styles.resolve_style_spec)(ref)                | A style spec as a dict, from whatever refers to one.                                                                                                                                                        |
|-----------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`style_spec`](#cutan.styles.style_spec)(name)                       | The style spec `name`, parsed: a new dict on every call.                                                                                                                                                    |
| [`style_spec_digest`](#cutan.styles.style_spec_digest)(name)                | The sha256 of the style spec `name`'s file: the version a copy was made from.                                                                                                                               |
| [`style_spec_path`](#cutan.styles.style_spec_path)(name)                  | The file of the style spec `name` (for a tool that reads a path).                                                                                                                                           |
| [`style_spec_text`](#cutan.styles.style_spec_text)(name)                  | The YAML text of the style spec `name`, comments included.                                                                                                                                                  |
| [`style_specs`](#cutan.styles.style_specs)()                          | The names of the style specs that ship with `cutan`, sorted.                                                                                                                                                |
| [`check_policy`](#cutan.styles.check_policy)(policy, \*[, where])      | `policy` parsed into an `an.semantic.Policy`, or [`PolicyError`](#cutan.styles.PolicyError) naming `where`.                                                                               |
| [`layered_policy`](#cutan.styles.layered_policy)(\*[, shot, style_pack]) | The policy in force: `shot` over `style_pack` (each checked).                                                                                                                                               |
| [`policy_of`](#cutan.styles.policy_of)(obj)                         | The policy block an object carries: a `policy` field (declared or extra) or key; else `None`.                                                                                                               |
| [`policy_problems`](#cutan.styles.policy_problems)(policy)                | What is wrong with a `policy` block, one sentence each (empty when it is sound).                                                                                                                            |
| [`style_pack`](#cutan.styles.style_pack)(spec)                       | The StylePack a project saves for a style: its `live.style_pack` (a bare pack named after the style when the spec has none), its `policy`, and the spec it was copied from (name and digest) in `metadata`. |
| [`style_voice`](#cutan.styles.style_voice)(spec, role)                | The partial voice document `spec` casts `role` as (<br/><br/>```<br/>``<br/>```<br/><br/>an.audio.takes.                                                                                                    |
| [`check_style_copies`](#cutan.styles.check_style_copies)(ctx)                | `an validate`: the style pack the scene names, and every voice its lines speak with, warn when they were copied from an older version of the shipped spec they record (cutan#19).                           |

### Exceptions

| [`UnknownStyleError`](#cutan.styles.UnknownStyleError)   | No style spec of that name ships with `cutan`.                                   |
|----------------------------------------------------------------------|----------------------------------------------------------------------------------|
| [`PolicyError`](#cutan.styles.PolicyError)         | A policy block names an aspect or a method that does not exist, or is malformed. |

### *exception* cutan.styles.PolicyError

Bases: [`ValueError`](https://docs.python.org/3/builtins/exceptions.html#ValueError)

A policy block names an aspect or a method that does not exist, or is malformed.

### cutan.styles.STYLE_SPEC_SCHEMA_VERSION *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= '0.1.0'*

bumped when a key’s meaning
changes, so a reader of a spec copied elsewhere knows which shape it holds.

* **Type:**
  The `schema_version` the shipped specs carry

### cutan.styles.STYLE_SPEC_SUFFIX *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= '.yaml'*

The file suffix of a style spec in this package.

### *exception* cutan.styles.UnknownStyleError

Bases: [`KeyError`](https://docs.python.org/3/builtins/exceptions.html#KeyError)

No style spec of that name ships with `cutan`.

A `KeyError` (so a mapping or a `ChainMap` of spec sources falls through
it), and so also a `LookupError`.

### cutan.styles.check_policy(policy, , where='policy')

`policy` parsed into an `an.semantic.Policy`, or [`PolicyError`](#cutan.styles.PolicyError) naming `where`.

* **Return type:**
  [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

### cutan.styles.check_style_copies(ctx)

`an validate`: the style pack the scene names, and every voice its lines
speak with, warn when they were copied from an older version of the shipped
spec they record (cutan#19). Once per validation.

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### cutan.styles.layered_policy(, shot=None, style_pack=None)

The policy in force: `shot` over `style_pack` (each checked).

Each argument is anything [`policy_of()`](#cutan.styles.policy_of) reads (or `None`). The
author’s explicit request is not here: the matcher puts it first
(`resolve(..., requested=)`).

* **Return type:**
  [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

### cutan.styles.policy_of(obj)

The policy block an object carries: a `policy` field (declared or extra) or key; else `None`.

* **Return type:**
  [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

```pycon
>>> policy_of({"policy": {"locomotion": ["loco.glide"]}})
{'locomotion': ['loco.glide']}
>>> policy_of(None) is None
True
```

### cutan.styles.policy_problems(policy)

What is wrong with a `policy` block, one sentence each (empty when it is sound).

Every aspect must be registered, every choice a method OF that aspect (by
id: `loco.bounce`, not `bounce`), and every choice well formed (an id or
`{method, args, version}`).

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

```pycon
>>> policy_problems({"locomotion": ["loco.bounce", "loco.glide"]})
[]
>>> for p in policy_problems({"locomotion": ["bounce"], "dance": ["x"]}): print(p)
policy locomotion: 'bounce' is not a locomotion method id; did you mean 'loco.bounce'?
policy aspect 'dance' is not registered (aspects: expression, locomotion, speech)
```

### cutan.styles.resolve_style_spec(ref)

A style spec as a dict, from whatever refers to one.

- a mapping is passed through (a deep copy);
- a string spelled as a name (no path separator, no suffix) is looked up
  by name in the spec sources — today the shipped specs only — and never
  read from a file in the working directory (spell a local file
  `./south_park`);
- anything else is a path to a YAML file.

```pycon
>>> resolve_style_spec('reiniger')['style']
'reiniger'
>>> resolve_style_spec({'targets': {}})
{'targets': {}}
```

A missing file whose stem is a shipped style says how to load that one:

```pycon
>>> resolve_style_spec('oversimplified.yaml')
Traceback (most recent call last):
  ...
FileNotFoundError: no style spec file 'oversimplified.yaml' ...
```

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### cutan.styles.style_pack(spec)

The StylePack a project saves for a style: its `live.style_pack` (a bare
pack named after the style when the spec has none), its `policy`, and the
spec it was copied from (name and digest) in `metadata`.

`spec` is anything [`cutan.styles.resolve_style_spec()`](#cutan.styles.resolve_style_spec) takes (a
style’s name, a path, a mapping). Save it as the skill’s step 3 says:
`mall["styles"][pack.name] = pack.model_dump(mode="json")`.

* **Return type:**
  [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

```pycon
>>> pack = style_pack("south_park")
>>> pack.name, pack.policy, pack.metadata["style_spec"]["name"]
('south_park', {'locomotion': ['loco.bounce']}, 'south_park')
```

### cutan.styles.style_spec(name)

The style spec `name`, parsed: a new dict on every call.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### cutan.styles.style_spec_digest(name)

The sha256 of the style spec `name`’s file: the version a copy was made from.

It hashes the file’s bytes with line endings normalised to `\n` (a
Windows checkout has the same spec as the wheel), so a comment-only edit
is a new version too.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### cutan.styles.style_spec_path(name)

The file of the style spec `name` (for a tool that reads a path).

Raises `FileNotFoundError` when `cutan` is imported from an archive
(a zipped wheel), where the spec is not a file: use [`style_spec_text()`](#cutan.styles.style_spec_text).

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

### cutan.styles.style_spec_text(name)

The YAML text of the style spec `name`, comments included.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### cutan.styles.style_specs()

The names of the style specs that ship with `cutan`, sorted.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

### cutan.styles.style_voice(spec, role)

The partial voice document `spec` casts `role` as (`an.audio.takes.
style_voice_role`: target names resolved to values), with the spec it came
from recorded, so a later re-measure of the style is noticed. Merge it beside
a `voice_id`: `{**style_voice("oversimplified", "eager"), "voice_id": ...}`.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

```pycon
>>> doc = style_voice("oversimplified", "narrator")
>>> doc["metadata"]["style_spec"]["name"], "targets" in doc["takes"]["cues"]["deadpan"]
('oversimplified', True)
```

### Modules

| [`copies`](cutan.styles.copies.md#module-cutan.styles.copies)   | Copies of a style spec, and whether they are stale (cutan#19).                                  |
|--------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------|
| [`policy`](cutan.styles.policy.md#module-cutan.styles.policy)   | A style's policy: per-aspect method orders the compiler applies (ADR 0002 decision 4, cutan#9). |
