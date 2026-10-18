# Characters

Three ways to give the film a character, cheapest first. Use the first unless the writer asks for a look it cannot make.

1. **A factory character** (`cast.sh`): built from options (build, head size, hat, hair, colours). Fully rigged: lip-sync, blinks, gaze, expressions, a four-view turnaround, walking legs. Costs nothing.
2. **A factory character with redrawn parts**: run the factory, then replace some of its drawings (head, torso, arms, legs) with your own SVG on the same canvases. Keeps the rig and the face.
3. **A hand-drawn character**: a full art package (`assets/characters/<name>/`), for an illustrator. Expensive; describe it in `PRODUCTION.md` and let the pipeline owner commission it.

## 1. The factory: `cast.sh`

One command per character, run from the project root by the pipeline. Comments (`#`) above each line say who the character is. Only `an character ...` commands are allowed in this file.

```
# Teo: short and round, red cap, mustard jacket. Relentlessly cheerful.
an character new teo --offline --build squat --head-scale 1.2 --hat cap --hair-style curly --palette "skin=#f1c9a5,hair=#5a3a22,clothing=#d9a62e,accessory=#c0392b,leg=#3a4a6a" --mouth-variants happy,sad
```

Always write `--offline` (the deterministic, fully rigged factory). The options:

| option | values | notes |
|---|---|---|
| `NAME` | lowercase id, no spaces | the id scenes use: `teo` |
| `--build` | `regular` (264 px tall at scale 1), `tall` (312), `squat` (179: round body, short legs), `stick` (225: small blocky body, stick limbs) | the silhouette is the first thing that tells two characters apart |
| `--head-scale` | a number, 1.0 regular; 1.2 to 1.7 for cartoon heads | the head and the whole face together |
| `--hat` | `none`, `cap`, `beanie`, `bowler`, `bicorne` | worn above the brows, in the `accessory` colour |
| `--hair-style` | `peak` (default), `bald`, `bun`, `curly` | in the `hair` colour |
| `--hair-length` | `short` (default), `medium` (to the jaw), `long` (past the chin) | `bald` takes `short` |
| `--sash` | flag | a diagonal band across the torso, `accessory` colour |
| `--palette` | `"skin=#..,hair=#..,clothing=#..,leg=#..,accessory=#.."` | any subset; quote the whole value. Unset roles take a seeded colour |
| `--mouth-variants` | comma list of `happy`, `sad`, `angry`, `surprised`, `afraid`, `disgusted` | the mouth shapes the character's emotions use; default `happy,sad`. Include every mood its lines carry |
| `--voice-ref` | a key of `assets/voices/` | the voice document the character speaks with (`voices-and-looks.md`) |
| `--no-views` | flag | leaves out the turnaround (rarely wanted) |

More commands allowed in `cast.sh`, after a character's `new` line: `an character mouths <name> --variants angry` (adds mouth sets), `an character add-half-lid <name>`, `an character add-views <name>` and `an character add-gaze <name>` (the last three are already done for a new character; they matter only after `--no-views`). Nothing else is accepted: the pipeline refuses any other command or option.

Give every character a different combination of build, head scale, hat, hair and costume colour, so a silhouette tells them apart. Describe what each looks like and sounds like in `PRODUCTION.md`.

## Faces and expressions

An `expression` action, or a dialogue `[emotion]`, holds a face. The presets:

| preset | reads as |
|---|---|
| `neutral` | the rest face |
| `happy` | brows up, eyes soften, smiling mouth |
| `sad` | inner brows up, lids lowered, down-turned mouth |
| `angry` | brows knit down, a half-lid glare, frowning mouth |
| `surprised` | brows high, eyes wide (factory eyes cannot open wider: a warning), open mouth |
| `afraid` | brows up and worried, eyes wide (same warning), tense mouth |
| `disgusted` | brows down, a squint, a sour mouth |
| `thinking` | one brow up, one down |
| `skeptical` | one brow raised, one eye narrowed |
| `amused` | a soft version of happy |

