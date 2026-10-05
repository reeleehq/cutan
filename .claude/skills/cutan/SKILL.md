---
name: cutan
description: Use when making a cut-out animated character video with `an`: rigged characters, faces and expressions, lip-sync, turning and facing, motion, impacts, and named cut-out styles (South Park, OverSimplified, Kurzgesagt, Gilliam, Reiniger, Norstein). Triggers on "make a character", "an character new", "lip-sync", "expression", "turn around", "walk", "cutout", "in the style of", or any scene with a `character` entity.
---

# cutan: cut-out animation for `an`

`cutan` is the cut-out genre of `an` (`pip install "an[cutout]"`): rigged 2D characters drawn by the stage engine, faces and expressions, lip-sync visemes, swap sets and views, impacts (timing ground truth), and named cut-out styles. `an` finds it through the `an.genres` entry point and loads it with `an.genres.load()` (the CLI and `an.load(project)` do). The scene format, the project layout, the assets recipe and rendering are the `an` skill's; this one holds what is specific to characters.

- **Start a production from the library, not from an earlier video:** `an init <project>` then `an library checkout <project> cutan:kit.<style>` checks out the style's starter set in one call (style pack, voices, cast, recurring sets and props), pinned in `assets.lock.json`. Today there is `cutan:kit.oversimplified`. Reuse anything else with `an library find --package cutan --style <style>` (or `--family cora`) and `an library checkout`. Never copy another project's `assets/`. A new reusable asset goes back with `an library publish`, and a new style's set with `an library kit`.
- **A character:** `an character new <name> --offline` (a built-in factory; `an character --help` for builds, head scale, DiceBear styles), `an character add-views <name>` (a turnaround), `an character validate <dir>` and `an character contract` (what an illustrator must deliver; skill `cutan-art-package`).
- **Actions on a character:** `play` (a descriptor animation or a motion preset such as `hop`, `nod`, `walk`, `turn`), `expression` (a preset or axes on the face), and the dialogue sugar `maya [happy]: Hi!`. Lines are lip-synced by the `offline` provider by default; `--lipsync rhubarb` or `whisper` choose another.
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

`{kind: play, target: ned, animation: walk, args: {distance: 320, gait: bounce}}`. A walk's **gait** is a locomotion method chosen by what the character affords; with none asked, it is `legs` when the rig has a leg pair (`leg_l`/`leg_r` with art) and `glide` otherwise. Ask for one with `args: {gait: …}`, or declare `"gait": "…"` in `character.json` for every walk of that character.

| gait | needs | reads as |
|---|---|---|
| `legs` | legs | legs swing in profile, lift facing the camera; body bobs, arms counter-swing |
| `profile` | legs + a side view | the four-pose profile walk (contact, down, passing, up); Reiniger |
| `shuffle` | legs | short quick steps, feet barely lifting |
| `hem` | legs (the two hem halves of a robe) | hem halves tilt in turn, body sways |
| `waddle` | nothing | body rocks foot to foot and bobs (legs lift if any) |
| `hop` | nothing | the figure jumps every step |
| `bounce` | nothing | slides with a pronounced bob, feet flick: South Park |
| `glide` | nothing | slides, leaning into the move, gentle bob: robe figures, the legless default |
| `rock` | nothing | the old legless walk: body rocks about its feet |

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

