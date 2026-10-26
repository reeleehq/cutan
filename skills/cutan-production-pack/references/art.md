# Art: what to provide

The pictures make or break a cut-out film. You can draw, but only by writing SVG, and SVG you write looks computer-made. So before you draw anything, tell the writer what your drawings will look like and what the better options are, and help them get real art.

## Say this first (in your own words)

> I can draw the art for you, but only as SVG: shapes I write as code. The result is simple geometry in flat colours (circles, rectangles, smooth curves), clean but very obviously computer-generated: no texture, no brush or pencil line, little detail, stiff faces. It is fine for a placeholder, a map, a title card or a deliberately flat look. For a film that looks drawn, use a specialised image generator (Midjourney, ChatGPT's image tool, Flux, Ideogram, Recraft) or photograph or scan drawings made on paper, and give me the pictures: I will say what each one must show, and write the prompts.

Then let the writer choose, per piece if they like:

- **Pictures from a generator**: you write a prompt per picture (below), they paste it into their tool and give you the results.
- **Drawings on paper**: they draw (or cut paper), photograph or scan, and give you the files.
- **Your SVG**: for placeholders, maps, title cards, diagrams, or a deliberately flat look. Say in `PRODUCTION.md` which drawings are yours.
- **A mix**: real art for the sets and the characters people look at, your SVG for small props and labels.

The factory characters (`cast.sh`) are drawn by the pipeline and are not yours to apologise for; what you would draw are the sets, the props and any redrawn parts.

## What the pack does with pictures

| art | in the pack | status |
|---|---|---|
| set plates (sky, far, mid, near, the view through a moving window) | `assets/environments/<set>/plates/<layer>.png` (or `.jpg`, `.webp`), named by an `image` plane in `meta.json` | used as they are when the background is transparent (the sky may be opaque); a flat background is cut out by the pipeline owner first |
| props, vehicles, roadside objects | `assets/props/<prop>/parts/<prop>.png`, named by the prop's skin in `prop.json` | as plates: transparent is ready, a flat background is cut out first |
| a character reference sheet, a costume | `reference/<name>-sheet.png`, listed in `PRODUCTION.md` | the pipeline owner cuts it into a puppet: it takes their time, so say so |
| a redrawn part of a factory character | `assets/characters/<name>/parts/<part>.png`, named like the factory's SVG (`head.png` for `head.svg`) | replaces that part in the box the factory's drawing had: transparent background, the factory part's aspect |

An image plane is fitted into its `size` box keeping its aspect, so give each plane a `size` with the picture's own aspect (a 2560x1080 picture: `"size": [2560, 1080]`, or `[1707, 720]` to show it frame-high at 720p). A prop picture is sized like an SVG prop: make it 1024x1024 (resize the generator's output to that), and 1024 px of picture shows as 345 px at `stage.scale: 1`; set `origin` in those pixels (the wheels' line, the base of a lamp). A picture's colours are its own: a style pack's colour roles do not recolour it, while outlines and shadows still apply.

Pictures cannot be sent through the connector's check (it takes text): send each one as the text `image WxH` (its size in pixels, e.g. `"assets/environments/street/plates/mid.png": "image 2560x1080"`) and the checker uses a stand-in of that size, so it checks where the picture goes and its size, not the picture itself (its transparency, its format). Put the real files in the zip, and write in `PRODUCTION.md` that the pictures were checked as stand-ins. `scripts/validate_pack.py`, where it can run, checks the real files.

Every picture needs its provenance on the plane, the prop or in `PRODUCTION.md`: who made it, with which tool, and on what terms (a generator's terms of use, the artist's permission). Leave `license` to the pipeline owner unless the writer states one. Never use a picture found online, a logo or a still from a film or show.

## Writing a prompt

A prompt is the subject in the writer's words, then the kind's **prompt words**, then `Look:` and the style's look in words:

> a quiet suburban street at dusk, terraced houses, a bus stop on the right. A stage-like set seen straight on at eye level, the floor line three-quarters of the way down, the centre left open and uncluttered for characters, no people, no animals, no text. Look: construction-paper cut-out look, simple round and geometric shapes, flat solid colours, thin near-black outlines, faint paper grain, no shading, no gradients, no perspective. --ar 21:9 --no text, letters, watermark, people

- Keep the look identical in every prompt of the film, word for word: it is what makes the pictures belong together. With no named style, write the look once with the writer (medium, colours, line, texture) and reuse it.
- **Never put a show's, studio's or artist's name in a prompt** ("in the style of ..."): describe the look. Never ask for a real person's likeness, a show's characters or a logo.
- Generate each layer of a set separately, from the same look; generate the props one per picture.
- **Say where the camera is** whenever the art touches a character: a car's interior around the driver, a seat, a steering wheel, a costume. "Seen from in front of the car, looking back at the driver" in the prompt; otherwise the picture and the character face different ways.
- **A view through a moving window** (a car's rear or side window, a train) is two kinds of picture. The plate holds only what is effectively at infinity: the sky, the horizon, far mountains, the sea. Everything near or in the middle distance (roadside trees, poles, fences, road markings) is a separate transparent prop, one per object, which the scene moves past in perspective. A plate with near trees painted in stays still while the poles move, and reads as broken. The plate's prompt:

  > a hot late afternoon in a dry southern landscape. A distant landscape seen far away: the sky and the horizon with far mountains, empty flat land or calm sea stretching to the horizon, everything small and far, nothing in the foreground or the middle distance, no trees, no poles, no fences, no road, no buildings, no car parts, no window frame, no people, no text. Look: <the film's look>. --ar 16:9

  and each roadside object's (one per picture, two or three variants of a tree):

  > an olive tree. A single roadside object standing upright, whole and centred with its base on the bottom edge of a square frame, seen from the road at eye level, isolated on a plain flat white background, no ground, no cast shadow, no text. Look: <the film's look>. --ar 1:1
- For a character, make the reference sheet first, then ask for every other picture of it with that sheet as the reference image (Midjourney `--oref` in V7, `--cref` in V6; an edit in ChatGPT), so it stays the same person.
- Give the writer the prompts in a list they can copy, one code block per picture, each headed with the file it becomes.

<!-- art:begin (generated by tests/test_production_pack_skill.py; do not edit by hand) -->
### What each picture must show

#### Sky (the farthest plate) (`sky`)

- **Goes to:** assets/environments/<set>/plates/<layer>.png (or .jpg; an image plane in meta.json)
- **Canvas:** 16:9, at least 1920x1080; the camera barely moves it (depth 0 to 0.2)
- **Background:** opaque
- Sky only: its colours, clouds, sun or moon, stars.
- No ground, buildings or horizon objects: those are the next layers.
- **Prompt words** (after the subject): An empty sky filling the whole frame, no ground, no horizon, no buildings, no people, no text. (Midjourney: `--ar 16:9`)

#### Far layer (distant hills, skyline, sea) (`far`)

- **Goes to:** assets/environments/<set>/plates/<layer>.png (or .jpg; an image plane in meta.json)
- **Canvas:** wide: about 2560x1080 (21:9), wider still when the camera pans; parallax depth about 0.4
- **Background:** transparent above its top edge, so the sky shows through (or a plain flat colour there, cut out afterwards)
- Only what is far away, as one band across the whole width.
- The horizon at the same height from left to right.
- **Then:** ready if its background is transparent; a flat background is cut out by the pipeline owner first (cutan.carve).
- **Prompt words** (after the subject): A wide horizontal band of distant scenery across the whole width, horizon level and at the same height throughout, nothing in the foreground, no people, empty plain flat white sky above it, no text. (Midjourney: `--ar 21:9`)

#### Mid layer (the set the characters stand in) (`mid`)

- **Goes to:** assets/environments/<set>/plates/<layer>.png (or .jpg; an image plane in meta.json)
- **Canvas:** wide: about 2560x1080 (21:9), enough to cover the frame and the camera's pan; depth 1 (moves with the characters)
- **Background:** transparent where the far layer and sky should show
- The street, room or landscape the characters stand in, at their scale.
- The floor line about three-quarters of the way down.
- The middle third left quiet: the characters stand and talk there.
- No characters in it.
- **Then:** ready if its background is transparent; a flat background is cut out by the pipeline owner first (cutan.carve).
- **Prompt words** (after the subject): A stage-like set seen straight on at eye level, the floor line three-quarters of the way down, the centre left open and uncluttered for characters, no people, no animals, no text. (Midjourney: `--ar 21:9`)

#### Near layer (foreground in front of the characters) (`near`)

- **Goes to:** assets/environments/<set>/plates/<layer>.png (or .jpg; an image plane in meta.json); listed after the environment's characters_after plane
- **Canvas:** the frame's width or wider (16:9 or 21:9)
- **Background:** transparent everywhere except the foreground object
- What is in front of the characters: a railing, a bush, a counter, a car's dashboard and window frames.
- Kept to the edges and bottom of the frame so it does not hide faces.
- Anything around a character (a dashboard, a seat, a steering wheel) drawn from the camera's viewpoint relative to that character, stated in the prompt.
- **Then:** ready if its background is transparent; a flat background is cut out by the pipeline owner first (cutan.carve).
- **Prompt words** (after the subject): A foreground element along the bottom edge of the frame, the rest of the picture plain flat white and empty, seen from <where the camera is relative to the characters, e.g. in front of the car looking back at the driver>, no people, no text. (Midjourney: `--ar 16:9`)

#### The view through a moving window (a car's rear or side window, a train) (`window_view`)

- **Goes to:** assets/environments/<set>/plates/<layer>.png (or .jpg; an image plane in meta.json); its own plate, behind the vehicle's interior plate
- **Canvas:** 16:9, at least 1920x1080 behind a rear window or windscreen (what is at infinity does not move); a strip 2 to 3 frames wide behind a side window, for a slow drift
- **Background:** opaque
- Only what is effectively at infinity: the sky, the horizon, far mountains, the sea, a distant skyline.
- Nothing near or in the middle distance: no roadside trees, poles, fences, road markings or nearby buildings. Those are separate transparent props (`roadside`) that the scene moves in perspective (an#484): painted into the plate they stay still while the poles move, and the shot reads as broken.
- No car parts, no window frame, no reflections: the car's interior is a separate near-layer picture with the glass left empty.
- **Prompt words** (after the subject): A distant landscape seen far away: the sky and the horizon with far mountains, empty flat land or calm sea stretching to the horizon, everything small and far, nothing in the foreground or the middle distance, no trees, no poles, no fences, no road, no buildings, no car parts, no window frame, no people, no text. (Midjourney: `--ar 16:9`)

#### Roadside objects for a moving view (a tree, a pole, a fence, a road dash) (`roadside`)

- **Goes to:** assets/props/<object>/parts/<object>.png, one prop per object
- **Canvas:** square, 1024x1024, like any prop; the object standing on the bottom edge
- **Background:** transparent (or a plain flat white, cut out afterwards)
- One object per picture, whole, upright, its base on the bottom edge.
- Seen from the angle the window sees it: side-on through a side window; from the road, straight on, through a rear window or windscreen.
- Two or three variants of what repeats (trees of different shapes) so the stream does not look stamped.
- No ground under it, no cast shadow.
- **Then:** the scene moves each one past the window in perspective (written as moves in scene.md today; a declarative travelling view is an#484).
- **Prompt words** (after the subject): A single roadside object standing upright, whole and centred with its base on the bottom edge of a square frame, seen from the road at eye level, isolated on a plain flat white background, no ground, no cast shadow, no text. (Midjourney: `--ar 1:1`)

#### A prop (any object a scene shows) (`prop`)

- **Goes to:** assets/props/<prop>/parts/<prop>.png (in prop.json's skin)
- **Canvas:** square, 1024x1024; the object fills the square
- **Background:** transparent (or a plain flat white, cut out afterwards)
- One object per picture, whole, not cropped.
- Seen from the angle the scene shows it.
- No cast shadow on a floor, no hands holding it.
- Moving pieces (a lid, a door) as separate pictures.
- **Then:** ready if its background is transparent; a flat background is cut out by the pipeline owner first (cutan.carve).
- **Prompt words** (after the subject): A single object, whole and centred, filling a square frame, seen from the angle it is used at, nothing else in the picture, isolated on a plain flat white background, no cast shadow, no text. (Midjourney: `--ar 1:1`)

#### A vehicle seen from outside (a car in three-quarter view) (`vehicle`)

- **Goes to:** assets/props/<car>/parts/<car>.png
- **Canvas:** square, 1024x1024, like any prop; the car fills the width, the space above it empty
- **Background:** transparent (or a plain flat white, cut out afterwards)
- The whole vehicle in three-quarter front view, wheels on one level line.
- Nobody inside: windows dark or empty, so characters can be placed.
- Wheels that must turn as separate pictures, seen at the same angle.
- **Then:** ready if its background is transparent; a flat background is cut out by the pipeline owner first (cutan.carve).
- **Prompt words** (after the subject): A whole car in three-quarter front view, filling the width of a square frame, wheels level, nobody inside, isolated on a plain flat white background, no road, no cast shadow, no text. (Midjourney: `--ar 1:1`)

#### A character reference sheet (`character_sheet`)

- **Goes to:** reference/<name>-sheet.png (a folder the scene does not use; PRODUCTION.md lists it)
- **Canvas:** landscape, about 3000x1500, the views side by side
- **Background:** plain flat white
- The same character in front, three-quarter, side and back views, full body, at the same scale and in the same light.
- Standing straight, arms hanging a little away from the body, legs a little apart, so each limb can be cut out.
- A face sheet on its own: eyes open and closed, and the mouth shapes (closed, slightly open, wide open, O, E, F/V, M/B/P, L, rest).
- No text labels, no props in the hands.
- **Then:** the pipeline owner cuts it into parts (cutan.carve) and rigs it by hand: allow for that work (cutan#92).
- **Prompt words** (after the subject): A character turnaround sheet: front, three-quarter, side and back views side by side, full body, same scale and lighting in every view, standing straight with arms slightly away from the body and legs slightly apart, plain flat white background, no text, no labels. (Midjourney: `--ar 2:1`)

#### Character parts (a puppet in pieces) (`character_parts`)

- **Goes to:** reference/<name>-parts/<part>.png; the pipeline owner builds the art package from them (`an character contract`)
- **Canvas:** each part on its own canvas, all at the same scale
- **Background:** transparent
- Head (no eyes or mouth drawn on it), torso, each arm, each leg; eyes open and closed; nine mouth shapes.
- Each limb with a little extra at the joint so the pieces overlap.
- A part that replaces a factory character's own is a PNG with alpha named like the factory's SVG (`assets/characters/<name>/parts/head.png` for `parts/head.svg`).
- **Then:** the pipeline owner assembles the art package (character.json).
- **Prompt words** (after the subject): A single body part of a cut-out puppet, isolated on a plain flat white background, flat even lighting, no text. (Midjourney: `--ar 1:1`)

#### A costume (`costume`)

- **Goes to:** reference/<name>-costume.png, or on the reference sheet; colours in PRODUCTION.md
- **Canvas:** as the reference sheet, or close-ups at 1024x1024
- **Background:** plain flat white
- For a factory character: the colours by name or hex for the clothing, accessory and legs (the cast line's --palette).
- For a drawn character: the costume on the reference sheet, with close-ups of a hat, a pattern or a badge.
- A costume change is a second reference sheet.
- **Then:** the pipeline owner applies it.
- **Prompt words** (after the subject): A costume design sheet: the outfit laid out flat from the front, with close-ups of its details, plain flat white background, no text. (Midjourney: `--ar 1:1`)

### Each named style's look, in words

| style | look (paste after `Look:`) |
|---|---|
| `gilliam` | Victorian engraving and vintage photograph collage, hand-tinted sepia colours, visible scissor-cut paper edges, surreal and theatrical, lit from above |
| `kurzgesagt` | flat vector illustration, clean geometric shapes, no outlines, soft gradients, vivid saturated colours with soft glowing highlights, rounded corners, deep blue night tones |
| `marionette` | wooden marionette puppet on thin strings, jointed limbs, painted wood and cloth, a puppeteer's control bar above, theatre lighting |
| `norstein` | painted multiplane cut-out, soft gouache and watercolour textures, muted earthy colours, misty translucent tracing-paper layers, soft edges, hushed atmosphere |
| `oversimplified` | flat 2D vector cartoon, bold simple shapes, muted earthy palette (brick red, sage green, ochre), thin dark outlines, minimal detail, no shading |
| `reiniger` | black paper silhouette cut-out, intricate lace-like scissor-cut edges, pure flat black shapes with no inner detail, backgrounds of graded pastel or translucent coloured paper |
| `south_park` | construction-paper cut-out look, simple round and geometric shapes, flat solid colours, thin near-black outlines, faint paper grain, no shading, no gradients, no perspective |

### Generators

- **midjourney:** append the aspect (--ar 16:9 for a plate, --ar 1:1 for a prop) and --no text, letters, watermark; it cannot make a transparent background, so ask for a plain flat white one; keep a character consistent with a reference image (--oref <image URL> in V7, --cref in V6).
- **gpt-image:** ChatGPT's image tool (gpt-image): write the prompt as plain sentences; it can make a transparent PNG when asked ('transparent background, PNG'); ask for edits of the same image to keep a character consistent.
- **flux:** no negative prompt, and naming a thing tends to add it: use the positive-only prompt (image_prompt(..., tool='flux') drops the 'no ...' words); give the size as an aspect (16:9, 1:1); a flat plain background, cut out afterwards.
- **ideogram:** good at following a long description; switch magic prompt off so your words stay yours; ask for no text in the image.
- **recraft:** can draw in a vector style and export SVG, which suits the flat looks (South Park-like, OverSimplified-like, Kurzgesagt-like); an SVG it exports must still follow the pack's SVG rules (no embedded images).

### Drawings made on paper

- Draw each piece on its own sheet, or spread pieces out with a hand's width of empty paper between them.
- Use plain white or pale paper, and a background colour that appears nowhere in the drawing; strong, closed outlines cut out cleanest.
- Scan at 300 dpi, or photograph straight down in even daylight: no shadow of the phone or the hand, no glare, no perspective, the sheet filling the frame.
- Cut-paper pieces (actual scissors and card) are welcome: photograph them flat on a contrasting background.
- Send the original files (PNG or JPEG), not screenshots; the pipeline owner cuts the pieces out (cutan.carve) and keeps who drew them and on what terms.
<!-- art:end -->