`intensity` (0 to 1) scales the brows and lids: below about 0.5 nothing reads at full-figure framing. `axes` set individual controls, each from -1 to 1: `brow_height_l`, `brow_height_r` (+ raises), `brow_angle_l`, `brow_angle_r` (+ worried, - furrowed), `lid_open_l`, `lid_open_r` (- closes; -0.35 to -0.85 is a squint), `gaze_x` (+ looks to the viewer's right; on a mirrored character, one with a negative `scale_x`, + looks to the viewer's LEFT), `gaze_y` (+ looks down). Example: `{kind: expression, target: mara, preset: sad, intensity: 0.6, axes: {gaze_x: -0.6}}`. The gaze is what sells a reaction: point it at whoever caused it.

Blinks and small eye movements happen on their own; you do not author them.

## Turning and facing

Every factory character has four views: `front` (rest), `three_quarter`, `side` (a profile facing the **viewer's right**) and `back` (the face hidden).

- **A turn on screen:** `{kind: play, target: mara, animation: turn, args: {to: three_quarter, direction: left}, start: 5.6}`. `to` is the view; `direction: left` faces it to the viewer's left (by mirroring). It takes 0.3 s (`duration` changes that). Turns chain: each starts from where the previous left the character.
- **Start a shot already turned:** `{kind: set, target: teo, property: view, value: side, at: 0.0}`, and to face left as well, `{kind: set, target: teo, property: scale_x, value: -1.1, at: 0.0}` (minus the character's stage scale).
- **A view holds for its shot only.** Set it again at `at: 0.0` in the next shot.
- Lip-sync works in front, three-quarter and side; a line said with the back turned is heard, not seen.
- Never hide face parts with `alpha` to fake a view.

## Walking

`{kind: play, target: teo, animation: walk, args: {distance: 560}, start: 0.3}` moves the character 560 px to the right from where it stands (negative goes left; or `to_x: 120` to an absolute x). A step is 80 px times the character's stage scale (rounded to whole steps) and takes 0.4 s, so 560 px at scale 1.1 is 6 steps, 2.4 s (`shuffle`: 40 px, 0.3 s); `steps` and `step_s` override. With `to_x` and no `steps`, a walk always takes 6 steps (2.4 s) whatever the distance: prefer `distance`, or give `steps`. A walk never turns the character: set or `turn` its view first (a profile walk reads best).

`args: {gait: ...}` picks the walk:

| gait | reads as |
|---|---|
| `legs` (default for a character with legs) | legs swing in profile, lift facing the camera; arms counter-swing |
| `profile` | the four-pose profile walk; needs the `side` view in force |
| `shuffle` | short, quick steps, feet barely lifting: the old, the tired, the cautious |
| `waddle` | rocks foot to foot: a toddler, a penguin |
| `hop` | jumps on every step: glee |
| `bounce` | slides with a bob, feet flick: the South Park walk |
| `glide` | slides, leaning in: robes, ghosts |
| `rock` | rocks side to side: a sack, a blob |

## Motion presets

Played by name with `{kind: play, target: <id or part>, animation: <preset>, args: {...}, start: <s>}`. Distances are scene pixels, angles radians, times seconds. Each preset starts from the pose the character has at that moment.

- `hop` (whole character): a jump of `height` px. `shake`: a tremble. `pop_in`: grows from nothing (an entrance; also good for a prop appearing). `slide_in` / `slide_out`: whips in from / out to a side. `squash_stretch`: a cartoon bounce.
- `nod`: dips the head `count` times. Target the character (`part: head` is the default).
- `point`: swings an arm out, holds, lowers. **Target the arm**: `teo/arm_r` with a negative `angle` (`-1.3`), `teo/arm_l` with a positive one. To raise an arm and keep it up, use a tween instead: `{kind: tween, target: teo/arm_r, property: rotation, to: -1.3, duration: 0.3, start: 1.0}` (`-2.1` is up and out, `-2.6`/`-2.2` alternated is a wave).
- `turn`, `walk`: above. `waddle`: an old-style rocking walk. `speech_pulse`: the head pulses on syllables (for a character with no mouth). `crawl`: a Star Wars text crawl, on a text prop.
- Characters also declare `idle_breath` (a slow breathing loop: `{kind: play, target: mara, animation: idle_breath}` keeps a waiting character alive) and `blink`.

Every parameter, with its default (generated from the code; never pass one that is not listed):

<!-- presets:begin (generated by tests/test_production_pack_skill.py; do not edit by hand) -->
| preset | parameters (`args`) and defaults |
|---|---|
| `pop_in` | `duration` = `0.45`, `easing` = `(0.34, 1.56, 0.64, 1.0)` |
| `hop` | `height` = `40.0`, `duration` = `0.5` |
| `shake` | `amplitude` = `8.0`, `duration` = `0.4`, `cycles` = `3` |
| `slide_in` | `from_side` = `'left'`, `distance` = `600.0`, `duration` = `0.35`, `easing` = `(0.34, 1.56, 0.64, 1.0)` |
| `slide_out` | `to_side` = `'right'`, `distance` = `600.0`, `duration` = `0.35`, `easing` = `'ease_in'` |
| `squash_stretch` | `amount` = `0.2`, `duration` = `0.36` |
| `crawl` | `distance` = `2400.0`, `duration` = `30.0`, `start`, `tilt` = `0.96`, `perspective` = `1.0`, `fade` = `(700.0, 1500.0)`, `y`, `easing` = `'linear'` |
| `nod` | `part` = `'head'`, `angle` = `0.18`, `duration` = `0.5`, `count` = `2` |
| `point` | `angle` = `-1.3`, `raise_duration` = `0.25`, `hold` = `0.6`, `easing` = `(0.34, 1.56, 0.64, 1.0)` |
| `waddle` | `steps` = `4`, `step_duration` = `0.3`, `angle` = `0.1`, `lift` = `6.0`, `travel` = `0.0` |
| `turn` | `to` = `'back'`, `direction` = `'right'`, `from_direction`, `duration` = `0.3`, `view_set` = `'view'`, `step_hz` |
| `walk` | `to_x`, `distance`, `direction`, `steps`, `step_s`, `step_length`, `stride`, `lift`, `bob`, `arm_swing`, `rock`, `hem_tilt`, `hop_height`, `lean`, `view`, `gait`, `legs`, `arms`, `scale` |
| `speech_pulse` | `beats` = `(0.0,)`, `strength` = `0.06`, `part` = `'head'`, `attack` = `0.06`, `release` = `0.1` |
<!-- presets:end -->

## Part paths

A target is `<entity id>/<part>`. On a factory character the face parts are children of the head. The paths each rig builds, for an entity with id `c` (generated from the code):

<!-- rig-paths:begin (generated by tests/test_production_pack_skill.py; do not edit by hand) -->
| rig | node paths |
|---|---|
| `an character new --offline` (default) | `c`, `c/arm_l`, `c/arm_r`, `c/head`, `c/head/left_brow`, `c/head/left_eye`, `c/head/left_pupil`, `c/head/left_sclera`, `c/head/mouth`, `c/head/right_brow`, `c/head/right_eye`, `c/head/right_pupil`, `c/head/right_sclera`, `c/leg_l`, `c/leg_r`, `c/torso` |
| `new_character(..., gaze=False)` | `c`, `c/arm_l`, `c/arm_r`, `c/head`, `c/head/left_brow`, `c/head/left_eye`, `c/head/mouth`, `c/head/right_brow`, `c/head/right_eye`, `c/leg_l`, `c/leg_r`, `c/torso` |
| the default rig with `"nesting": "bones"` (an#340) | `c`, `c/leg_l`, `c/leg_r`, `c/torso`, `c/torso/arm_l`, `c/torso/arm_r`, `c/torso/head`, `c/torso/head/left_brow`, `c/torso/head/left_eye`, `c/torso/head/left_pupil`, `c/torso/head/left_sclera`, `c/torso/head/mouth`, `c/torso/head/right_brow`, `c/torso/head/right_eye`, `c/torso/head/right_pupil`, `c/torso/head/right_sclera` |
| no descriptor (the placeholder rig) | `c`, `c/head`, `c/head/hair`, `c/head/left_brow`, `c/head/left_eye`, `c/head/mouth`, `c/head/right_brow`, `c/head/right_eye`, `c/left_arm`, `c/right_arm`, `c/torso` |
<!-- rig-paths:end -->

Use the first row: a character from `cast.sh` is `an character new --offline`. Arms hang from the shoulder, legs from the hip, the head from the neck: a `rotation` turns a part about that joint, and is absolute (`to: 0` straightens it).

## 2. Redrawing factory parts

When the writer wants a look the options cannot make (a beard, a crown, a robe, a non-human head), keep the factory rig and redraw parts:

1. Add the character's `an character new ... --offline` line to `cast.sh` as usual.
2. If you can run code: `pip install cutan`, run that line yourself, and open the generated `assets/characters/<name>/parts/*.svg`. Each part's `viewBox` and `width`/`height` are its canvas, and they differ with the build and head scale (a `tall` torso is 224x320, a `squat` one 300x220; a head is `viewBox="0 0 80 80"` drawn at 285 to 342 px), so read them from the files, never from memory. An arm hangs from the top centre of its canvas (the shoulder) to the hand at the bottom; a leg from the hip at the top. If you cannot run code, ask the pipeline owner for the generated folder before drawing.
3. Draw the replacement **on the same canvas**, with the joint where the original has it (the neck at the bottom of the head, the shoulder at the top of the arm). Keep the face clear: eyes, brows and mouth are separate parts drawn on top of the head, so the head drawing has no features of its own. Redraw the matching view drawings too (`head_side.svg`, `head_back.svg`, `head_three_quarter.svg`, `torso_*.svg`) or the turnaround will show the old look.
4. Keep each file's root `<svg ...>` tag exactly as the factory wrote it (its `width`/`height` set the part's size on screen and may differ from its viewBox: a head is `viewBox="0 0 80 80" width="285"`). Change only what is inside.
5. Ship only the redrawn files, under `assets/characters/<name>/parts/` in the pack (no `character.json`: that folder then means "redrawn parts"), and list them in `PRODUCTION.md` ("teo: head and head_* redrawn with a beard"). The validator and the pipeline build the character from `cast.sh` first, then copy your parts over the factory's.

Colours in a redrawn part are yours: a style pack does not recolour them.

## What a factory character cannot do

- **Sit, kneel, bend an elbow or a knee**: each arm and leg is one drawing hung from its joint. Stage a seated character behind something (a counter, a table plate drawn in front of them) or keep them standing; describe a real sit in `PRODUCTION.md` as an art need.
- **Hold or carry a prop**: a prop does not follow a hand. Place it where the hand will be and keep that arm still while it shows.
- **Mirrored characters swap arms on screen**: with a negative `scale_x`, `arm_l` hangs on the viewer's RIGHT, still raised with a positive angle, and `arm_r` on the left with a negative one.

## 3. A hand-drawn character

A full art package is a folder `assets/characters/<name>/` holding `character.json` (bones, slots, skins, swap sets) and `parts/` (one drawing per piece: head, torso, two arms, two legs, eyes open and closed, brows, and nine mouth shapes `mouth_a` ... `mouth_h`, `mouth_x`). The exact contract comes from `an character contract`; an illustrator works from it and the pipeline owner validates the delivery with `an character validate`. Writing `character.json` by hand is error-prone: unless you can run the validator, do not attempt it. Instead, describe the character in `PRODUCTION.md` (silhouette, proportions, costume, which views are needed, which moods its lines use) as an art brief.
