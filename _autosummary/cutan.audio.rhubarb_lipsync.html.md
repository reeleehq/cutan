# cutan.audio.rhubarb_lipsync

RhubarbLipSync — calls the rhubarb-lip-sync binary for phoneme-aligned visemes.

Requires the `rhubarb` binary on PATH. macOS: `brew install rhubarb-lipsync`.
Linux/Windows: download from the project’s GitHub releases.

Falls back gracefully (raises a clear error) if the binary is missing — the
default `OfflineLipSync` keeps the pipeline functional in the meantime.

**The recognizer follows the language** (an#96, epic #9 defect 5a). Rhubarb has
two: `pocketSphinx` — its default, “use for English recordings”, the only one
that reads `--dialogFile` (it builds a dialog language model and mixes it 90/10
with the default) — and `phonetic`, “use for non-English recordings”, which
`UNUSED(dialog)``s the transcript at source. This module used to pass
``-r phonetic` **and** `--dialogFile` unconditionally: English speech from an
English transcript ran the language-independent recognizer and the transcript
it wrote to disk was never read. Now `recognizer=None` (the default) resolves
per `language` — `"en"` → `pocketSphinx` with the dialog file, anything
else → `phonetic` and **no transcript is written** (a file nothing reads is a
lie waiting for the next reader). An explicit `recognizer` still overrides.
`name` carries the recognizer so the viseme cache key changes with it and no
stale `phonetic` track replays.

### Module Attributes

| [`ENGLISH_LANGUAGES`](#cutan.audio.rhubarb_lipsync.ENGLISH_LANGUAGES)   | The languages `pocketSphinx` (CMU Sphinx US English acoustic model) covers.   |
|----------------------------------------------------------------------|-------------------------------------------------------------------------------|

### Functions

| [`recognizer_for`](#cutan.audio.rhubarb_lipsync.recognizer_for)(language)   | The Rhubarb recognizer for a BCP-47 language tag (primary subtag only).   |
|-----------------------------------------------------------------------------|---------------------------------------------------------------------------|

### Classes

| [`RhubarbLipSync`](#cutan.audio.rhubarb_lipsync.RhubarbLipSync)(\*[, binary_path, language, ...])   | Wrap the rhubarb CLI.   |
|-----------------------------------------------------------------------------------------------------|-------------------------|

### Exceptions

| [`RhubarbNotFoundError`](#cutan.audio.rhubarb_lipsync.RhubarbNotFoundError)   | The rhubarb binary is not on this machine (with how to install it).   |
|-------------------------------------------------------------------------|-----------------------------------------------------------------------|

### cutan.audio.rhubarb_lipsync.ENGLISH_LANGUAGES *: [frozenset](https://docs.python.org/3/builtins/stdtypes.html#frozenset)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)]* *= frozenset({'en'})*

The languages `pocketSphinx` (CMU Sphinx US English acoustic model) covers.

### *class* cutan.audio.rhubarb_lipsync.RhubarbLipSync(, binary_path=None, language='en', recognizer=None, timeout_s=60.0)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Wrap the rhubarb CLI. Implements the `LipSyncProvider` protocol.

```pycon
>>> RhubarbLipSync(binary_path="/bin/rhubarb").recognizer
'pocketSphinx'
>>> RhubarbLipSync(binary_path="/bin/rhubarb", language="de").recognizer
'phonetic'
>>> RhubarbLipSync(binary_path="/bin/rhubarb", language="de").name
'rhubarb:phonetic'
```

#### check_available()

Raise [`RhubarbNotFoundError`](#cutan.audio.rhubarb_lipsync.RhubarbNotFoundError) when this machine has no binary.

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

#### repeatable *: [bool](https://docs.python.org/3/builtins/functions.html#bool)* *= True*

The same audio, transcript and recognizer give the same track on one
machine (one binary), and nothing is billed: `an cache gc` may re-make
a missing track in memory (an#311, cutan#29). A machine without the
binary says so in [`check_available()`](#cutan.audio.rhubarb_lipsync.RhubarbLipSync.check_available).

#### *property* uses_dialog_file *: [bool](https://docs.python.org/3/builtins/functions.html#bool)*

Whether the chosen recognizer reads a transcript at all.

### *exception* cutan.audio.rhubarb_lipsync.RhubarbNotFoundError

Bases: [`RuntimeError`](https://docs.python.org/3/builtins/exceptions.html#RuntimeError)

The rhubarb binary is not on this machine (with how to install it).

### cutan.audio.rhubarb_lipsync.recognizer_for(language)

The Rhubarb recognizer for a BCP-47 language tag (primary subtag only).

Accepts the POSIX locale spelling too (`en_US`); an empty tag is refused
rather than read as “non-English” (an#96 review).

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

```pycon
>>> recognizer_for("en"), recognizer_for("en-GB"), recognizer_for("en_US"), recognizer_for("fr")
('pocketSphinx', 'pocketSphinx', 'pocketSphinx', 'phonetic')
```
