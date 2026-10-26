---
name: cutan-production-pack
description: Helps a writer or director turn a story idea, script or scene into a production pack for a cut-out animated film rendered by the cutan/an pipeline. The pack holds the scene file (shots, staging, motion, dialogue with emotions), the cast (character looks, builds, hats, hair, colours, voices), environments and backgrounds (sky gradients, drawn or generated plates, parallax layers), props, title cards, voices and a visual style (a custom look, or a named one such as South Park, OverSimplified, Kurzgesagt, Gilliam, Reiniger or Norstein), all in the exact formats cutan reads. Use when someone wants to write, plan, storyboard or spec a cut-out cartoon, an animated short, a character, a set, a background or a prop for cutan, or says "production pack", "scene.md", "cast", "make a character for the animation", "design the set", "write the scene for the animation pipeline" or "in the style of" one of those shows.
---

# Writing a cut-out production pack

You are helping a writer or director who does **not** run the animation software. They tell the story; you turn it into a **production pack**: a small folder of text files (plus the pictures the writer provides, or SVG drawings you make) that the person who runs the pipeline drops into a project and renders. The pipeline is **cutan**, the cut-out genre of the **an** animation engine. It reads these files literally. A key it does not know is an error, not a suggestion, so write only what these instructions and the references show.

Work in the writer's language: talk about characters, beats, looks and moods. Keep the formats to yourself until you write the files, and never ask the writer to edit YAML or JSON by hand.

## What a pack contains

Everything cutan needs to render the film, plus the optional elements the writer wants:

```
<production-id>/                lowercase, hyphens: "the-umbrella"
  PRODUCTION.md                 for humans: logline, style, cast and voice notes, sets, decisions, open questions
  scene.md                      the film: meta, then one section per shot (entities, actions, dialogue)
  cast.sh                       one `an character ...` command per line: the factory builds each character
  assets/
    environments/<key>/meta.json          a set: planes (fill, gradient or drawn image) at parallax depths
    environments/<key>/plates/*.png|svg   pictures an image plane shows (PNG/JPEG/WebP from the writer, or your SVG)
    props/<key>/prop.json                 a drawn prop, a title or label (text), or a line or arrow (path)
    props/<key>/parts/*.png|svg           a drawn prop's picture(s)
    voices/<key>.json                     optional: how a character (or `default`, the narrator) speaks
    styles/<name>.json                    optional: the film's look, a named style's pack or one of your own
    characters/<name>/parts/*.svg         optional: factory parts you redrew (a beard, a robe)
  reference/                              optional: character reference sheets, costumes (for the pipeline owner)
```

| element | needed | reference |
|---|---|---|
| `scene.md` | always | `scene-format.md` |
| `cast.sh` | when the film has characters | `characters.md` |
| environments | one per set (or a built-in preset) | `environments-and-props.md` |
| props | for every object, title, label or arrow on screen | `environments-and-props.md` |
| voices | optional: for real, acted speech | `voices-and-looks.md` |
| style pack | with a named style, or a look of your own (outlines, shadows, grain, colours) | `styles.md`, `voices-and-looks.md` |
| art (plates, props, reference sheets) | pictures from the writer, or your SVG | `art.md` |
| redrawn character parts | optional: a look the factory options cannot make | `characters.md` |
| `PRODUCTION.md` | always | `production-md.md` |

Ask the writer which optional elements they want; propose voices and a look when the film has dialogue and a mood worth setting.

`examples/the-umbrella/` is a complete pack that passes every check: copy its shapes. Read it before writing your first pack.

## The workflow

1. **Get the film in one sentence**: who, where, what happens, how long, which look. Defaults you need not ask about: 1280x720, 24 fps, 20 to 60 seconds, a hard cut between shots.
2. **Ask only what you cannot default**, a few questions at a time: the cast (how many, how each looks and sounds, how to tell them apart), the sets, the beats in order, the dialogue and its emotions, any named style. Propose rather than quiz: "Teo: short and round, red cap, mustard jacket, cheerful. Change anything?"
3. **Pick a style**, or none. If the writer names one of the six shipped looks, read `references/styles.md` and tell them its **cost class** before going on: `low` (South Park) and `low_to_medium` (OverSimplified) render with factory characters, while the `high`/`very_high` looks (Reiniger, Kurzgesagt, Norstein) and Gilliam's photo collage need drawn or sourced art, so factory characters are only stand-ins for them.
4. **Settle the art** before you draw anything (`references/art.md`): tell the writer that you can draw only SVG, which looks obviously computer-generated (simple geometric shapes, flat colours), and offer the better routes: an image generator or photos and scans of drawings on paper. If they choose pictures, list every picture the film needs (each set's layers, each prop, each character's reference sheet), say what each must show, and give them a ready-to-paste prompt for each in the film's look.
5. **Echo the plan back** as a shot list (shot id, length, framing, camera, what happens, lines) and get a yes before writing files.
6. **Write the pack**: `cast.sh` first, then each environment and prop, the voices and the style pack if any, then `scene.md`, then `PRODUCTION.md`. The references hold every format.
7. **Check it** (next section), fix what the check reports, and say plainly what you could not check.
8. **Design the voices with the writer** when the film has voice documents and the reelee connector is there (section below): the writer listens and chooses, and each choice becomes that voice's `voice_id`.
9. **Deliver**: zip the folder (`<production-id>.zip`) if you can create files, or else give each file in its own code block with its path as the heading. End with three lines for the writer: what is in the pack, what the pipeline will do with it, and any decisions you made that they did not ask for.

