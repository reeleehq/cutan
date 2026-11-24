# cutan.audio.whisper_lipsync

WhisperLipSync — faster-whisper word timestamps → viseme keyframes.

Phase 9. Bridges the gap between deterministic `OfflineLipSync` (twitchy,
char-distributed) and the system-binary-dependent `RhubarbLipSync`. Uses
`faster-whisper` to transcribe the rendered audio into word-level
timestamps, then distributes visemes within each word’s [start, end] span
based on the word’s letter→viseme mapping (collapsed-duplicates).

This gives ~75% of Rhubarb-quality lip-sync without any system binaries,
just a ~75 MB model download (cached after first use).

Trade-offs vs. OfflineLipSync:

- **Better**: timing is locked to actual word boundaries. Mouth holds shape
  through silent gaps between words instead of cycling through visemes.
- **Same**: viseme codes per phoneme are still our simple letter mapping;
  no IPA/ARPAbet awareness yet (that’s a future upgrade with cmudict).
- **Cost**: ~3–5 seconds CPU inference for a 10s clip on first call;
  subsequent calls in the same process re-use the cached model.

### Module Attributes

| [`ALIGN_VERSION`](#cutan.audio.whisper_lipsync.ALIGN_VERSION)   | Bump (`None` -> `"2"` -> ...) when how this provider aligns changes in a way a cached track must not survive: every key changes, and every take is re-aligned once.   |
|------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------|

### Classes

| [`WhisperLipSync`](#cutan.audio.whisper_lipsync.WhisperLipSync)(\*[, model_size, device, ...])   | faster-whisper word timestamps → visemes.   |
|--------------------------------------------------------------------------------------------------|---------------------------------------------|

### cutan.audio.whisper_lipsync.ALIGN_VERSION *: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None)* *= None*

Bump (`None` -> `"2"` -> …) when how this provider aligns changes in a
way a cached track must not survive: every key changes, and every take is
re-aligned once. `None` keeps the legacy key in the legacy configuration.

### *class* cutan.audio.whisper_lipsync.WhisperLipSync(\*, model_size='tiny', device='cpu', compute_type='int8', char_to_viseme=None, phone_to_viseme=<function phone_viseme>)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

faster-whisper word timestamps → visemes.

Implements the `LipSyncProvider` protocol. The model is lazy-loaded on
the first call (subsequent calls in the same process reuse the instance
via the class-level `_model` cache).

#### *property* cache_version *: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None)*

What re-keys this provider’s cached tracks (`an.audio.lipsync.
CACHE_VERSION_ATTR`, an#727): `None` (the bare `whisper` key every
existing track has) in the legacy configuration, else the model, the
compute type and any custom mapping, plus [`ALIGN_VERSION`](#cutan.audio.whisper_lipsync.ALIGN_VERSION).

So a change of model size no longer serves the other size’s tracks, and a
code change that must invalidate bumps [`ALIGN_VERSION`](#cutan.audio.whisper_lipsync.ALIGN_VERSION); neither
re-runs a take cached under the configuration it was made with (cutan#227).

```pycon
>>> WhisperLipSync().cache_version is None
True
>>> WhisperLipSync(model_size="base").cache_version
'base-int8'
```

#### emits_word_timings *: [bool](https://docs.python.org/3/builtins/functions.html#bool)* *= True*

Whisper aligns from words, so the track carries them (an#96).
