# scene.md: the film

`scene.md` is Markdown with fenced YAML blocks. Prose between the blocks is kept and ignored by the engine: use it for the shot's description, written for a human. The complete, validated example is `examples/the-umbrella/scene.md`.

```
# <Title>                         a level-1 heading: the film's title
<a sentence or two of prose>
```yaml meta  ...```              the film's settings (exactly one)
## Shot <id> (cutout)             one section per shot, in order
<prose: what happens>
```yaml shot ...```               length, camera, transition, viewpoint (scene-space.md)
```yaml entities ...```           what is in the shot
```yaml actions ...```            what moves, and when
```dialogue ...```                who says what
```

Shot ids are short, lowercase, unique words (`title`, `arrival`, `close_mara`). Write each action and entity as one line of YAML flow mapping (`{kind: set, target: ..., ...}`); it keeps the file readable.

## The `meta` block

```yaml meta
title: The Umbrella
fps: 24
resolution: {width: 1280, height: 720}
default_renderer: cutout
closing_transition: {kind: fade, duration: 1.0, color: "#000000"}
```

| key | meaning |
|---|---|
| `title` | the film's title |
| `duration` | leave it out, EXCEPT when a shot enters with a `dissolve` or a `wipe`: then write the film's real length, the sum of the shot durations minus each dissolve's and wipe's duration (they overlap two shots). Give transitions whole-frame lengths (at 24 fps: 0.25, 0.5, 0.75, 1.0) so the sum comes out exact |
| `fps` | frames per second: 24 is filmic, 30 the default; a named style sets its own |
| `resolution` | `{width, height}`; 1280x720 renders about twice as fast as 1920x1080 and is right for drafts |
| `default_renderer` | always `cutout` here |
| `step_hz` | optional: moves update this many times a second ("on twos" is 12 at 24 fps): the jerky South Park look. Leave it out for smooth motion |
| `default_easing` | optional: the curve of every move that names none: `linear`, `ease_in_out` (the default), `ease_out`, `step`, ... (the easings are listed below this table) |
| `style_pack` | optional: the name of a named style (`south_park`, ...) or of a pack in `assets/styles/` |
| `closing_transition` | optional: `{kind: fade, duration: 1.0, color: "#000000"}` fades the end of the film |
| `captions` | optional: `{}` burns subtitles in and writes an `.srt` |
| `notes` | optional free text |

Easings you may name: `linear`, `ease_in`, `ease_out`, `ease_in_out`, `step`, `ease-in`, `ease-out`, `ease-in-out` (CSS), `smooth`, `there_and_back`, `wiggle`, `lingering`, or a cubic-bezier as four numbers `[0.34, 1.56, 0.64, 1.0]` (that one overshoots: a springy pop).

## The `shot` block

```yaml shot
duration: 9.0
camera: {move: hold}
transition: {kind: fade, duration: 0.6, color: "#000000"}
```

- `duration`: seconds. Typical shots run 2 to 10 s; let a style's shot length guide you.
- `camera`: one of
  - a named move: `{move: hold}` (still), `push_in` (slow zoom to 1.25x over the shot), `pull_out` (to 0.8x), `zoom_in` (to 1.5x), `zoom_out` (to 0.7x), `pan_left`, `pan_right` (a third of the frame), `tilt_up`, `tilt_down`;
  - explicit keys: `{keys: [{at: 0, x: 0}, {at: 3.0, x: 200, zoom: 1.2, easing: ease_in_out}]}`: `at` in shot seconds, `x`/`y` the camera position in pixels (`+x` moves the camera right, so the picture slides left), `zoom`, `rotation` (radians);
  - a follow: `{follow: {target: teo}}` keeps a walking character where it started in frame;
  - a shake on top of any of them: `{move: hold, shake: [{at: 1.2, duration: 0.4}]}` (an impact).
  A camera move must not show past the edge of the set: give planes enough `size`, or move less (`an validate` warns).
