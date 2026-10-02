# cutan.audio

The cut-out genre’s lip-sync providers: letters, Rhubarb and word timings to mouth shapes.

Moved from `an.audio` (an#225). `an.audio` keeps the protocols
(`LipSyncProvider`, `VisemeTrack`),
text-to-speech and the pipeline; a viseme only means something to a genre that
draws mouths. The genre registers these by name as `lipsync.<name>` services
([`cutan.genre`](cutan.genre.html.md#module-cutan.genre)), which is how `render(lipsync="offline")` and
`an render --lipsync rhubarb` keep working.

```pycon
>>> offline_factory().name
'offline'
```

### Functions

| [`offline_factory`](#cutan.audio.offline_factory)(\*\*_)          | The deterministic char-to-viseme provider (the default).                        |
|----------------------------------------------------------------------------------|---------------------------------------------------------------------------------|
| [`rhubarb_factory`](#cutan.audio.rhubarb_factory)(\*[, language]) | Rhubarb Lip Sync (needs the `rhubarb` binary); `language` picks its recognizer. |
| [`whisper_factory`](#cutan.audio.whisper_factory)(\*\*_)          | Word timings from Whisper, distributed over the mouth shapes.                   |

### Classes

| [`OfflineLipSync`](#cutan.audio.OfflineLipSync)(\*[, char_to_viseme])             | Default lip-sync provider: deterministic char-to-viseme mapping.   |
|---------------------------------------------------------------------------------------------------|--------------------------------------------------------------------|
| [`RhubarbLipSync`](#cutan.audio.RhubarbLipSync)(\*[, binary_path, language, ...]) | Wrap the rhubarb CLI.                                              |
| [`StaticWordTimings`](#cutan.audio.StaticWordTimings)(words, \*[, label])            | A `WordTimingProvider` over a fixed list of timings.               |
| [`WhisperLipSync`](#cutan.audio.WhisperLipSync)(\*[, model_size, device, ...])    | faster-whisper word timestamps → visemes.                          |
| [`WordTimingsLipSync`](#cutan.audio.WordTimingsLipSync)(provider, \*[, ...])          | `LipSyncProvider` driven by a `WordTimingProvider`.                |

### *class* cutan.audio.OfflineLipSync(, char_to_viseme=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Default lip-sync provider: deterministic char-to-viseme mapping.

Implements the `LipSyncProvider` protocol.

### *class* cutan.audio.RhubarbLipSync(, binary_path=None, language='en', recognizer=None, timeout_s=60.0)

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

#### *property* uses_dialog_file *: [bool](https://docs.python.org/3/builtins/functions.html#bool)*

Whether the chosen recognizer reads a transcript at all.

### *class* cutan.audio.StaticWordTimings(words, , label='static')

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A `WordTimingProvider` over a fixed list of timings.

### *class* cutan.audio.WhisperLipSync(, model_size='tiny', device='cpu', compute_type='int8', char_to_viseme=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

faster-whisper word timestamps → visemes.

Implements the `LipSyncProvider` protocol. The model is lazy-loaded on
the first call (subsequent calls in the same process reuse the instance
via the class-level `_model` cache).

#### emits_word_timings *: [bool](https://docs.python.org/3/builtins/functions.html#bool)* *= True*

Whisper aligns from words, so the track carries them (an#96).

### *class* cutan.audio.WordTimingsLipSync(provider, , char_to_viseme=None, convention='rhubarb', rest_viseme='X', min_gap_for_rest=0.2)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

`LipSyncProvider` driven by a `WordTimingProvider`.

Skips transcription entirely. Use this when the caller already has
authoritative word timings (e.g. from a separate lyric-alignment
pipeline).

* **Parameters:**
  * **provider** (`WordTimingProvider`) – any `WordTimingProvider`.
  * **char_to_viseme** ([`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)] | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – optional override of the character→viseme code
    mapping; defaults to the one shared with
    [`OfflineLipSync`](#cutan.audio.OfflineLipSync) / [`WhisperLipSync`](#cutan.audio.WhisperLipSync).
  * **convention** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – declared viseme convention string for the produced
    track. Defaults to `"rhubarb"` for compatibility with the
    existing cutout adapter.
  * **rest_viseme** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – code emitted in silent gaps. Defaults to
    `_REST_VISEME`.
  * **min_gap_for_rest** ([`float`](https://docs.python.org/3/builtins/functions.html#float)) – minimum inter-word silence (seconds) before
    we insert a rest keyframe. Defaults to `0.20`.

#### emits_word_timings *: [bool](https://docs.python.org/3/builtins/functions.html#bool)* *= True*

Built from words, so the track carries them (an#96).

### cutan.audio.offline_factory(\*\*\_)

The deterministic char-to-viseme provider (the default).

* **Return type:**
  [`OfflineLipSync`](cutan.audio.offline_lipsync.html.md#cutan.audio.offline_lipsync.OfflineLipSync)

### cutan.audio.rhubarb_factory(, language='en', \*\*\_)

Rhubarb Lip Sync (needs the `rhubarb` binary); `language` picks its recognizer.

* **Return type:**
  [`RhubarbLipSync`](cutan.audio.rhubarb_lipsync.html.md#cutan.audio.rhubarb_lipsync.RhubarbLipSync)

### cutan.audio.whisper_factory(\*\*\_)

Word timings from Whisper, distributed over the mouth shapes.

* **Return type:**
  [`WhisperLipSync`](cutan.audio.whisper_lipsync.html.md#cutan.audio.whisper_lipsync.WhisperLipSync)

### Modules

| [`injectable_lipsync`](cutan.audio.injectable_lipsync.html.md#module-cutan.audio.injectable_lipsync)   | Lip-sync provider that consumes pre-computed word timings.                      |
|-------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------|
| [`offline_lipsync`](cutan.audio.offline_lipsync.html.md#module-cutan.audio.offline_lipsync)         | OfflineLipSync — deterministic transcript → viseme track.                       |
| [`rhubarb_lipsync`](cutan.audio.rhubarb_lipsync.html.md#module-cutan.audio.rhubarb_lipsync)         | RhubarbLipSync — calls the rhubarb-lip-sync binary for phoneme-aligned visemes. |
| [`whisper_lipsync`](cutan.audio.whisper_lipsync.html.md#module-cutan.audio.whisper_lipsync)         | WhisperLipSync — faster-whisper word timestamps → viseme keyframes.             |
