# cutan.audio.offline_lipsync

OfflineLipSync — deterministic transcript → viseme track. No network, no binary.

The default lip-sync provider for `an`. Maps each meaningful character of the
transcript to a Rhubarb-convention viseme letter (A–H + X), then distributes
keyframes evenly across the audio’s duration. Repeated visemes get collapsed
into a single keyframe so the mouth doesn’t “stutter” on long vowel runs.

Crude but visible. Use `RhubarbLipSync` for real phoneme alignment once
you’ve installed the Rhubarb binary.

A clip that knows its timings is followed instead of spread: its phones first
(`AudioClip.phones`, a take timed by a forced aligner, an#491: each phone’s own
mouth shape, [`cutan.audio.phones`](cutan.audio.phones.html.md#module-cutan.audio.phones)), else its words (`AudioClip.words`,
an#490: each word’s letters over its span).

```pycon
>>> from an.audio.tts import AudioClip
>>> ls = OfflineLipSync()
>>> track = ls.align(AudioClip(duration=1.0, transcript="hello"), "hello")
>>> track.convention
'rhubarb'
>>> track.duration
1.0
>>> len(track.visemes) >= 2
True
```

### Functions

| [`clip_words`](#cutan.audio.offline_lipsync.clip_words)(audio)   | The word timings `audio` carries (`AudioClip.words`, a recorded take imported with a timed transcript — an#490), as a list; `None` when it has none or when the core predates the field.   |
|----------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|

### Classes

| [`OfflineLipSync`](#cutan.audio.offline_lipsync.OfflineLipSync)(\*[, char_to_viseme, ...])   | Default lip-sync provider: deterministic char-to-viseme mapping.   |
|----------------------------------------------------------------------------------------------|--------------------------------------------------------------------|

### *class* cutan.audio.offline_lipsync.OfflineLipSync(\*, char_to_viseme=None, phone_to_viseme=<function phone_viseme>)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Default lip-sync provider: deterministic char-to-viseme mapping.

Implements the `LipSyncProvider` protocol.

#### repeatable *: [bool](https://docs.python.org/3/builtins/functions.html#bool)* *= True*

`an cache gc`
may re-make a missing track in memory (an#311, cutan#29).

* **Type:**
  A pure function of the transcript, and nothing is billed

### cutan.audio.offline_lipsync.clip_words(audio)

The word timings `audio` carries (`AudioClip.words`, a recorded take
imported with a timed transcript — an#490), as a list; `None` when it has
none or when the core predates the field.

```pycon
>>> clip_words(AudioClip(duration=1.0)) is None
True
```

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`float`](https://docs.python.org/3/builtins/functions.html#float), [`float`](https://docs.python.org/3/builtins/functions.html#float)]] | [`None`](https://docs.python.org/3/builtins/constants.html#None)