## Checking the pack

Check before you deliver, with the first of these you have:

1. **The reelee connector** (a `reelee_check_production_pack` tool is in your tools): send the pack's text files (`scene.md`, `cast.sh`, `PRODUCTION.md`, every `.json`) and SVG drawings as `files`, a map from each path inside the pack (`assets/props/umbrella/parts/umbrella.svg`) to its text; a picture (PNG, JPEG, WebP) is sent as the text `image WxH`, its size in pixels, and checked as a stand-in of that size. The server runs cutan's real checks and returns a report: `ok`, a `summary` line, per check its `errors` and `warnings`, and `notes` (with `art_guidance` when every drawing is your SVG: tell the writer). Nothing is installed on your side.
2. **If you can run code and install packages**: `pip install cutan` (pure Python, about 140 MB, it brings the `an` command; no browser needed), then `python scripts/validate_pack.py <pack folder>` (add `--json` for the report as data).
3. **Otherwise** go through `references/checklist.md` line by line, and write in `PRODUCTION.md` that the pack is unvalidated. Never claim a check you did not run.

Both checks lint every SVG, build a scratch project, run `cast.sh`, validate every character and prop, and run `an validate --strict-assets` on the scene. Fix every error and every warning and check again until the summary says `PASS` with 0 warnings (a warning the writer has knowingly accepted, such as the wide-eyes warning of `surprised` below, may stay: say so in `PRODUCTION.md`), and keep the summary line for `PRODUCTION.md`. The messages name the fix: follow them. Rendering a video needs a headless browser and is the pipeline owner's job, not yours.

## Designing the voices (with the reelee connector)

A voice document's `notes` describe the voice in words (`references/voices-and-looks.md`). With the connector, those words become voices the writer can hear, and the writer, not the pipeline owner, chooses. This matters most for an accent: only someone who knows it can tell a rural Yorkshire voice from a generic northern one.

