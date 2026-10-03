# Changelog

## 2026-10-03

- **The rig presets move here from `an.motion`** (an#322): `nod`, `point`, `turn`, `face_toward`, `walk`, `waddle` and `speech_pulse`, with their defaults and the walk's limb names, are `cutan.motion`; the rig-free presets stay in `an.motion`. `cutan.motion.PRESETS` (the core's and the genre's) is the table a `play` resolves in. Moved verbatim: no preset expands differently, so no pixel moves. `an`'s preset tests moved with them (`tests/test_motion_presets.py`).

## 2026-10-02

- **The cut-out genre moves here from `an`** (an#225): characters, expression, impacts, the cut-out compile passes and lowering, lip-sync providers, the style lint and the character analyser; the mouth and eye visuals as a runtime script; the corpus, goldens, examples, demos and skills. Registered through the `an.genres` entry point; the `an` side keeps warning aliases at the old paths. Publishing is on.
- Scaffold: the `cutan` package (persisted identifiers, reserved `an.genres` entry-point name), README, CLAUDE.md, wads stub CI with publishing off until the first module moves (an#225).
