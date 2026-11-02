# cutan.characters.cast

A cast as data: `cast.yaml`, one entry per character, read by the factory (cutan#87).

A production pack used to carry its cast as `cast.sh`, one `an character`
shell line per step. `cast.yaml` says the same as data:

```default
mara:
  build: tall
  hair_style: bun
  palette: {skin: "#c08a5a", hair: "#2b1d14"}
  mouth_variants: [happy, sad]
  voice_ref: mara_voice
teo:
  build: squat
  head_scale: 1.2
  hat: cap
  mouths: [angry]          # more mouth sets after the character is made
  half_lid: 0.5            # a half eyelid for squints
```

Each entry is the factory’s options (`an character new`, always offline)
plus three follow-up steps (`mouths`, `half_lid`, `gaze`). The keys are
the ones `cutan.pack.CAST_OPTIONS` allows a pack, so a cast file cannot
reach an option a `cast.sh` line could not.

[`cast_steps()`](#cutan.characters.cast.cast_steps) reads a file or a mapping into [`CastStep`](#cutan.characters.cast.CastStep);
[`CastStep.argv()`](#cutan.characters.cast.CastStep.argv) is the `an character` command line (what a pack check
runs, behind the allow-list), and [`run_cast()`](#cutan.characters.cast.run_cast) runs the steps in this
process through the factory’s own commands (`an character cast FILE`).

```pycon
>>> [s.argv() for s in cast_steps({"teo": {"build": "squat", "hat": "cap", "half_lid": 0.5}})]
[['an', 'character', 'new', 'teo', '--offline', '--build', 'squat', '--hat', 'cap'], ['an', 'character', 'add-half-lid', 'teo', '--fraction', '0.5']]
```

### Module Attributes

| [`NAME_RE`](#cutan.characters.cast.NAME_RE)        | a name ending in a newline would make a folder of that name.                                                                                                  |
|-----------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`MAX_CAST_BYTES`](#cutan.characters.cast.MAX_CAST_BYTES) | a cast is a page of options, and a pack is checked on a server.                                                                                               |
| [`NEW_OPTIONS`](#cutan.characters.cast.NEW_OPTIONS)    | The options of `an character new` a cast entry may set, by key, with the type its value must have (a list joins with commas, a mapping as `key=value` pairs). |
| [`FOLLOW_UPS`](#cutan.characters.cast.FOLLOW_UPS)     | the `an character` subcommand, its option, and the value's type (`True` for a step that takes none).                                                          |

### Functions

| [`cast_steps`](#cutan.characters.cast.cast_steps)(cast)              | The factory steps of a cast file (or its mapping), in order: each character's `new`, then its follow-ups.   |
|--------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------|
| [`run_cast`](#cutan.characters.cast.run_cast)(cast, \*[, out_dir]) | Run a cast's steps through the factory's own commands, in this process; `(ok, one message per step)`.       |

### Classes

| [`CastStep`](#cutan.characters.cast.CastStep)(command, name[, options])   | One factory step: `an character <command> <name> <options>`.   |
|---------------------------------------------------------------------------------------|----------------------------------------------------------------|

### Exceptions

| [`CastError`](#cutan.characters.cast.CastError)   | A cast file that cannot be read as a cast; the message names the entry.   |
|--------------------------------------------------------------|---------------------------------------------------------------------------|

### *exception* cutan.characters.cast.CastError

Bases: [`ValueError`](https://docs.python.org/3/builtins/exceptions.html#ValueError)

A cast file that cannot be read as a cast; the message names the entry.

### *class* cutan.characters.cast.CastStep(command, name, options=dict())

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

One factory step: `an character <command> <name> <options>`.

#### argv()

The `an character` command line of this step (from [`kwargs()`](#cutan.characters.cast.CastStep.kwargs)).

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

#### kwargs()

The factory command’s keyword arguments (lists and mappings as the
command’s text; a new character is always made offline).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### cutan.characters.cast.FOLLOW_UPS *: [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None), [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[type](https://docs.python.org/3/builtins/functions.html#type), ...]]]* *= {'gaze': ('add-gaze', None, (<class 'bool'>,)), 'half_lid': ('add-half-lid', '--fraction', (<class 'int'>, <class 'float'>)), 'mouths': ('mouths', '--variants', (<class 'str'>, <class 'list'>))}*

the `an character`
subcommand, its option, and the value’s type (`True` for a step that
takes none).

* **Type:**
  The follow-up steps an entry may ask for, by key

### cutan.characters.cast.MAX_CAST_BYTES *: [int](https://docs.python.org/3/builtins/functions.html#int)* *= 65536*

a
cast is a page of options, and a pack is checked on a server.

* **Type:**
  The largest cast file read, and the longest value in it (characters)

### cutan.characters.cast.NAME_RE *= re.compile('^[a-z][a-z0-9_]{0,40}\\\\Z')*

a name
ending in a newline would make a folder of that name.

* **Type:**
  A character id
* **Type:**
  lowercase letters, digits, `_`. `\Z`, not `$`

### cutan.characters.cast.NEW_OPTIONS *: [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[type](https://docs.python.org/3/builtins/functions.html#type), ...]]* *= {'build': (<class 'str'>,), 'clothing_pattern': (<class 'str'>,), 'hair_length': (<class 'str'>,), 'hair_style': (<class 'str'>,), 'hat': (<class 'str'>,), 'head_scale': (<class 'int'>, <class 'float'>), 'mouth_variants': (<class 'str'>, <class 'list'>), 'palette': (<class 'str'>, <class 'collections.abc.Mapping'>), 'sash': (<class 'bool'>,), 'views': (<class 'bool'>,), 'voice_ref': (<class 'str'>,)}*

The options of `an character new` a cast entry may set, by key, with the
type its value must have (a list joins with commas, a mapping as
`key=value` pairs). `views: false` is `--no-views`.

### cutan.characters.cast.cast_steps(cast)

The factory steps of a cast file (or its mapping), in order: each
character’s `new`, then its follow-ups. Raise [`CastError`](#cutan.characters.cast.CastError) on an
unknown key, a wrong type or a name the factory would refuse.

```pycon
>>> cast_steps({"Teo": {}})
Traceback (most recent call last):
...
cutan.characters.cast.CastError: cast.yaml 'Teo': not a character name (lowercase letters, digits, _)
```

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`CastStep`](#cutan.characters.cast.CastStep)]

### cutan.characters.cast.run_cast(cast, , out_dir='')

Run a cast’s steps through the factory’s own commands, in this process;
`(ok, one message per step)`. Stops at the first step that fails, since
every later step of a cast builds on the earlier ones.

* **Return type:**
  [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`bool`](https://docs.python.org/3/builtins/functions.html#bool), [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]]
