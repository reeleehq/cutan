# One world, many shots: the scene space

When several shots show one place (a two-shot and the close singles of a conversation; a car and the road behind it), do not place the characters in each shot by hand. Describe the place ONCE as a `world` and give each shot a `viewpoint` onto it. Every placement then follows from the world: Paul's close-up shows Jerry beside him because the world says Jerry is there; the steering wheel in Paul's hands keeps its size relative to him in every framing; the road's poles rush past at the speed the world says, and they are in the same places when the film cuts back to the two-shot. This needs `an` 0.1.244 or later (the release of reeleehq/an#513; the pipeline owner upgrades the connector); a shot without a `viewpoint` is placed by hand exactly as before.

## The grammar

A ` ```yaml world ` block goes after the ` ```yaml meta ` block, before the first shot (the key is `world`):

````markdown
```yaml world
members:
- {kind: character, id: jerry, store: characters, ref: jerry, at: [-0.45, 0.65, 1.6], height: 1.75}
- {kind: character, id: paul, store: characters, ref: paul, at: [0.45, 0.65, 1.6], height: 1.75}
- {kind: prop, id: wheel, store: props, ref: wheel_hands, attached: {to: paul}, after: paul}
- {kind: environment, id: set, store: environments, ref: car_cabin}
viewpoints:
  two_shot: {at: [0, 0, 0], vanish: [0, -262]}
  paul_single: {subject: paul, size: close_up, subject_at: [150, 0]}
  jerry_single: {subject: jerry, size: close_up, subject_at: [-150, 0]}
travel:
  speed: 20
  far: 60
  streams:
  - {id: dash, ref: road_dash, height: 0.1, every: 12, y: 1.2, after: set/rear_view}
  - {id: pole, ref: pole, height: 6, every: [30, 50], lane: [3, 3.5], y: 1.2, after: set/rear_view}
  - {id: tree, ref: olive_tree, height: 4, every: [10, 40], lane: [-14, -5], y: 1.2, after: set/rear_view}
  plates: {far: [set/rear_view], vehicle: [set/cabin, set/front]}
```

## Shot mountain (cutout)

```yaml shot
duration: 10.0
viewpoint: two_shot
```

```yaml actions
- {kind: play, target: jerry, animation: idle_breath}
- {kind: expression, target: paul, preset: skeptical, intensity: 0.4}
```

## Shot its_big (cutout)

```yaml shot
duration: 6.0
viewpoint: jerry_single
```
````

- **Members** are the same `{kind, id, store, ref}` lines a shot's `entities` block uses, plus where they are: `at: [x, y, z]` in units of your choice (metres read well), `x` to the right, `y` DOWN (as on the stage), `z` away from the viewer; and a size, `height` (or `width`) in those units. A character's `at` is where its feet stand. A prop that shows part of a character's body (the wheel with Paul's hands, see `characters.md`) is `attached: {to: paul}` with no position of its own: it goes where Paul goes and is placed on his shoulders in every framing. An `environment` member is simply present in every framed shot (its plates are drawn per shot).
- **A viewpoint** is a camera: `at: [x, y, z]` and either `look: [yaw, pitch, roll]` in degrees, `look_at: [x, y, z]`, or `vanish: [sx, sy]` (where the road's vanishing point lands on screen, in pixels from the frame centre); `fov` is the horizontal field of view (default 50°). Or a **composition**: `subject` (one member, or a list for a two-shot), `size` (`close_up` head and shoulders, `medium` waist up, `full` the whole figure, `wide` with room around) and `subject_at: [sx, sy]` (where the subject lands on screen; `[0, 0]` is the centre). Name the coverage under `viewpoints` and reuse the names: two shots on `jerry_single` frame identically. `hide: [jerry]` on a viewpoint leaves a member out of that shot.
- **A framed shot's `entities` block** lists only what you animate or place by hand (it may be empty, or absent). Everything the frame shows is added for you. A hand `stage: {at: [...]}` on a listed member always wins (it keeps the world's size unless you also give `scale`), and the check says when it disagrees with the world. A member the viewpoint `hide`s but the shot lists stays: the listing wins.
- **Actions** stay in the shot's screen pixels, as always (a 2 px seat bob is 2 px in any framing). Place nothing with `set x`/`set y` at `at: 0` in a framed shot: the world placed it.
- **A travel** is the viewpoint moving through the world at `speed` units per second of film time; the cast rides with it. `streams` are rows of one prop: `every` units apart along the direction of travel (a range `[min, max]` scatters them), `lane` to the right of it (negative: left; a range scatters), at height `y` (the ground is below the eye, so `y` is positive). `plates` must name every plane of the shot's environment: `far` for what is at infinity (the sky, the horizon, the distant range, and NOTHING nearer: near and mid objects come from the streams; a far plate is drawn with `depth: 0`), `vehicle` for what is rigid with the camera (the cabin, the dashboard, the windscreen frame). A plate with near trees baked in stands still while the poles move, and reads as broken.
- **The line.** The check warns when two members swap sides across a cut (the 180° rule). Keep a conversation's viewpoints on one side of the line between the speakers: for two people side by side in a car, every viewpoint from the front.
- `on:` is not a word you can use as a key (YAML reads it as `true`); the field is `subject`. A long shot with dense streams can be refused past the travel's action budget (`max_actions`, 20,000): space the streams out (`every`), bring `far` in, or cut the shot.
