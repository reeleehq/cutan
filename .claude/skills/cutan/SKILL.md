---
name: cutan
description: Use when making a cut-out animated character video with `an`: rigged characters, faces and expressions, lip-sync, turning and facing, motion, impacts, and named cut-out styles (South Park, OverSimplified, Kurzgesagt, Gilliam, Reiniger, Norstein). Triggers on "make a character", "an character new", "lip-sync", "expression", "turn around", "walk", "cutout", "in the style of", or any scene with a `character` entity.
---

# cutan: cut-out animation for `an`

`cutan` is the cut-out genre of `an` (`pip install "an[cutout]"`): rigged 2D characters drawn by the stage engine, faces and expressions, lip-sync visemes, swap sets and views, impacts (timing ground truth), and named cut-out styles. `an` finds it through the `an.genres` entry point and loads it with `an.genres.load()` (the CLI and `an.load(project)` do). The scene format, the project layout, the assets recipe and rendering are the `an` skill's; this one holds what is specific to characters.

- **Start a production from the library, not from an earlier video:** `an init <project>` then `an library checkout <project> cutan:kit.<style>` checks out the style's starter set in one call (style pack, voices, cast, recurring sets and props), pinned in `assets.lock.json`. Today there is `cutan:kit.oversimplified`. Reuse anything else with `an library find --package cutan --style <style>` (or `--family cora`) and `an library checkout`. Never copy another project's `assets/`. A new reusable asset goes back with `an library publish`, and a new style's set with `an library kit`.
- **A character:** `an character new <name> --offline` (a built-in factory; `an character --help` for builds, head scale, DiceBear styles), `an character add-views <name>` (a turnaround), `an character validate <dir>` and `an character contract` (what an illustrator must deliver; skill `cutan-art-package`).
- **Actions on a character:** `play` (a descriptor animation or a motion preset such as `hop`, `nod`, `walk`, `turn`), `expression` (a preset or axes on the face), and the dialogue sugar `maya [happy]: Hi!` (at an intensity from 0 to 1: `maya [angry 0.4]: Fine.`, an#253). An expression whose preset has a mouth form (`happy`, `sad`, `angry`, ...) shows that form on the mouth while the character is silent, and a line under it speaks on the same set. This needs the character's `viseme@<form>` set: `an character new` makes `happy` and `sad`; add another with `an character mouths <name> --variants angry`. `an validate` and the compiler say when one is missing (an#253). Lines are lip-synced by the `offline` provider by default; `--lipsync rhubarb` or `whisper` choose another.
- **Styles:** the `cutan-style` skill applies a named style spec to a scene, renders, and lints the render against its targets (`python -m cutan.verify.style`).
- **Parts carved from a photo or a frame:** `cutan.carve` (`pip install "cutan[carve]"`): matte, neck cut, de-spill, normalise, and a prop folder whose descriptor carries the source; the `cutan-art-package` skill says how a carved part becomes a character's.
- **Impacts:** `an impacts clip` renders controlled test footage with exact ground truth.
- **Changing cutan itself:** `cutan/CLAUDE.md` and the `cutan-dev-*` skills.

## Turning and facing

An `an character new --offline` character carries a **turnaround** (an#197): a `view` swap set with keys `front` (its rest), `three_quarter`, `side` and `back`, drawn on the head and torso, plus a **pose per view** in the descriptor's `swap_poses`: the back hides the whole face, the profile hides the far eye and arm and slides the near eye and the mouth to the edge, the three-quarter shifts the face toward the facing side. `side` is drawn facing the **viewer's right**; a negative `scale_x` on the character root mirrors it to face left.

- **A turn:** `{kind: play, target: ned, animation: turn, args: {to: back}, start: 1.2}` — `scale_x` squashes through 0 and the view swaps at the edge-on midpoint (0.3 s by default; `duration` stretches it). Face a profile left with `args: {to: side, direction: left}`. **A turn played by name opens from where the timeline left the character** (an#203): the compiler reads the latest earlier `scale_x` on the entity (an earlier turn, or your own set/tween) and fills in `from_direction`, so a chain needs none by hand:

  ```yaml
  # front -> side (facing left) -> back, one character, one shot
  - {kind: play, target: ned, animation: turn, args: {to: side, direction: left}, start: 1.0}
  - {kind: play, target: ned, animation: turn, args: {to: back}, start: 2.5}
  - {kind: play, target: ned, animation: turn, args: {to: front}, start: 4.0}
  ```

  An explicit `from_direction` is kept, and `an validate` warns when it contradicts the timeline (the character would flip to the other side before turning). In Python, `cutan.motion.turn(...)` builds the tweens straight away and cannot see the timeline: pass `from_direction` there, or append the `PlayAction` instead.
- **A cut to a view** (no animation): `{kind: set, target: ned, property: view, value: side, at: 0.0}` — on the CHARACTER itself, which the compiler fans out to every slot the set draws on and poses the face; add `{kind: set, target: ned, property: scale_x, value: -1.4, at: 0.0}` (minus the stage scale) to face left.
- **A view holds for its shot only.** Every shot is compiled on its own (by design), so a character that turned its back at the end of one shot needs the `set … view back` (and any negative `scale_x`) again at `at: 0.0` in the next. `an validate` warns when a character ends a shot turned (a view other than `front`, or facing left) and the very next shot has it without setting its view (or its `scale_x`, for the facing) at 0, and gives the line; setting them there — to `front` and a positive `scale_x` for a deliberate reset — silences it.
- **Legs in profile:** the side view keeps both legs — the near one (`leg_r`) forward and drawn over the far one (`leg_l`), overlapping at the hip, feet apart — so a walk in profile has two legs to alternate (rotate `leg_l`/`leg_r` about the hip; the view's own splay is the rest your tweens override while they run). A character given its views before an#203 keeps the old one-leg profile until `an character add-views <name>` is run again (it rewrites the poses; the art is unchanged).
- **Looking at someone:** in Python, `cutan.motion.face_toward(shot, "ned", "carl", view="side", mall=mall)` returns the `turn` whose `direction` points at `carl`'s stage position.
- The face keeps working in every view: blinks and gaze run on the visible eye (a posed pupil still follows `gaze_x`), and lip-sync runs on the mouth in `front`, `three_quarter` and `side`; under `back` the mouth is hidden with the rest of the face, so a line said with the back turned is heard, not seen.
- **Never hide a face with `alpha` sets on `ned/head/left_eye`, `…/left_pupil`, `…/mouth` …** — that is what the view's pose is for, and a hand-set alpha on a face node overrides the view (authored wins) until the shot ends.
- **A face drawn differently in a view gets its own set, not a hide** (an#220): declare `eyelid@side` (`{OPEN, CLOSED}` → the profile's eye attachments, carried by the eye slots) and `viseme@side` (the profile's mouth shapes, on the mouth slot) and whenever `side` is in force the lids (blinks, expressions, a played `blink`) and the mouth (lines that start in it, and its rest between them) draw from them — the same for any view key (`eyelid@back` …). A view set lacking a key a line uses falls back to the plain set with a warning. A profile head carved with its eye and mouth baked in: carve them out as these per-view parts instead of hiding the face slots in `swap_poses` — **`an validate` warns when a line is spoken while the speaker's view hides its mouth** (alpha 0).
- **Characters made before an#202 (the turnaround) need `an character add-views <name>`** before any `view` set or `turn`; validate and compile both say so. A DiceBear or hand-drawn head cannot be turned by the factory; `an character contract` says how an illustrator declares views (`asset_sets.view` + `swap_poses`).

## Walking: gaits (an#224)

`{kind: play, target: ned, animation: walk, args: {distance: 320, gait: bounce}}`. A walk's **gait** is a locomotion method chosen by what the character affords; with none asked, it is `legs` when the rig has a leg pair (`leg_l`/`leg_r` with art) and `glide` otherwise. Ask for one with `args: {gait: …}`, or declare `"gait": "…"` in `character.json` for every walk of that character. A style can prefer another (its `policy:`, carried by the StylePack the scene names: South Park walks its legged figures with `bounce`), and so can a shot's `policy` field (in its ` ```yaml shot ` block, `policy: {locomotion: [loco.glide]}`); your `gait`, or one the character declares, always wins (the `cutan-style` skill, step 3).

| gait | needs | reads as |
|---|---|---|
| `legs` | legs | legs swing in profile, lift facing the camera; body bobs, arms counter-swing |
| `profile` | legs + a side view, in force when the walk starts | the four-pose profile walk (contact, down, passing, up); Reiniger |
| `shuffle` | legs | short quick steps, feet barely lifting |
| `hem` | legs (the two hem halves of a robe) | hem halves tilt as mirror images (the hem opens and closes), body sways; in profile they swing like legs |
| `waddle` | nothing | body rocks foot to foot and bobs (legs lift if any) |
| `hop` | nothing | the figure jumps every step |
| `bounce` | nothing | slides with a pronounced bob, feet flick: South Park |
| `glide` | nothing | slides, leaning into the move, gentle bob: robe figures, the legless default |
| `rock` | nothing | the old legless walk: body rocks about its origin and bobs |

- **Lengths scale with the figure**: `step_length`, `bob` and `hop_height` default to values for a figure at scale 1 and grow with its stage scale (a `scale: 2` character steps twice as far); pass them to set scene px outright. Every parameter and its per-gait default: `misc/docs/locomotion_gaits.md`.
- **A gait the character cannot do is never silent**: `an validate` warns (`cutout.walk_gait`) with the gait it will use instead and what to add (`profile` on a front-only character: `an character add-views <name>`); the compile records it, fatal under `--strict-assets`. `an character capabilities <name>` lists every gait that applies and why the others do not.
- A walk never turns the character: `turn` first, then `walk`.

### Addressing a character's parts

A target is `<entity id>/<node>` and the rigs are FLAT except the face, whose parts are children of the head: `ned/head/mouth`, never `ned/mouth`. The node paths each rig builds, for an entity with id `c` (generated from the code; `tests/test_skill_rig_paths.py` fails if this list drifts):

<!-- rig-paths:begin (generated by tests/test_skill_rig_paths.py; do not edit by hand) -->
| rig | node paths |
|---|---|
| `an character new --offline` (default) | `c`, `c/arm_l`, `c/arm_r`, `c/head`, `c/head/left_brow`, `c/head/left_eye`, `c/head/left_pupil`, `c/head/left_sclera`, `c/head/mouth`, `c/head/right_brow`, `c/head/right_eye`, `c/head/right_pupil`, `c/head/right_sclera`, `c/leg_l`, `c/leg_r`, `c/torso` |
| `new_character(..., gaze=False)` | `c`, `c/arm_l`, `c/arm_r`, `c/head`, `c/head/left_brow`, `c/head/left_eye`, `c/head/mouth`, `c/head/right_brow`, `c/head/right_eye`, `c/leg_l`, `c/leg_r`, `c/torso` |
| no descriptor (the placeholder rig) | `c`, `c/head`, `c/head/hair`, `c/head/left_brow`, `c/head/left_eye`, `c/head/mouth`, `c/head/right_brow`, `c/head/right_eye`, `c/left_arm`, `c/right_arm`, `c/torso` |
<!-- rig-paths:end -->

- **Rotation is radians, clockwise on screen** (y points down). An arm hangs from its shoulder, so a positive `rotation` swings its hand toward the viewer's LEFT: on an `an character new` character `arm_l` hangs on the viewer's left and `arm_r` on the right, so `+1.2` raises `arm_l` out to the side and swings `arm_r` across the chest, and `arm_r` is raised with a NEGATIVE angle (`-2.1` is up and out; alternate `-2.6`/`-2.2` for a wave — the same in front and three-quarter view). Another rig may put its arms the other way round: read the side off `an.motion.rest_pose(shot, "c/arm_r", mall=mall)["x"]` (negative is the viewer's left).
- `scale_x: -1` on the entity mirrors the whole character (a turn to face the other way): the arms swap sides on screen, and each is still raised by the same sign — `arm_l` with a positive angle, now on the viewer's right.

<!-- vocabulary:begin (generated by `python -m an.semantic.docs --write`; do not edit) -->
## Vocabulary (generated)

The names and methods the `cutout_animation` genre adds to the core vocabulary, with their versions and the spectrum levels each accepts (levels as in the `an` skill's vocabulary section, which lists the core names). `an.semantic.vocabulary()` returns the whole list as data. Regenerate with `python -m an.semantic.docs --write <this file> --owner cutout_animation`.

### Action kinds

| Name | Version | Levels | What it is |
|---|---|---|---|
| `play` | 1 | a | play a named animation (an action / animation clip) of the target entity's descriptor, falling back to a motion preset |
| `expression` | 1 | a | hold a facial expression (an expression-sheet preset) on a character |

### Entity kinds

| Name | Version | Levels | What it is |
|---|---|---|---|
| `character` | 1 | a | a rigged cut-out character: a skeleton of bones with slots, drawn by the stage engine; its nodes are stage nodes |

### Motion presets

| Name | Version | Levels | What it is |
|---|---|---|---|
| `pop_in` | 1 | a, b-name | Grow from nothing to full size, overshooting and settling (an entrance). |
| `hop` | 1 | a, b-name | Jump up by `height` scene pixels and land back where it started. |
| `shake` | 1 | a, b-name | Tremble side to side `cycles` times and come back to rest (on `x`). |
| `slide_in` | 1 | a, b-name | Whip in from `distance` pixels off to one side, overshoot, and settle. |
| `slide_out` | 1 | a, b-name | Exit `distance` pixels off to one side, accelerating (an exit). |
| `squash_stretch` | 1 | a, b-name | Squash (wide and short), stretch (narrow and tall), then settle. |
| `crawl` | 1 | a, b-name | An opening crawl: lay `target` on a plane tilted away, and slide it up and away. |
| `nod` | 1 | a, b-name | Dip the head `count` times (a rotation of `<target>/<part>`). |
| `point` | 1 | a, b-name | Swing an arm out to point, hold it, and lower it again. |
| `waddle` | 1 | a, b-name | A walk cycle for a rig with no legs to animate: rock and bob per step. |
| `turn` | 2 | a, b-name | Turn a character to the view `to` — the classic cut-out turn. |
| `walk` | 4 | a, b-name | Walk: the body travels on `x` while the gait moves it — legs that alternate, a hop, a bounce, a glide (an#214, an#224). |
| `speech_pulse` | 1 | a, b-name | Pulse a part on each syllable: speech carried without a mouth. |

### Expression presets

| Name | Version | Levels | What it is |
|---|---|---|---|
| `neutral` | 1 | a, b-name | the rest face: every axis at its neutral value |
| `happy` | 1 | a, b-name | expression-sheet preset: brow_angle_l +0.1, brow_angle_r +0.1, brow_height_l +0.2, brow_height_r +0.2, lid_open_l -0.2, lid_open_r -0.2; mouth form 'happy' |
| `sad` | 1 | a, b-name | expression-sheet preset: brow_angle_l +0.6, brow_angle_r +0.6, brow_height_l +0.3, brow_height_r +0.3, lid_open_l -0.3, lid_open_r -0.3; mouth form 'sad' |
| `angry` | 1 | a, b-name | expression-sheet preset: brow_angle_l -0.8, brow_angle_r -0.8, brow_height_l -0.6, brow_height_r -0.6, lid_open_l +0.1, lid_open_r +0.1; mouth form 'angry' |
| `surprised` | 1 | a, b-name | expression-sheet preset: brow_angle_l +0, brow_angle_r +0, brow_height_l +1, brow_height_r +1, lid_open_l +0.4, lid_open_r +0.4; mouth form 'surprised' |
| `afraid` | 1 | a, b-name | expression-sheet preset: brow_angle_l +0.5, brow_angle_r +0.5, brow_height_l +0.7, brow_height_r +0.7, lid_open_l +0.5, lid_open_r +0.5; mouth form 'afraid' |
| `disgusted` | 1 | a, b-name | expression-sheet preset: brow_angle_l -0.3, brow_angle_r -0.3, brow_height_l -0.3, brow_height_r -0.3, lid_open_l -0.4, lid_open_r -0.4; mouth form 'disgusted' |
| `thinking` | 1 | a, b-name | expression-sheet preset: brow_angle_l +0.3, brow_angle_r -0.1, brow_height_l +0.5, brow_height_r -0.2, lid_open_l -0.1, lid_open_r -0.1 |
| `skeptical` | 1 | a, b-name | expression-sheet preset: brow_angle_l +0, brow_angle_r -0.2, brow_height_l +0.6, brow_height_r -0.3, lid_open_l +0, lid_open_r -0.2 |
| `amused` | 1 | a, b-name | expression-sheet preset: brow_angle_l +0.05, brow_angle_r +0.05, brow_height_l +0.1, brow_height_r +0.1, lid_open_l -0.1, lid_open_r -0.1; mouth form 'happy' |

### Methods, by aspect

Default chains: **locomotion** `loco.legged_cycle` → `loco.glide`; **speech** `speech.mouth_chart` → `speech.pose_only`; **expression** `expr.full_face` → `expr.without_brows`. 
`an character capabilities <name>` says which apply to a character and what is missing for the rest.

| Aspect | Method | Spelled | Version | Requires | What it is |
|---|---|---|---|---|---|
| locomotion | `loco.legged_cycle` | `legs` | 2 | `limbs.legs` | a legged walk cycle: in profile the legs swing about the hip in opposition, facing the camera the stepping leg lifts; the arms swing against the legs |
| locomotion | `loco.glide` | `glide` | 2 | nothing | the figure slides, leaning into the move with a gentle bob; no limb moves (a robe figure, a ghost, a sack — the default for any figure without legs) |
| locomotion | `loco.profile_cycle` | `profile` | 2 | `limbs.legs`, `swap.view:side` | the four poses of a walk seen in profile (contact, down, passing, up): with a side or three-quarter view showing the legs swing about the hip in opposition and the body sinks after each contact and rises before the next; asked while another view shows, it walks as legs (Reiniger's silhouettes, any figure drawn side-on) |
| locomotion | `loco.shuffle` | `shuffle` | 2 | `limbs.legs` | the feet barely leave the ground: short, quick steps with little bob and arms close to the body (the old, the tired, the cautious) |
| locomotion | `loco.hem_sway` | `hem` | 2 | `limbs.legs` | a robe figure's walk: the leg slots are the two halves of the hem, which tilt about the hip as mirror images (the hem opens and closes) while the body sways and bobs facing the camera; in profile they swing like legs |
| locomotion | `loco.waddle` | `waddle` | 2 | nothing | the body rocks from foot to foot and bobs on each step; legs, if any, lift in turn (a penguin, a toddler, a squat figure) |
| locomotion | `loco.hop` | `hop` | 2 | nothing | the whole figure jumps on every step while it travels (a bird, a kangaroo, a gleeful character, anything drawable) |
| locomotion | `loco.bounce` | `bounce` | 2 | nothing | the body bobs on every step while it slides; legs, if any, only flick (the South Park walk) |
| locomotion | `loco.rock` | `rock` | 2 | nothing | no leg moves: the body rocks side to side and bobs once per step while it travels (a blob, a sack, anything drawable) |
| speech | `speech.mouth_chart` | `mouth_chart` | 1 | `face.mouth` | lip-sync on the character's mouth chart: the line's visemes swap the mouth drawings (the nine Rhubarb shapes, or the character's own set) |
| speech | `speech.pose_only` | `pulse` | 1 | nothing | no lip-sync: the head (or the body) pulses on each syllable, so a baked face or a mime still reads as speaking |
| expression | `expr.full_face` | `full_face` | 1 | `face.brows` | the expression acts with the whole face: the brows rise, knit and tilt, the lids open and close, the pupils move and the mouth takes the preset's form |
| expression | `expr.without_brows` | `without_brows` | 1 | nothing | the brows cannot be seen acting (covered, or not drawn): the lids, the gaze and the mouth form carry the expression |
<!-- vocabulary:end -->
