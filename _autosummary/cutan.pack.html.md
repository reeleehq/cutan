# cutan.pack

Check a cut-out production pack with cutan’s own validators (cutan#87).

A production pack (the `cutan-production-pack` skill, cutan#86) is a folder
shaped like an `an` project: `scene.md`, `cast.sh` (one `an character
...` command per line), `assets/` (environments, props, voices, styles,
optional redrawn character parts) and `PRODUCTION.md`. [`check_pack()`](#cutan.pack.check_pack)
builds a throwaway project from it and runs the real checks:

1. lint every SVG drawing in the pack (root tag, size, forbidden elements,
   outside links), check that every picture (PNG, JPEG, WebP: plates, prop
   parts, reference sheets) is one, and the keys of every voice document;
2. `an init` a scratch project and copy the pack over it, except redrawn
   character parts (a character folder with no `character.json`);
3. run each `cast.sh` line, refusing anything but the factory commands and
   options the skill documents (no shell: the line is split and run directly);
4. copy the redrawn parts over the factory’s (same file names, same root tag),
   check the voice documents with the engine’s own checks, then `an character
   validate` every character and `an props validate` every drawn prop;
5. `an validate --strict-assets` the scene.

A step fails on an error in its output, not only on its exit status (the
`an` commands exit 0 on some failures). The result is a [`PackReport`](#cutan.pack.PackReport):
one [`PackCheck`](#cutan.pack.PackCheck) per step, each with its errors and warnings, so a caller
(the skill’s `validate_pack.py`, the reelee connector’s `check this pack`
tool) can print it or return it as data ([`PackReport.to_dict()`](#cutan.pack.PackReport.to_dict)). A pack
that cannot be checked at all (no `scene.md`, a refused `cast.sh` line) is
a report with one failed `pack` check, never an exception. Its `notes` say
what is neither an error nor a warning: a pack whose drawings are all
hand-written SVG gets one, since such art looks computer-made
([`cutan.art_brief`](cutan.art_brief.html.md#module-cutan.art_brief) says what to ask for instead).

Nothing is rendered: no browser, no network (`an character new` must say
`--offline`), no paid call.

```pycon
>>> report = check_pack("/no/such/pack")
>>> report.ok, report.summary()
(False, 'FAIL: 0/1 checks passed, 0 warning(s)')
>>> report.errors
['pack: pack has no scene.md: is it a production pack?']
```

### Functions

| [`cast_commands`](#cutan.pack.cast_commands)(pack)                      | The `an character` commands of `cast.sh`; raise [`PackError`](#cutan.pack.PackError) on any other line.                                                                                                             |
|-------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`check_pack`](#cutan.pack.check_pack)(pack_dir, \*[, workdir, ...]) | Check the production pack at `pack_dir`; return a [`PackReport`](#cutan.pack.PackReport).                                                                                                                            |
| [`lint_svg`](#cutan.pack.lint_svg)(path, \*, exact_size)           | What is wrong with one SVG drawing (empty when nothing is).                                                                                                                                                                               |
| [`main`](#cutan.pack.main)([argv])                             | `python -m cutan.pack <pack> [--keep] [--json]`: check a pack; exit 1 on a failure.                                                                                                                                                       |
| [`pack_art_guidance`](#cutan.pack.pack_art_guidance)(pack_dir)              | What art to ask the writer for ([`cutan.art_brief.art_guidance()`](cutan.art_brief.html.md#cutan.art_brief.art_guidance)), in the look of the pack's named style if it has one, when every drawing is SVG; else None. |
| [`svg_only_art`](#cutan.pack.svg_only_art)(pack_dir)                   | How many drawings the pack has when every one is SVG (0 when any is a picture, or there are none): hand-written SVG looks computer-made.                                                                                                  |

### Classes

| [`PackCheck`](#cutan.pack.PackCheck)(label, ok[, output])   | One step of a pack check: its label, its verdict and what it printed.   |
|-----------------------------------------------------------------------------------|-------------------------------------------------------------------------|
| [`PackReport`](#cutan.pack.PackReport)([checks, notes])      | Every step of a pack check, in order.                                   |

### Exceptions

| [`PackError`](#cutan.pack.PackError)   | A pack that cannot be checked at all (a missing file, a refused line).   |
|--------------------------------------------------------------|--------------------------------------------------------------------------|

### *class* cutan.pack.PackCheck(label, ok, output='')

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

One step of a pack check: its label, its verdict and what it printed.

#### *property* errors *: [list](https://docs.python.org/3/builtins/stdtypes.html#list)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)]*

The step’s error lines (its whole output when it failed silently).

```pycon
>>> PackCheck("x", False, "  [error] bad\nfine").errors
['bad']
>>> PackCheck("x", False, "exit 2").errors
['exit 2']
```

#### *property* warnings *: [list](https://docs.python.org/3/builtins/stdtypes.html#list)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)]*

The step’s warning lines (a factory note counts as one).

### *exception* cutan.pack.PackError

Bases: [`Exception`](https://docs.python.org/3/builtins/exceptions.html#Exception)

A pack that cannot be checked at all (a missing file, a refused line).

### *class* cutan.pack.PackReport(checks=list(), notes=list())

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Every step of a pack check, in order.

#### *property* errors *: [list](https://docs.python.org/3/builtins/stdtypes.html#list)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)]*

`"<check>: <error>"` for every error of every check.

#### format()

The full report as text: each step’s verdict and output, then the summary.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

#### notes *: [list](https://docs.python.org/3/builtins/stdtypes.html#list)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)]*

Information for the writer that is neither an error nor a warning (it
never fails a check): e.g. that every drawing is hand-written SVG.

#### summary()

The one line a writer quotes in `PRODUCTION.md`.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

#### to_dict(, with_output=False)

The report as JSON-ready data (the output of each step on request).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

#### *property* warnings *: [list](https://docs.python.org/3/builtins/stdtypes.html#list)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)]*

`"<check>: <warning>"` for every warning of every check.

### cutan.pack.cast_commands(pack)

The `an character` commands of `cast.sh`; raise [`PackError`](#cutan.pack.PackError) on any other line.

Blank lines and `#` comments are skipped; a trailing backslash continues
a line.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]]

### cutan.pack.check_pack(pack_dir, , workdir=None, an_command=('/opt/hostedtoolcache/Python/3.12.15/x64/bin/python', '-P', '-m', 'an'), python=None, timeout=300.0, deadline=900.0)

Check the production pack at `pack_dir`; return a [`PackReport`](#cutan.pack.PackReport).

pack_dir: the pack folder (`scene.md`, `cast.sh`, `assets/`, `PRODUCTION.md`)
workdir: where the scratch project is built (default: a temporary folder,

> deleted afterwards; given, it is kept, and the project is `<workdir>/project`)

an_command: how to run `an` (default: `python -m an` with this interpreter)
python: the interpreter for the engine’s voice checks (default: the one in

> `an_command` when it starts with one, else this one)

timeout: seconds one step may run before it counts as failed
deadline: seconds the whole check may run (`None`: no limit)

The pack is untrusted: only `PACK_SUFFIXES` files are copied, the
`an` children run without the working directory on their import path
and without any secret-looking environment variable, the work is capped
(`MAX_CAST_LINES`, `MAX_ASSET_FOLDERS`, `deadline`), and the
report names no server path (the scratch project is `<project>`).

A pack that cannot be checked at all gives a report with one failed
`pack` check; nothing here raises on a bad pack.

* **Return type:**
  [`PackReport`](#cutan.pack.PackReport)

### cutan.pack.lint_svg(path, , exact_size)

What is wrong with one SVG drawing (empty when nothing is).

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

### cutan.pack.main(argv=None)

`python -m cutan.pack <pack> [--keep] [--json]`: check a pack; exit 1 on a failure.

* **Return type:**
  [`int`](https://docs.python.org/3/builtins/functions.html#int)

### cutan.pack.pack_art_guidance(pack_dir)

What art to ask the writer for ([`cutan.art_brief.art_guidance()`](cutan.art_brief.html.md#cutan.art_brief.art_guidance)), in the
look of the pack’s named style if it has one, when every drawing is SVG; else None.

```pycon
>>> pack_art_guidance("/no/such/pack") is None
True
```

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### cutan.pack.svg_only_art(pack_dir)

How many drawings the pack has when every one is SVG (0 when any is a picture,
or there are none): hand-written SVG looks computer-made.

```pycon
>>> svg_only_art("/no/such/pack")
0
```

* **Return type:**
  [`int`](https://docs.python.org/3/builtins/functions.html#int)