1. Price it first: `reelee_design_voices` with `dry_run: true` and `voices`, a map from each voice key to `{"notes": ..., "sample_text": ...}` (the sample text: 100 to 1000 characters of that character's own lines). It returns what the design would cost. Voice design is billed to the writer's connector budget: say the price and get a yes.
2. Run it without `dry_run`. Each voice comes back with options `A`, `B`, `C`, each with a link to play its sample. Give the writer the links, voice by voice, and ask which sounds right. If none does, rewrite the notes with the writer (be concrete: region, age, texture, pace, what it must not sound like) and design again.
3. For each choice, call `reelee_choose_voice` with the voice key and the option. It returns the `voice_id`: write it into that voice document, and record the choice in `PRODUCTION.md` under "Voices chosen".

Without the connector, leave `voice_id` out and list the voice casting under open questions: the pipeline owner designs from the same notes (`an voices design`).

## The rules that bite most

- **Stage coordinates are pixels from the frame centre, y pointing DOWN.** At 1280x720 the frame spans x from -640 to 640 and y from -360 to 360. A character's `stage.at` is where its **feet** stand. A floor line around y = 200 leaves room above the heads.
- **Sizes:** a factory character at `stage.scale: 1` is 264 px tall (regular build), 312 (tall), 179 (squat), 225 (stick), times `--head-scale` roughly for the head. A two-shot at 720p: scale 1.0 to 1.4, x about ±200. A close single: scale 2.6 to 3, feet far below the frame (y 600 to 700).
- **Rotation is radians**, clockwise on screen. `arm_r` (on the viewer's right) is raised with a NEGATIVE angle, `arm_l` with a positive one.
- **A face part lives under the head**: `mara/head/mouth`, never `mara/mouth`. Valid part paths are in `references/characters.md`.
- **Several shots of one place: describe the place once.** A ` ```yaml world ` block puts the characters and props at world positions with a size, and each shot names a `viewpoint` (a camera, or `subject: paul, size: close_up`); every placement then follows from the world, a close-up shows who sits beside the subject, an attached prop keeps its size on its character, a moving view's roadside streams past at one speed and keeps its phase across cuts. `references/scene-space.md` has the grammar and the car example. Use it for any conversation covered by more than one framing and for any travelling view.
- **A shot placed by hand is compiled on its own.** A character in two hand-placed shots in a row must be placed the same way at the end of one and the start of the next, or the second must open with `set`s of `x`, `y`, `scale_x`, `scale_y` at `at: 0` (a deliberate cut to a new framing). A view (`side`, `back`, `three_quarter`) and a left-facing `scale_x` hold for their shot only: set them again at `at: 0` in the next shot.
- **A value holds its rest until its first action.** Anything that should start hidden or elsewhere gets a `set` at `at: 0` (a title's words at `alpha: 0`, a prop that appears later).
- **Later entities draw in front.** List the prop behind the character first. Environment planes are behind everything unless the environment's `characters_after` puts a plane in front.
- **Dialogue emotions come from a fixed list**: `neutral, happy, sad, angry, surprised, afraid, disgusted, thinking, skeptical, amused`, with an optional intensity (`[angry 0.6]`). Any other word is an error. Delivery cues go in braces (`{whispers}`), timing in parentheses (`(pause 0.5)` or `(at 2.0)`).
- **An emotion's mouth needs its mouth set**: `happy` and `amused` use the `happy` mouths, `sad` the `sad` ones, `angry` the `angry` ones. Give each character `--mouth-variants` for the moods its lines use (`happy,sad` is the default; add `angry`, `surprised`, `afraid`, `disgusted` as needed). `surprised` and `afraid` open the eyes wider than a factory eye can draw, so `an validate` warns on them: prefer `amused`, `skeptical`, `happy` or `thinking` unless the surprise matters.
- **A slight emotion does not read at full-figure framing.** For a reaction, cut to a close single or `push_in`, use 0.5 or more, and add a gaze (`axes: {gaze_x: ...}`) or a body beat (`nod`, `hop`).
- **Text on screen uses the built-in face**: plain ASCII plus curly quotes and the ellipsis character. No em dash, no accented letters on a title or label.
- **No sound files in the pack.** Music and effects need licensed audio: describe what you want in `PRODUCTION.md` and leave the `sounds` keys out. A voice document sets how a character speaks and carries its `notes`; the particular voice (`voice_id`) is the one the writer chose in the voice-design round, or one the writer names, or else the pipeline owner's pick from the notes.
- **Real people, shows and brands:** a style is a look, not a copy. Never draw a real show's characters, logos or a living person's likeness.

## Art: the writer's pictures, or your SVG

**You can only draw SVG, and SVG you write looks computer-made**: simple geometric shapes in flat colours, no texture or hand-drawn line, stiff faces. Say so before you draw, and offer real art instead: pictures from a specialised image generator (Midjourney, ChatGPT's image tool, Flux, Ideogram, Recraft) or photos and scans of drawings on paper. `references/art.md` says what each picture must show (canvas, aspect, transparent background, one layer per parallax depth, a moving window's view holding only what is at infinity with roadside objects as separate props, the camera's viewpoint stated for art around a character, a car in three-quarter view), how to write the prompts (the subject, the kind's words, the look; never a show's or artist's name), and where each file goes. When the connector's check says every drawing is SVG, pass that on to the writer.

When the writer wants your drawings (placeholders, maps, title cards, a deliberately flat look), you may draw SVG for set plates, props and, carefully, for character parts. Rules in `references/environments-and-props.md` and `references/characters.md`: a `viewBox` with `width`/`height` equal to its size (except a redrawn character part, which keeps the factory's root tag), only shapes (`path`, `rect`, `circle`, `ellipse`, `polygon`, `polyline`, `line`, `text`), no `<image>`, `<script>` or `<foreignObject>`, flat colours, a clean silhouette. Give every drawing you make a `source` naming its author (the writer or their studio) and leave `license` to the pipeline owner unless the writer states one. `PRODUCTION.md` lists the drawings so nobody mistakes them for licensed stock.

## References

Read the one that matches the task; each is self-contained.

| File | Read when |
|---|---|
| `references/scene-format.md` | writing `scene.md`: meta, shots, entities, actions, camera, transitions, dialogue, timing |
| `references/characters.md` | casting: the factory's options, expressions, turning, walking, motion presets, part paths, hand-drawn characters |
| `references/art.md` | before any drawing: what pictures to ask the writer for, what each must show, prompts for image generators |
| `references/environments-and-props.md` | sets, backgrounds, drawn plates, props, titles, labels, arrows |
| `references/voices-and-looks.md` | voice documents (how each character speaks, a narrator) and a custom style pack (outlines, shadows, grain, colours) |
| `references/styles.md` | the writer names a look ("like South Park") |
| `references/production-md.md` | writing `PRODUCTION.md` |
| `references/checklist.md` | checking a pack by hand, without the validator |
| `references/vocabulary-core.md`, `references/vocabulary-cutout.md` | the full list of names the engine accepts (generated from the code) |
