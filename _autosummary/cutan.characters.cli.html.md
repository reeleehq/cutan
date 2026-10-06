# cutan.characters.cli

User-facing character CLI subcommands.

Wired into the top-level `an` dispatcher via `character_*` dispatch-friendly
functions in `an.tools`. Each function here takes plain strings/bools
and returns a string for terminal display.

Subcommands (used as `an character <verb> ...`):

- `new`       — generate a fresh character from DiceBear or fallback art.
- `add-views` — give an offline character its turnaround (an#197).
- `add-half-lid` — a HALF eyelid drawing from the rig’s own lid art (cutan#65).
- `mouths`    — regenerate the 9-shape default mouth set.
- `validate`  — completeness check.
- `capabilities` — what it affords, and per aspect which methods apply (an#248).
- `silhouette`— rasterize silhouettes; for two characters, also IoU.
- `preview`   — open an HTML viewer cycling visemes + idle animation.

### Module Attributes

| [`SILHOUETTE_ARTIFACTS`](#cutan.characters.cli.SILHOUETTE_ARTIFACTS)   | Where silhouettes go, under the project the characters belong to (never a character's own folder: that folder is the published asset, an#272).   |
|-------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------|

### Functions

| [`add_gaze`](#cutan.characters.cli.add_gaze)(name[, out_dir, overwrite_eyes])         | Give `name` the eye stack (an#99): sclera and pupil slots under each lid, a filled closed lid, and the `gaze_travel` clamp — so `gaze_x` / `gaze_y` and the ambient saccades move its pupils.   |
|----------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`add_half_lid`](#cutan.characters.cli.add_half_lid)(name[, out_dir, fraction, ...])      | Give `name` a HALF eyelid drawing (cutan#65), made from its own OPEN and CLOSED lid art: the closed lid cut to its top `fraction`, under the open eye's outline.                                |
| [`add_views`](#cutan.characters.cli.add_views)(name[, out_dir])                        | Give `name` its turnaround (an#197): back, side and three-quarter head and torso art, a `view` swap set, and a pose per view — so `play: turn` and `set <name> view <key>` turn it.             |
| [`capabilities`](#cutan.characters.cli.capabilities)(name[, out_dir, as_json, style])     | What a character affords, and per aspect which methods apply and what the rest lack.                                                                                                            |
| [`contract`](#cutan.characters.cli.contract)()                                        | Print the art-package contract an illustrator must satisfy.                                                                                                                                     |
| [`mouths`](#cutan.characters.cli.mouths)(name[, out_dir, palette, variants])        | Regenerate the default 9-shape mouth set for `name`, plus its `viseme@<form>` variants, and declare them in the descriptor.                                                                     |
| [`new`](#cutan.characters.cli.new)(name[, out_dir, seed, style, voice_ref, ...]) | Create a new character at `out_dir`/`name`.                                                                                                                                                     |
| [`preview`](#cutan.characters.cli.preview)(name[, out_dir, open_browser])            | Render a small HTML viewer that previews all visemes + idle animation.                                                                                                                          |
| [`record`](#cutan.characters.cli.record)(name[, out_dir, output, duration, ...])    | Record a character's preview HTML to mp4.                                                                                                                                                       |
| [`silhouette`](#cutan.characters.cli.silhouette)(name[, other, out_dir, output, size])  | Render a black silhouette for `name` (and optionally compare to `other`).                                                                                                                       |
| [`validate`](#cutan.characters.cli.validate)(name[, out_dir])                         | Validate a character's directory structure and descriptor.                                                                                                                                      |

### cutan.characters.cli.SILHOUETTE_ARTIFACTS *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), ...]* *= ('artifacts', 'silhouettes')*

Where silhouettes go, under the project the characters belong to (never a
character’s own folder: that folder is the published asset, an#272).

### cutan.characters.cli.add_gaze(name, out_dir='', overwrite_eyes=False)

Give `name` the eye stack (an#99): sclera and pupil slots under each
lid, a filled closed lid, and the `gaze_travel` clamp — so `gaze_x` /
`gaze_y` and the ambient saccades move its pupils. The expand step for a
character made before Wave 6; idempotent on one that has it.

name: character id
out_dir: parent directory; defaults to ./assets/characters
overwrite_eyes: replace hand-drawn eye parts with the synthesized outline

> and filled lid (refused otherwise — a promoted rig’s eyes are not the
> factory’s to redraw)
* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### cutan.characters.cli.add_half_lid(name, out_dir='', fraction=0.5, overwrite=False)

Give `name` a HALF eyelid drawing (cutan#65), made from its own OPEN and
CLOSED lid art: the closed lid cut to its top `fraction`, under the open
eye’s outline. A partial lid (`lid_open` between -0.35 and -0.85: a squint,
suspicion, annoyance) then narrows the eyes instead of showing them open.

name: character id
out_dir: parent directory; defaults to ./assets/characters
fraction: how much of the eye the half lid covers, from the top
overwrite: replace a HALF lid someone drew (refused otherwise)

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### cutan.characters.cli.add_views(name, out_dir='')

Give `name` its turnaround (an#197): back, side and three-quarter head
and torso art, a `view` swap set, and a pose per view — so `play: turn`
and `set <name> view <key>` turn it. The expand step for an offline
character made before views; idempotent. Refused for a DiceBear head or a
hand-drawn rig, whose views are an illustrator’s to draw.

name: character id
out_dir: parent directory; defaults to ./assets/characters

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### cutan.characters.cli.capabilities(name, out_dir='', as_json=False, style='')

What a character affords, and per aspect which methods apply and what the rest lack.

The affordances are derived from `character.json` and the art files
present (ADR 0002 decision 2), with the declared overrides it used; per
aspect (`locomotion`, `speech`, …) the method the default chain picks,
the methods that apply, and for each other method the missing capabilities
with the remedy that would add them. With `style`, each aspect also says
what it resolves to under that style’s policy (cutan#9, an#273): a South
Park character with legs bounces, a Reiniger silhouette mimes.

name: character id
out_dir: parent directory; defaults to ./assets/characters
as_json: print the answer as JSON (what the MCP surface returns)
style: a style spec’s name (`python -m cutan.styles` lists them) or path

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### cutan.characters.cli.contract()

Print the art-package contract an illustrator must satisfy.

**Derived from the schema and the validator, never hand-written**, so it
cannot drift from what `an character validate` actually enforces — a
contract that disagrees with its checker is worse than none, because it
gets a human paid for work that cannot land.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### cutan.characters.cli.mouths(name, out_dir='', palette='', variants='happy,sad')

Regenerate the default 9-shape mouth set for `name`, plus its
`viseme@<form>` variants, and declare them in the descriptor.

Useful when you want to reset a character’s mouth art to the offline
fallback (e.g. after experimenting with hand-drawn mouths), or to give a
pre-an#98 character the variant sets its expressions prefer.

name: character id
out_dir: parent directory; defaults to ./assets/characters
palette: optional JSON string to override colors, e.g. ‘{“lip”:”#a44”}’
variants: comma-separated mouth forms (see `an character new`); “” = none

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### cutan.characters.cli.new(name, out_dir='', seed='', style='lorelei', voice_ref='', offline=False, acknowledge_attribution=False, overwrite=False, mouth_variants='happy,sad', palette='', build='regular', head_scale=1.0, hat='none', sash=False, views=True, hair_style='peak', hair_length='short')

Create a new character at `out_dir`/`name`.

name: character id (used as the directory name and descriptor ‘name’)
out_dir: parent directory; defaults to ./assets/characters
seed: deterministic seed for DiceBear; defaults to `name`
style: DiceBear style. The default is CC0 — no attribution duty. Some styles

> are CC BY 4.0 and oblige whoever ships the video to credit the artist;
> those need –acknowledge-attribution. Run `an credits <project>` to see
> what a project owes.

voice_ref: voice id stored in the descriptor’s `voice_ref` field
offline: skip DiceBear and use the deterministic geometric fallback
acknowledge_attribution: accept the attribution duty of a CC BY style
overwrite: replace an existing directory at the target
mouth_variants: comma-separated mouth forms to draw as `viseme@<form>`

> sets (an#98) — a form an expression preset prefers (happy, sad, angry,
> surprised, afraid, disgusted); “” for the neutral set only

palette: colours by StylePack role, “skin=#f1c9a5,clothing=#2e7d4f” (or a
: JSON object); roles: skin, hair, clothing, leg, accessory

build: body proportions — regular, squat (round body, short legs), tall,
: stick (small blocky body, stick limbs)

head_scale: the head and its whole face scaled together (1.0 = regular)
hat: none, cap, beanie, bowler or bicorne (offline head only), in the

> accessory colour, worn above the brows so expressions read (a hat that
> cannot clear them on a very small head is recorded, and
> `an character capabilities` says the brows cannot act)

hair_style: peak (the default), bald, bun or curly (offline head only),
: in the hair colour

hair_length: short (the default), medium (to the jaw) or long (past the
: chin) (offline head only); bald takes short

sash: a diagonal band across the torso, in the accessory colour
views: draw the turnaround — back, side (a profile facing right) and

> three_quarter beside the front, as a `view` swap set (offline head
> only), so `play: turn` can turn the character (an#197)
* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### cutan.characters.cli.preview(name, out_dir='', open_browser=False)

Render a small HTML viewer that previews all visemes + idle animation.

The page includes the head SVG, cycles through `mouth_a … mouth_x`
once a second, and shows a ±2 px sine-wave breath on the head. Useful
for eyeballing a character’s mouth set before integrating into the
main runtime.

name: character id
out_dir: parent directory; defaults to ./assets/characters
open_browser: also open the file in the default browser

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### cutan.characters.cli.record(name, out_dir='', output='', duration=8.0, width=640, height=480)

Record a character’s preview HTML to mp4.

Real video file showing the new SVG character art animating: cycles
through all 9 visemes and applies the breath/head-tilt animation.

name: character id
out_dir: parent directory; defaults to ./assets/characters
output: output mp4 path; defaults to <character_dir>/preview.mp4
duration: recording length in seconds (default 8)
width / height: video resolution (default 640x480)

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### cutan.characters.cli.silhouette(name, other='', out_dir='', output='', size=512)

Render a black silhouette for `name` (and optionally compare to `other`).

The silhouette is the figure as the stage draws it (build, head scale, hat:
an#272), tinted black on white. When two names are given, prints both
silhouettes’ paths and an IoU score (0..1; lower means more visually
distinct). Nothing is written into a character’s folder, so a later
`an library publish` never ships a silhouette.

name: character id
other: optional second character to compare against
out_dir: parent directory; defaults to ./assets/characters
output: output PNG path (one name only); defaults to the project’s

> artifacts/silhouettes/<name>.png

size: square output size in pixels (default 512)

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### cutan.characters.cli.validate(name, out_dir='')

Validate a character’s directory structure and descriptor.

name: character id
out_dir: parent directory; defaults to ./assets/characters

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)
