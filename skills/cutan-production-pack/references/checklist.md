# Checking a pack by hand

Use this only when neither the reelee connector's `reelee_check_production_pack` tool nor `scripts/validate_pack.py` can run. Go through every item; each one is a mistake the validator would have caught.

**Files**
- [ ] `scene.md`, `cast.sh`, `PRODUCTION.md` at the top of the pack; every `ref` in `scene.md` is a character in `cast.sh` (or a folder under `assets/characters/`), a folder under `assets/environments/` or `assets/props/`, or a built-in environment (`park`, `indoor`, `night`, `sunset`, `default`).
- [ ] Every JSON file parses (double quotes, no trailing commas, no comments). Environments and props have their `kind` (`EnvironmentDescriptor`, `PropDescriptor`, `TextDescriptor` or `PathDescriptor`) and a `name` equal to their folder's; a style pack is `assets/styles/<name>.json` with `"kind": "StylePack"` and that `name`; a voice document has no `kind` and only the keys in `voices-and-looks.md`; its `notes` are a string of 20 to 1000 characters.
- [ ] A `style_pack:` in the meta has its file in `assets/styles/`; every `--voice-ref` in `cast.sh` has its file in `assets/voices/`.
- [ ] Every file an environment or prop points to (`src`, `path`) exists at that path inside the asset's own folder.
- [ ] `cast.sh` holds only comments and `an character new <name> --offline ...` lines (plus `an character mouths`, `add-half-lid`, `add-views`, `add-gaze`), each option spelled as in `references/characters.md`, palette values quoted.

**SVG drawings**
- [ ] Root has `xmlns="http://www.w3.org/2000/svg"`, a `viewBox`, and `width`/`height` equal to the viewBox's size; a redrawn character part keeps the factory file's root tag exactly, and has the same file name as the factory's.
- [ ] Only shapes and groups; no `<image>`, `<script>`, `<foreignObject>`, no links to other files or addresses (`href` only to `#id`, no `url(http...)`, no `data:`). Valid XML (every tag closed, attributes quoted).
- [ ] It draws something visible inside its viewBox.

**scene.md**
- [ ] One `yaml meta` block; each shot is `## Shot <id> (cutout)` with a `yaml shot` block holding a `duration`; ids unique.
- [ ] Each shot's environment is the first entity; every entity has `kind`, `id`, `store`, `ref`; characters, drawn props and `world` text or paths have a `stage: {at: [x, y], scale: s}` (an `overlay` title needs none).
- [ ] Every action's `target` is an entity id of THAT shot, or a part path from `references/characters.md` (`mara/head`, `teo/arm_r`, never `mara/mouth`), or `<environment id>/<plane name>`, or `<text id>/word_N` with N below the number of words.
- [ ] With a `dissolve` or `wipe`, the meta has `duration:` = the sum of shot durations minus those transitions' durations.
- [ ] Every action ends inside its shot (`start` + length <= `duration`; a walk takes about `distance / (80 x stage scale)` steps of 0.4 s each: 560 px at scale 1.1 is 6 steps, 2.4 s).
- [ ] `rotation` values are radians (between about -3.2 and 3.2), not degrees.
- [ ] Anything that starts hidden or elsewhere has a `set` at `at: 0.0`.
- [ ] A character in two consecutive shots: same `stage.at` and scale at the cut, or the second shot opens with `set`s of `x`, `y`, `scale_x`, `scale_y` at 0. A view other than `front`, or a negative `scale_x`, is set again at 0 in the next shot.
- [ ] Motion presets and their `args` exist in the table in `references/characters.md`; `point` targets an arm, not the character.
- [ ] Camera moves are from the list in `references/scene-format.md`; a style's allowed list respected.
- [ ] Dialogue: emotions only from `neutral, happy, sad, angry, surprised, afraid, disgusted, thinking, skeptical, amused`; each character's `--mouth-variants` covers the moods it speaks in (`happy`/`amused` need `happy`, `sad` needs `sad`, `angry` needs `angry`, ...); only `(pause s)` or `(at s)` in parentheses before the colon.
- [ ] Dialogue fits its shot: about 2.5 words a second, plus pauses, ending a second before the shot does.
- [ ] Text props: ASCII only (curly quotes and the ellipsis are fine), no em dash or accents.

Write "Not validated: checked by hand against the checklist" in `PRODUCTION.md`, so the pipeline owner runs the validator on receipt.
