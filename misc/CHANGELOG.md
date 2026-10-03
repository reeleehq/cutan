# Changelog

## 2026-10-03

- **Locomotion gaits** (an#224, P10 of an#231): `walk` takes nine gaits, each a locomotion method with declared requirements — `legs`, `profile` (the four-pose profile cycle; needs `swap.view:side`), `shuffle`, `hem` (need `limbs.legs`), and `waddle`, `hop`, `bounce`, `glide`, `rock` (need nothing). The chain is `legs` → `glide`: a figure without legs now glides instead of rocking about its feet. Default lengths (`step_length`, `bob`, `hop_height`) scale with the figure's drawn scale (an#224's comment: `scale: 2` used to shuffle). `an validate` warns when a requested gait will not be used (`cutout.walk_gait`), naming what would enable it. `walk` is version 2. Classification: `misc/docs/locomotion_gaits.md`.

- **The rig presets move here from `an.motion`** (an#322): `nod`, `point`, `turn`, `face_toward`, `walk`, `waddle` and `speech_pulse`, with their defaults and the walk's limb names, are `cutan.motion`; the rig-free presets stay in `an.motion`. `cutan.motion.PRESETS` (the core's and the genre's) is the table a `play` resolves in. Moved verbatim: no preset expands differently, so no pixel moves. `an`'s preset tests moved with them (`tests/test_motion_presets.py`).

## 2026-10-02

- **The cut-out genre moves here from `an`** (an#225): characters, expression, impacts, the cut-out compile passes and lowering, lip-sync providers, the style lint and the character analyser; the mouth and eye visuals as a runtime script; the corpus, goldens, examples, demos and skills. Registered through the `an.genres` entry point; the `an` side keeps warning aliases at the old paths. Publishing is on.
- Scaffold: the `cutan` package (persisted identifiers, reserved `an.genres` entry-point name), README, CLAUDE.md, wads stub CI with publishing off until the first module moves (an#225).
