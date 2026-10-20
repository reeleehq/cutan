# Environments and props

## Environments (sets and backgrounds)

An environment is `assets/environments/<key>/meta.json`: a list of **planes** drawn back to front, each at a parallax **depth**. A shot names it once, first in its entities: `{kind: environment, id: set, store: environments, ref: bus_stop}`. Its planes are then addressable as `set/<plane name>` (to tint, fade or move one).

```json
{
  "kind": "EnvironmentDescriptor",
  "name": "bus_stop",
  "planes": [
    {"name": "sky", "art": {"kind": "gradient", "gradient": {"stops": ["#1b2140", "#e9a86b"]}}, "depth": 0.2},
    {"name": "skyline", "art": {"kind": "image", "src": "plates/skyline.svg"}, "depth": 0.5, "size": [1800, 450], "offset": [0, -25],
     "source": {"provider": "...", "author": "..."}},
    {"name": "ground", "art": {"kind": "fill", "color": "#4a4f57"}, "depth": 1.0, "size": [2400, 200], "offset": [0, 300]},
    {"name": "shelter", "art": {"kind": "image", "src": "plates/shelter.svg"}, "depth": 1.0, "size": [400, 360], "offset": [300, 20]}
  ],
  "characters_after": "shelter"
}
```

`"kind": "EnvironmentDescriptor"` is required: without it the planes are dropped (with a warning) and a plain backdrop is drawn. `name` equals the folder name.

A plane (unknown keys are an error):

