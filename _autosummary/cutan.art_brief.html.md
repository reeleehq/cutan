# cutan.art_brief

What art a cut-out film needs, and how to ask an image generator for it.

Claude can draw for a production pack, but only by writing SVG: simple
geometric shapes in flat colours, which read as obviously computer-made. A
film looks far better with real art: pictures from a specialised image
generator (Midjourney, GPT-image, Flux, Ideogram, Recraft…) or photographs
and scans of drawings made on paper. This module is the one place that says
what each piece of art must contain to be usable, so the writer-facing skill
(`cutan-production-pack`, its `references/art.md`), the pack checker
([`cutan.pack.check_pack()`](cutan.pack.html.md#cutan.pack.check_pack), its note on an all-SVG pack) and the reelee
connector (its `check this pack` result) all say the same thing.

- `ART_KINDS`: each kind of art (sky, far, mid and near plates, the view
  through a moving window, roadside objects, a prop, a vehicle, a character reference sheet, character
  parts, a costume), with where it goes in a pack, its canvas, its background
  and what it must and must not show.
- [`style_look()`](#cutan.art_brief.style_look): a named style’s look in words, for a prompt (the
  `guidance.image_prompt` of its spec in `cutan/styles/`; never a show’s
  name).
- [`image_prompt()`](#cutan.art_brief.image_prompt): a ready-to-paste prompt for one kind, subject and look.
- [`art_guidance()`](#cutan.art_brief.art_guidance): all of it as JSON-ready data.

```pycon
>>> sorted(ART_KINDS)[:3]
['character_parts', 'character_sheet', 'costume']
>>> print(image_prompt("prop", "a red umbrella, closed", style="south_park"))
a red umbrella, closed. A single object, whole and centred, filling a square frame,
seen from the angle it is used at, nothing else in the picture, isolated on a plain
flat white background, no cast shadow, no text. Look: construction-paper cut-out
look, simple round and geometric shapes, flat solid colours, thin near-black
outlines, faint paper grain, no shading, no gradients, no perspective.
>>> image_prompt("sky", "a summer evening", tool="midjourney").endswith("--ar 16:9 --no text, letters, watermark, people")
True
```

### Module Attributes

| [`RASTER_SUFFIXES`](#cutan.art_brief.RASTER_SUFFIXES)   | The picture formats a plate, a prop part or a character part may be (an#211).   |
|--------------------------------------------------------------------|---------------------------------------------------------------------------------|
| [`CLAUDE_SVG_NOTE`](#cutan.art_brief.CLAUDE_SVG_NOTE)   | What Claude tells the writer before it draws anything itself.                   |
| [`SVG_ONLY_NOTE`](#cutan.art_brief.SVG_ONLY_NOTE)     | The checker's note on a pack whose drawings are all hand-written SVG.           |
| [`VIEWPOINT_RULE`](#cutan.art_brief.VIEWPOINT_RULE)    | Art that touches a body says where the camera is relative to the character.     |
| [`PAPER_DRAWINGS`](#cutan.art_brief.PAPER_DRAWINGS)    | How to photograph or scan drawings made on paper so they can be cut out.        |
| [`GENERATOR_TIPS`](#cutan.art_brief.GENERATOR_TIPS)    | how to get usable art out of it.                                                |

### Functions

| [`art_guidance`](#cutan.art_brief.art_guidance)(\*[, style])                      | Everything a writer's Claude needs to ask for real art, as JSON-ready data.   |
|-------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------|
| [`image_prompt`](#cutan.art_brief.image_prompt)(kind, subject, \*[, style, tool]) | A prompt to paste into an image generator for one piece of art.               |
| [`style_look`](#cutan.art_brief.style_look)(style)                              | A style's look in words, for a prompt (`guidance.image_prompt` of its spec).  |

### Classes

| [`ArtKind`](#cutan.art_brief.ArtKind)(key, title, goes_to, canvas, ...[, ...])   | One kind of art a production pack can carry.   |
|-----------------------------------------------------------------------------------------------------|------------------------------------------------|

### *class* cutan.art_brief.ArtKind(key, title, goes_to, canvas, background, content, framing, aspect, status='ready', has_figures=False)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

One kind of art a production pack can carry.

#### aspect *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)*

Midjourney’s `--ar` for it.

#### background *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)*

`"opaque"` or `"transparent"` (or a plain flat colour cut out afterwards).

#### canvas *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)*

Size and aspect, at the default 1280x720 frame.

#### content *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), ...]*

What the picture must show, and must not.

#### framing *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)*

The words a generator prompt adds after the subject.

#### goes_to *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)*

Where the file goes in the pack.

#### has_figures *: [bool](https://docs.python.org/3/builtins/functions.html#bool)* *= False*

Whether the subject is a person or creature (no `people` in –no).

#### status *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'ready'*

`"ready"` (the pack uses it as it is) or
what the pipeline owner still has to do with it.

* **Type:**
  Who turns the picture into film

### cutan.art_brief.CLAUDE_SVG_NOTE *= "I can draw the art for you, but only as SVG: shapes I write as code. The result is simple geometry in flat colours (circles, rectangles, smooth curves), clean but very obviously computer-generated: no texture, no brush or pencil line, little detail, stiff faces. It is fine for a placeholder, a map, a title card or a deliberately flat look. For a film that looks drawn, use a specialised image generator (Midjourney, ChatGPT's image tool, Flux, Ideogram, Recraft) or photograph or scan drawings made on paper, and give me the pictures: I will say what each one must show, and write the prompts."*

What Claude tells the writer before it draws anything itself.

### cutan.art_brief.GENERATOR_TIPS *= {'flux': "no negative prompt, and naming a thing tends to add it: use the positive-only prompt (image_prompt(..., tool='flux') drops the 'no ...' words); give the size as an aspect (16:9, 1:1); a flat plain background, cut out afterwards", 'gpt-image': "ChatGPT's image tool (gpt-image): write the prompt as plain sentences; it can make a transparent PNG when asked ('transparent background, PNG'); ask for edits of the same image to keep a character consistent", 'ideogram': 'good at following a long description; switch magic prompt off so your words stay yours; ask for no text in the image', 'midjourney': 'append the aspect (--ar 16:9 for a plate, --ar 1:1 for a prop) and --no text, letters, watermark; it cannot make a transparent background, so ask for a plain flat white one; keep a character consistent with a reference image (--oref <image URL> in V7, --cref in V6)', 'recraft': "can draw in a vector style and export SVG, which suits the flat looks (South Park-like, OverSimplified-like, Kurzgesagt-like); an SVG it exports must still follow the pack's SVG rules (no embedded images)"}*

how to get usable art out of it.

* **Type:**
  Per image generator

### cutan.art_brief.PAPER_DRAWINGS *= ("Draw each piece on its own sheet, or spread pieces out with a hand's width of empty paper between them.", 'Use plain white or pale paper, and a background colour that appears nowhere in the drawing; strong, closed outlines cut out cleanest.', 'Scan at 300 dpi, or photograph straight down in even daylight: no shadow of the phone or the hand, no glare, no perspective, the sheet filling the frame.', 'Cut-paper pieces (actual scissors and card) are welcome: photograph them flat on a contrasting background.', 'Send the original files (PNG or JPEG), not screenshots; the pipeline owner cuts the pieces out (cutan.carve) and keeps who drew them and on what terms.')*

How to photograph or scan drawings made on paper so they can be cut out.

### cutan.art_brief.RASTER_SUFFIXES *= ('.png', '.jpg', '.jpeg', '.webp')*

The picture formats a plate, a prop part or a character part may be (an#211).

### cutan.art_brief.SVG_ONLY_NOTE *= "every drawing in this pack is hand-written SVG ({n} file(s)): it will look computer-generated (simple shapes, flat colours). Tell the writer, and offer real art instead: pictures from an image generator or photos and scans of paper drawings, as PNG (transparent background for props and parts) or JPEG (opaque plates). What each picture must show, and prompts to paste into a generator: the skill's references/art.md (cutan.art_brief.art_guidance())."*

The checker’s note on a pack whose drawings are all hand-written SVG.

### cutan.art_brief.VIEWPOINT_RULE *= "Art that touches a character (a car's interior around the driver, a seat, a steering wheel, a costume) states the camera's viewpoint relative to that character in the prompt, e.g. 'seen from in front of the car, looking back at the driver'; otherwise the picture and the character face different ways."*

Art that touches a body says where the camera is relative to the character.

### cutan.art_brief.art_guidance(, style=None)

Everything a writer’s Claude needs to ask for real art, as JSON-ready data.

A prompt is `prompt_recipe`: the subject, the kind’s `framing`, the `look`.

```pycon
>>> g = art_guidance(style="norstein")
>>> sorted(g)
['claude_svg', 'formats', 'generators', 'kinds', 'look', 'paper_drawings', 'prompt_recipe', 'viewpoint']
>>> g["kinds"][0]["key"], g["look"].startswith("painted multiplane")
('sky', True)
```

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

### cutan.art_brief.image_prompt(kind, subject, , style=None, tool=None)

A prompt to paste into an image generator for one piece of art.

kind: a key of `ART_KINDS`
subject: what the picture is of, in the writer’s words
style: a style name or spec (its look in words), or `None` for a placeholder
tool: `"midjourney"` appends its `--ar` and `--no` flags; `"flux"`

> drops the `no ...` words; any other tool takes the plain prompt (see
> [`GENERATOR_TIPS`](#cutan.art_brief.GENERATOR_TIPS))
* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### cutan.art_brief.style_look(style)

A style’s look in words, for a prompt (`guidance.image_prompt` of its spec).

`style` is a style’s name, a spec mapping, or `None` (the writer’s own look).

```pycon
>>> style_look("reiniger").startswith("black paper silhouette")
True
>>> style_look(None)
'<your look in words: medium, colours, line, texture>'
```

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)