- `viewpoint`: the name of a viewpoint from the ` ```yaml world ` block, or an inline one (`{subject: paul, size: close_up}`): the shot is a camera onto the scene's space, and its entities are placed for you (`scene-space.md`). Leave it out for a hand-placed shot.
- `transition`: how this shot is **entered** (not on the first shot): `{kind: fade, duration: 0.6, color: "#000000"}` dips through a colour; `dissolve` overlaps the two shots, and `wipe` (with `direction: left|right|up|down`) overlaps them behind a moving edge: both make the film shorter by their duration (write the meta `duration`, above); leave it out for a hard cut.

## The `entities` block

Everything visible in the shot, back to front: **later entries draw in front.**

```yaml entities
- {kind: environment, id: set, store: environments, ref: bus_stop}
- {kind: character, id: mara, store: characters, ref: mara, stage: {at: [180, 200], scale: 1.0}}
- {kind: prop, id: umbrella, store: props, ref: umbrella, stage: {at: [-112, 118], scale: 0.6}}
```

| kind | store | ref | notes |
|---|---|---|---|
| `environment` | `environments` | a folder under `assets/environments/`, or a built-in preset: `park`, `indoor`, `night`, `sunset`, `default` | one per shot, first in the list |
| `character` | `characters` | a name from `cast.sh` or a folder under `assets/characters/` | `stage: {at: [x, y], scale: s}`: `at` is where the feet stand |
| `prop` | `props` | a folder under `assets/props/` | drawn props, text (titles, labels) and paths (arrows, lines) |

- `id` is the name actions use; it is usually the same as `ref`. Two entities from one ref need two ids (`label_west`, `label_east`).
- `overrides` changes a stored document for this shot only: `{kind: prop, id: west, store: props, ref: label, overrides: {text: West}}` reuses one label style with different words.
- `stage: {after: set/shelter}` draws an entity right after a named plane of the environment (between two planes) instead of in list order.
- Coordinates: pixels from the frame centre, y DOWN. At 1280x720, x runs -640..640 and y -360..360. Pixels do not rescale with the resolution: the same numbers fill more of a 720p frame than of a 1080p one.

## The `actions` block

Every action has a `kind`, a `target` (an entity id, or a part path such as `mara/head` or `teo/arm_r`) and a time: `at` for an instant, `start` for something that lasts (both in seconds from the start of the shot).

| kind | shape | does |
|---|---|---|
| `set` | `{kind: set, target: teo, property: view, value: side, at: 0.0}` | jumps a property to a value at an instant, and holds it |
| `tween` | `{kind: tween, target: title/word_0, property: alpha, from: 0.0, to: 1.0, duration: 0.6, start: 0.4, easing: ease_out}` | moves a property smoothly; `from` is optional (it starts from wherever the property is), `easing` too |
| `play` | `{kind: play, target: teo, animation: walk, args: {distance: 560}, start: 0.3}` | plays a named move (a motion preset, or an animation the character declares, such as `idle_breath` or `blink`); `args` are the preset's parameters (`references/characters.md`), `duration` stretches it, `speed` divides it |
| `expression` | `{kind: expression, target: mara, preset: sad, intensity: 0.6, axes: {gaze_x: -0.6}, start: 1.0, duration: 3.0}` | holds a face: a preset, scaled by `intensity` (0 to 1), plus or instead of raw `axes`; without `duration` it holds to the end of the shot |

Properties a `set` or `tween` may move:

- `x`, `y` (pixels; absolute positions, not offsets), `rotation` (radians, clockwise), `scale_x`, `scale_y`, `alpha` (0 hidden, 1 shown; it fades the whole entity and its parts), `skew_x`, `skew_y`;
- `tint`: a colour `"#rrggbb"` multiplied over the art (`"#000000"` makes a silhouette, `"#ffffff"` is no tint);
- on a character: `view` (`front`, `three_quarter`, `side`, `back`), and any swap set the character declares (`hands`, ...);
- on a path prop: `trim_end`, `trim_start` (0 to 1: a draw-on);
- on a text prop with `counter`: `value`; with `texts`: `text` (a key of `texts`).

Rules:

- **A property holds its rest value until its first action.** A title that fades in needs `{kind: set, ..., property: alpha, value: 0.0, at: 0.0}` first, or it shows from frame one.
- **A `tween` without `from` starts from the value at that moment**, so a chain of `to`-only tweens is continuous: `set x -800`, then `tween x to 0` walks in from the left.
- **Keep every action inside its shot** (`start` plus its length at most the shot's `duration`). The validator checks this only for dialogue, so do the arithmetic: a move that runs past the cut is simply cut off.
- **`alpha` on a character fades all of it.** To hide a face in a turn, use the view, never `alpha` on face parts.
- **A looping animation** (`idle_breath`) without a `duration` runs to the end of the shot.
- Grouping is allowed (`{kind: sequence, children: [...]}`, `parallel`, `delay`, `loop`), but single lines with `start:` are easier to read and to change. Prefer them.

## The `dialogue` block

````
```dialogue
teo [happy] (at 3.6): Evening! Is this the stop for the number nine?
mara [skeptical] (pause 0.5): It was. Until about an hour ago.
narrator {warm}: Some evenings are longer than others.
```
````

One line per line of speech: `speaker [emotion intensity] {delivery cues} (timing): words`. Everything between the speaker and the colon is optional, in any order.

- `speaker`: a character id in the shot (its lips move), or any other name, such as `narrator` or a character who is off screen in this shot (heard, not seen).
- `[emotion]`: one of `neutral, happy, sad, angry, surprised, afraid, disgusted, thinking, skeptical, amused`, optionally with an intensity: `[angry 0.6]`. It moves the brows, lids and mouth for the line. Anything else is an error.
- `{cues}`: delivery for an expressive voice: `{whispers}`, `{sighs, annoyed}`, `{deadpan}`, `{laughs}`. Never spoken, never captioned.
- `(timing)`: `(pause 1.5)` waits that long after the previous line ends; `(at 3.0)` starts the line at 3.0 s into the shot. Only timing goes in parentheses before the colon.
- Lines follow each other with no gap unless timed. Without real voices the pipeline estimates a line's length from its words; real speech is longer than it looks on the page, so leave a second or two of air at the end of a shot that has dialogue.
- One delivery per line: a setup and its punchline are two lines.
- Text on screen (captions) uses the built-in face: no em dash, no accented letters if captions are on.

## Staging arithmetic (1280x720)

- Floor line: y about 200. A character standing there at scale 1 reaches y 200 - 264 = -64 (regular build). Keep `y - height x scale - hop height` above -360, and allow for the camera's zoom (`push_in` ends at 1.25x about the frame centre).
- Two-shot: scale 1.0 to 1.4, x = ±180 to ±250. Three across: x = -350, 0, 350 at scale 1.
- Close single: scale 2.6 to 3.0 at y 600 to 700 (the feet far below the frame) and x near 0: the face fills the upper half.
- A character entering from off screen starts at |x| > 640 + its half width (about 760 at scale 1.1).
- An eye on a factory character is about 9 px wide at scale 1: blinks and brow moves read only from scale 2 up.

## Continuity across cuts

Every shot is compiled alone, so:

- A character in consecutive shots must end one shot and start the next with the same `stage.at` and scale, or the next shot opens with `set`s of `x`, `y`, `scale_x` and `scale_y` at `at: 0.0` to say the jump is deliberate (a cut to a close-up, then back). See `regret` and `offer` in the example.
- A view and a left-facing mirror hold for their shot only: repeat `{kind: set, target: mara, property: view, value: three_quarter, at: 0.0}` and `{kind: set, target: mara, property: scale_x, value: -1.0, at: 0.0}` (minus the stage scale) at the top of the next shot.
- An expression holds only for its shot.