| key | meaning |
|---|---|
| `name` | unique within the environment |
| `art` | what it is made of, one of: `{"kind": "fill", "color": "#rrggbb"}`; `{"kind": "gradient", "gradient": {...}}`; `{"kind": "image", "src": "plates/<file>.svg"}` (a path inside the environment's own folder; `.png`, `.jpg`, `.webp` also work) |
| `depth` | parallax: `0` never moves with the camera (a sky), `1.0` moves exactly with the characters (the ground they stand on, a wall behind them), between is in between, above 1 is foreground (moves faster) |
| `size` | `[width, height]` in pixels. Leave it out on a fill or gradient to cover the whole frame. An image is fitted into its box keeping its aspect (`"fit": "stretch"` fills it) |
| `offset` | `[x, y]`: where the plane's centre sits, in pixels from the frame centre, y down |
| `anchor` | `[0.5, 0.5]` by default: which point of the plane sits at `offset` |
| `source` | who made the drawing (an image plane you drew) |

Gradients use CSS's vocabulary: `{"stops": ["#141a33", "#f2c48a"]}` runs top to bottom (`"angle": 90` runs left to right, in degrees, 0 is up); `{"type": "radial", "stops": ["#fff3d2", "#fff3d200"]}` is a glow (8-digit hex carries transparency), with `center` and `radius` as fractions of the box.

- `characters_after` names the plane the characters stand in front of. Planes listed after it are drawn **over** the characters: a railing, a bush, a counter in the foreground.
- Size planes for the camera: a `pan_right` travels a third of the frame (about 430 px at 720p), so a plane at depth 1 must reach that far past the edge. A sky at depth 0 or 0.2 can stay frame-sized. `an validate` warns when a camera shows past a plane's edge.
- A zoom (`push_in`) magnifies every plane alike, so it needs no extra size beyond the frame.
- A title card or a map is just an environment: one `fill` plane at depth 0 (`examples/the-umbrella/assets/environments/title_card/`).
- Built-in presets need no folder: `park`, `indoor`, `night`, `sunset`, `default`. They are plain; prefer your own.

### A plate from a picture

The best plates are the writer's pictures (from an image generator, or a scan of a painting): `references/art.md` says what each layer must show and how to prompt for it. A picture is an `image` plane like an SVG: `{"kind": "image", "src": "plates/street.png"}`, with a `size` of the picture's own aspect (a 2560x1080 picture: `"size": [2560, 1080]`, or `[1707, 720]` to show it frame-high at 720p). Layers above the sky need a transparent background where the layer behind should show (a PNG with alpha). Credit it with `source` (who made it, which tool).

### Drawing a plate (SVG)

- Root: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 W H" width="W" height="H">`, with `width`/`height` equal to the viewBox size.
- Only shapes: `path`, `rect`, `circle`, `ellipse`, `polygon`, `polyline`, `line`, `text`, `g`. No `<image>`, `<script>`, `<foreignObject>`, no external fonts or links. Flat fills read best in cut-out; `fill-opacity` is fine.
- Draw at the size it will show (a 1600x400 skyline for a plane of about 1800x450) so lines keep their weight.
- The bottom edge of anything standing on the ground (a shelter, a house) lines up with the floor line (y about 200 at 720p): put the plane's `offset` y at `200 - height / 2`.
- Leave the middle third of the frame quiet where characters will stand and talk.

## Props

A prop is `assets/props/<key>/prop.json`, placed in a shot as `{kind: prop, id: umbrella, store: props, ref: umbrella, stage: {at: [x, y], scale: s}}`. Three kinds of document.

### A drawn prop (`PropDescriptor`)

```json
{
  "kind": "PropDescriptor",
  "name": "umbrella",
  "origin": [412, 1010],
  "slots": [{"name": "body", "bone": "root", "attachment": "umbrella"}],
  "skins": {"default": {"slots": {"body": {"umbrella": {"path": "parts/umbrella.svg"}}}}},
  "source": {"provider": "...", "author": "..."}
}
```

- The drawing is `parts/<file>.svg`, or a picture `parts/<file>.png` (transparent background; `references/art.md`), on a 1024x1024 canvas (`viewBox="0 0 1024 1024" width="1024" height="1024"`): draw the object to fill it as the prop's frame.
- `origin` is the point of the drawing (in those 1024 units) that lands on `stage.at`: the base of a lamp, the handle of an umbrella. Without it the prop is placed by its centre.
- Size on screen: the 1024 canvas height shows as 345 px at `stage.scale: 1`, so an object filling the canvas is 345 px tall; scale it from there (a 1.2 m umbrella next to a 1.7 m character of 312 px: scale about 0.6).
- To make a prop appear: `set` its `alpha` to 0 at 0, then back to 1, or `play` `pop_in` at that moment. It moves with `x`, `y`, `rotation`, `scale_x`, `scale_y` tweens like anything else.
- A prop does not follow a hand: place it where the hand will be, and keep that arm still while it shows.
- A prop with moving pieces (a clock's hands, a door) or two states (a lamp on and off) is possible but needs bones and swap sets: describe it in `PRODUCTION.md` and leave it to the pipeline owner.

### Text (`TextDescriptor`): titles, labels, captions on screen

```json
{"kind": "TextDescriptor", "name": "title", "text": "The Umbrella", "layer": "overlay", "unit": "word", "size": 0.11, "color": "#f4efe6", "anchor": "center"}
```

| key | meaning |
|---|---|
| `text` | the words; `\n` breaks a line |
| `layer` | `overlay` (fixed to the screen: titles; takes `anchor`: `center`, `top`, `bottom`, `top-left`, ...) or `world` (in the scene, moves with the camera: a sign, a map label; place it with `stage.at`) |
| `unit` | what animates separately: `word` (default), `glyph`, `line` |
| `size` | a fraction of the frame HEIGHT: 0.06 default, 0.1 for a title |
| `color`, `stroke_width`, `stroke_color` | fill, and an outline in pixels (white labels edged in black) |
| `align`, `max_width` | `left`/`center`/`right`; wrap width as a fraction of the frame width |

Every unit is a part: `title/word_0`, `title/word_1`, ... (spaces are not units). A word-by-word reveal is a `set` of each word's `alpha` to 0 at 0, then a `tween` to 1 at its own `start` (the example's title shot). One style can carry many labels: `overrides: {text: West}` on the entity. Characters: plain ASCII plus curly quotes and the ellipsis; no em dash, no accented letters (they are refused).

### A line or an arrow (`PathDescriptor`)

```json
{"kind": "PathDescriptor", "name": "route", "points": [[-300, 60], [0, -40], [260, 30]], "arrowhead": true, "trim_end": 0.0, "color": "#ba5f31", "width": 10}
```

`points` are scene pixels. `curve: "cubic"` makes smooth curves (points are then `p0 c1 c2 p1 c1 c2 p2 ...`). `trim_end: 0` hides it; `{kind: tween, target: route, property: trim_end, to: 1.0, duration: 1.5, start: 0.5}` draws it on. `wobble: 3` makes it hand-drawn; `closed: true` with `fill: "#rrggbb"` makes a filled shape (a territory on a map); `tail_arrowhead: true` adds a head at the start.

## Provenance

Every drawing you make (a plate, a prop part, a redrawn character part) is credited: `"source": {"provider": "<the production or studio>", "author": "<who made it>"}` on the plane, the prop, or the attachment. Leave `license` out unless the writer has stated one: the pipeline owner sets it. Never use a picture you found online, a logo, or a still from a film: describe what you need in `PRODUCTION.md` instead.
