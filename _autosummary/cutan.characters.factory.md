# cutan.characters.factory

High-level entry points: build and inspect a character.

The [`new_character()`](#cutan.characters.factory.new_character) function wires together fetching/wrapping art,
slicing it into per-part SVGs, generating the default mouth set, and
writing a complete character directory + `character.json` descriptor.

Checking one is [`cutan.characters.validate`](cutan.characters.validate.md#module-cutan.characters.validate)’s job, not this module’s — it
opens every part and reports `an.verify._base.Finding` s, so a character
problem routes the way every other verifier’s does (an#78).

```pycon
>>> import tempfile
>>> with tempfile.TemporaryDirectory() as d:
...     descriptor_path = new_character(d, name='nobody', use_dicebear=False)
...     descriptor_path.parent.name, descriptor_path.name
('nobody', 'character.json')
```

### Module Attributes

| [`PALETTE_ROLES`](#cutan.characters.factory.PALETTE_ROLES)            | The roles `new_character(palette=...)` takes.                                                                                                                                                                                                                                                                                                               |
|---------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`HEAD_ART_ROLES`](#cutan.characters.factory.HEAD_ART_ROLES)           | The roles a head's own art carries.                                                                                                                                                                                                                                                                                                                         |
| [`OUTLINE_COLOUR`](#cutan.characters.factory.OUTLINE_COLOUR)           | it is the drawing's ink, not a costume colour.                                                                                                                                                                                                                                                                                                              |
| [`SHOE_COLOUR`](#cutan.characters.factory.SHOE_COLOUR)              | The shoe, drawn in the leg part.                                                                                                                                                                                                                                                                                                                            |
| [`PUPIL_COLOUR`](#cutan.characters.factory.PUPIL_COLOUR)             | The pupil, in its own part (or the pre-gaze open eye).                                                                                                                                                                                                                                                                                                      |
| [`DFLT_HAND_COLOUR`](#cutan.characters.factory.DFLT_HAND_COLOUR)         | Default hand, trouser and brow colours — the literals the factory always drew.                                                                                                                                                                                                                                                                              |
| [`HATS`](#cutan.characters.factory.HATS)                     | The hats [`new_character()`](#cutan.characters.factory.new_character) can draw.                                                                                                                                                                                                                                                                         |
| [`FACTORY_ART_PROVENANCE`](#cutan.characters.factory.FACTORY_ART_PROVENANCE)   | The `art_provenance` of a head the factory drew (its knobs re-draw it).                                                                                                                                                                                                                                                                                     |
| [`HAIR_STYLES`](#cutan.characters.factory.HAIR_STYLES)              | `peak` (the factory's original hair, a widow's peak — the default), `bald`, `bun` (the hair gathered in a bun on the crown) and `curly` (a halo of curls around the crown).                                                                                                                                                                                 |
| [`HAIR_LENGTHS`](#cutan.characters.factory.HAIR_LENGTHS)             | `short` (nothing below the crown — the default), `medium` (falling beside the face to the jaw) and `long` (past the chin, in locks that keep clear of the neck and the collar).                                                                                                                                                                             |
| [`MAX_HEAD_SCALE`](#cutan.characters.factory.MAX_HEAD_SCALE)           | The largest head scale accepted — past it the head no longer fits the 1024-unit view box above a regular body.                                                                                                                                                                                                                                              |
| [`BUILDS`](#cutan.characters.factory.BUILDS)                   | Named builds.                                                                                                                                                                                                                                                                                                                                               |
| [`RECIPE_KEY`](#cutan.characters.factory.RECIPE_KEY)               | every drawing call that made the character, in order, with its parameters — so the factory's bytes can be re-derived anywhere ([`redraw_digests()`](#cutan.characters.factory.redraw_digests)).                                                                                                                                                          |
| [`RECIPE_VERSION`](#cutan.characters.factory.RECIPE_VERSION)           | The version of the recipe's format.                                                                                                                                                                                                                                                                                                                         |
| [`FACTORY_AUTHOR`](#cutan.characters.factory.FACTORY_AUTHOR)           | The provider of every per-part source the factory stamps on what it draws.                                                                                                                                                                                                                                                                                  |
| [`EYE_CANVAS`](#cutan.characters.factory.EYE_CANVAS)               | The eye's geometry in its 64x32 canvas, shared by the four synthesizers so the sclera, the pupil and the lid outline agree (an#99).                                                                                                                                                                                                                         |
| [`LID_COVER_PAD`](#cutan.characters.factory.LID_COVER_PAD)            | How much farther than the eye white the FILLED closed lid reaches, in eye view-box units (cutan#66).                                                                                                                                                                                                                                                        |
| [`GAZE_PARTS`](#cutan.characters.factory.GAZE_PARTS)               | The parts a rig gains with `an character add-gaze`.                                                                                                                                                                                                                                                                                                         |
| [`FACE_SLOTS`](#cutan.characters.factory.FACE_SLOTS)               | The face slots of the default rig with the eye stack (an#99).                                                                                                                                                                                                                                                                                               |
| [`SIDE_EYE_SHIFT`](#cutan.characters.factory.SIDE_EYE_SHIFT)           | how far the near eye, its stack and brow slide toward the face's edge, and the mouth with them (view_box units at head_scale 1); the mouth is narrowed, seen edge-on.                                                                                                                                                                                       |
| [`SIDE_LEG_OFFSET`](#cutan.characters.factory.SIDE_LEG_OFFSET)          | both hang from under the body, the near leg (`leg_r`, drawn over the far one) a little forward and the far leg a little back, overlapping at the hip — each hip sits `SIDE_LEG_OFFSET` leg widths off the centre line — and splayed so the FEET part: the shoe centres land `SIDE_FOOT_SPREAD` leg widths apart, on every build (a stubby leg splays more). |
| [`THREE_QUARTER_FACE_SHIFT`](#cutan.characters.factory.THREE_QUARTER_FACE_SHIFT) | the whole face slides toward the facing side, the far eye narrows, the far arm tucks in toward the body and the legs in.                                                                                                                                                                                                                                    |
| [`MAX_RECIPE_STEPS`](#cutan.characters.factory.MAX_RECIPE_STEPS)         | The most drawing steps a recipe may replay, and the most bytes of JSON its parameters may take: the replay runs on whoever reads the descriptor, so its cost is bounded here, not by the recipe's author (review-292 R3).                                                                                                                                   |

### Functions

| [`add_gaze`](#cutan.characters.factory.add_gaze)(char_dir, \*[, skin, overwrite_eyes])   | Give a character the eye stack (an#99): three sibling slots per eye under the head — `<side>_sclera` (white fill) below `<side>_pupil` below `<side>_eye` (the existing slot, now the lid, drawn above the pupil) — with synthesized parts, an outline-only open eye, a FILLED closed lid, the `gaze_travel` clamp, and draw orders that put the lid over the pupil.                                  |
|---------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`add_views`](#cutan.characters.factory.add_views)(char_dir)                              | Give a factory character its turnaround (an#197): `back`, `side` and `three_quarter` head and torso art beside the front, a `view` swap set projected onto those two slots, and a pose per view (`swap_poses`) — so `{kind: set, target: <entity>, property: view, value: side}` or [`cutan.motion.turn()`](cutan.motion.md#cutan.motion.turn) turns the whole character. |
| [`brow_cover_unknowable`](#cutan.characters.factory.brow_cover_unknowable)(desc)                      | Whether `desc` is a factory head with a hat whose drawing is not the factory's for its recorded knobs (edited by hand), so its brow cover cannot be derived: only a declared `occluded` can say (an#284).                                                                                                                                                                                             |
| [`declare_mouth_variants`](#cutan.characters.factory.declare_mouth_variants)(descriptor, variants)     | Declare a `viseme@<form>` set per variant on `descriptor` — the set's keys map to `mouth_<shape>_<form>` attachments, which are added to the default skin's `mouth` slot with the neutral mouth's geometry.                                                                                                                                                                                           |
| [`derived_brow_cover`](#cutan.characters.factory.derived_brow_cover)(desc)                         | What covers a FACTORY head's brows, derived from its recorded knobs (an#284, ADR 0002 decision 2): its hat, as drawn (`_worn_seat()`), measured against the brows' acting range ([`seat_overlap()`](cutan.characters.brows.md#cutan.characters.brows.seat_overlap)).                                                                                                                |
| [`factory_descriptor_source`](#cutan.characters.factory.factory_descriptor_source)(source_svg)            | The descriptor-level source of a character this factory drew, pinned to its drawing.                                                                                                                                                                                                                                                                                                                  |
| [`factory_source`](#cutan.characters.factory.factory_source)(data)                             | The per-part source of a part this factory drew, pinned to its bytes.                                                                                                                                                                                                                                                                                                                                 |
| [`gaze_travel_for`](#cutan.characters.factory.gaze_travel_for)([rx, ry, pupil_r])               | The pupil's travel per axis, in view-box units: the sclera's clearance minus the pupil's radius — the semi-axes of the inner ellipse the gaze axes' unit circle maps onto.                                                                                                                                                                                                                            |
| [`new_character`](#cutan.characters.factory.new_character)(out_dir, \*, name[, seed, ...])    | Build a complete character on disk.                                                                                                                                                                                                                                                                                                                                                                   |
| [`recording_drawn`](#cutan.characters.factory.recording_drawn)(char_dir)                        | Log what the body writes, then record the factory-stamped bytes it wrote at `char_dir`.                                                                                                                                                                                                                                                                                                               |
| [`redraw_digests`](#cutan.characters.factory.redraw_digests)(descriptor)                       | `{path: sha256}` of every file the factory draws from `descriptor`'s recipe (an#292).                                                                                                                                                                                                                                                                                                                 |
| [`scale_part_files`](#cutan.characters.factory.scale_part_files)(paths, scale)                   | Rewrite each part SVG's root size by `scale` (its drawing untouched): the compiler draws a part at its own raster size, so that IS its size on screen.                                                                                                                                                                                                                                                |
| [`stage_extent`](#cutan.characters.factory.stage_extent)(desc)                               | How far a character's art reaches above and below its stage point, in scene pixels at `stage.scale: 1`: `{"top", "feet", "height"}`.                                                                                                                                                                                                                                                                  |
| [`stamp_factory_descriptor`](#cutan.characters.factory.stamp_factory_descriptor)(char_dir)               | Record the factory as the source of the character it just drew at `char_dir`.                                                                                                                                                                                                                                                                                                                         |
| [`stamp_factory_parts`](#cutan.characters.factory.stamp_factory_parts)(char_dir, paths, \*[, skip]) | Give each part the factory drew a `cc0` per-part source pinned to its digest.                                                                                                                                                                                                                                                                                                                         |
| [`stamp_generated_head`](#cutan.characters.factory.stamp_generated_head)(char_dir, source)           | Pin a generator's `source` (DiceBear's) to the bytes it produced at `char_dir`.                                                                                                                                                                                                                                                                                                                       |
| [`stand_on_feet`](#cutan.characters.factory.stand_on_feet)(char_dir, \*[, undo])              | Convert an existing character to stand on its feet (an#285), or back.                                                                                                                                                                                                                                                                                                                                 |
| [`view_poses`](#cutan.characters.factory.view_poses)([body, head_scale, slots])            | `{view: {slot: SlotPose}}` for the factory's rig built as `body` — what a view does besides swapping art: the back hides the face, the side hides the far eye and arm and slides the near eye and mouth to the profile edge.                                                                                                                                                                          |

### Classes

| [`BodyBuild`](#cutan.characters.factory.BodyBuild)([torso_size, torso_radius, ...])   | The proportions of a synthesized body, in view_box units.   |
|-----------------------------------------------------------------------------------------------|-------------------------------------------------------------|

### cutan.characters.factory.BUILDS *: [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [BodyBuild](#cutan.characters.factory.BodyBuild)]* *= {'regular': BodyBuild(torso_size=(256, 256), torso_radius=40, torso_inset_bottom=20, arm_width=36, arm_length=256, hand_radius=20, limb_stroke=4, leg_width=40, leg_length=300.0, shoe_size=(32, 18), shoulder=(90, 240), hip_x=50, neck_height=260), 'squat': BodyBuild(torso_size=(300, 220), torso_radius=80, torso_inset_bottom=4, arm_width=36, arm_length=140, hand_radius=18, limb_stroke=4, leg_width=50, leg_length=96, shoe_size=(34, 16), shoulder=(118, 168), hip_x=46, neck_height=214), 'stick': BodyBuild(torso_size=(170, 210), torso_radius=14, torso_inset_bottom=4, arm_width=10, arm_length=200, hand_radius=9, limb_stroke=3, leg_width=10, leg_length=230, shoe_size=(15, 7), shoulder=(82, 188), hip_x=28, neck_height=214), 'tall': BodyBuild(torso_size=(224, 320), torso_radius=36, torso_inset_bottom=4, arm_width=32, arm_length=320, hand_radius=18, limb_stroke=4, leg_width=36, leg_length=380, shoe_size=(30, 16), shoulder=(80, 304), hip_x=44, neck_height=324)}*

Named builds. `regular` is today’s body, number for number.

### *class* cutan.characters.factory.BodyBuild(torso_size=(256, 256), torso_radius=40, torso_inset_bottom=20, arm_width=36, arm_length=256, hand_radius=20, limb_stroke=4, leg_width=40, leg_length=300.0, shoe_size=(32, 18), shoulder=(90, 240), hip_x=50, neck_height=260)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

The proportions of a synthesized body, in view_box units.

Every length that decides where a part hangs is here, so the bones the
factory writes and the art it draws are derived from ONE record and cannot
disagree — a leg’s art is exactly `leg_length` tall and its bone sits
`leg_length` above the ground, so it hangs from the hip to the ground at
every build (tests/test_rig_layout.py).

#### arm_width *: [float](https://docs.python.org/3/builtins/functions.html#float)* *= 36*

Sleeve thickness and the arm canvas’s length (sleeve + hand).

#### hip_x *: [float](https://docs.python.org/3/builtins/functions.html#float)* *= 50*

The hip joints’ distance from the centre line.

#### neck_height *: [float](https://docs.python.org/3/builtins/functions.html#float)* *= 260*

The neck’s height above the hip; the head hangs above it.

#### shoulder *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[float](https://docs.python.org/3/builtins/functions.html#float), [float](https://docs.python.org/3/builtins/functions.html#float)]* *= (90, 240)*

The shoulder joint (x from the centre line, height above the hip).

#### torso_inset_bottom *: [float](https://docs.python.org/3/builtins/functions.html#float)* *= 20*

The gap between the drawn body and the canvas bottom (the hip). The
regular body’s 20 leaves a sliver between body and legs; the other
builds close it.

#### torso_size *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[float](https://docs.python.org/3/builtins/functions.html#float), [float](https://docs.python.org/3/builtins/functions.html#float)]* *= (256, 256)*

Torso canvas; the drawn body is inset 20 on every side, and the canvas
bottom sits on the hip.

### cutan.characters.factory.DFLT_HAND_COLOUR *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= '#f1c9a5'*

Default hand, trouser and brow colours — the literals the factory always drew.

### cutan.characters.factory.EYE_CANVAS *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[int](https://docs.python.org/3/builtins/functions.html#int), [int](https://docs.python.org/3/builtins/functions.html#int)]* *= (64, 32)*

The eye’s geometry in its 64x32 canvas, shared by the four synthesizers so
the sclera, the pupil and the lid outline agree (an#99).

### cutan.characters.factory.FACE_SLOTS *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), ...]* *= ('left_eye', 'right_eye', 'left_sclera', 'right_sclera', 'left_pupil', 'right_pupil', 'mouth', 'left_brow', 'right_brow')*

The face slots of the default rig with the eye stack (an#99).

### cutan.characters.factory.FACTORY_ART_PROVENANCE *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'fallback_geometric'*

The `art_provenance` of a head the factory drew (its knobs re-draw it).

### cutan.characters.factory.FACTORY_AUTHOR *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'an (generated locally)'*

The provider of every per-part source the factory stamps on what it draws.
The licence of the factory’s own drawings: no rights to clear.
Who the factory’s descriptor-level source names as the author.

### cutan.characters.factory.GAZE_PARTS *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), ...]* *= ('sclera_l', 'sclera_r', 'pupil_l', 'pupil_r')*

The parts a rig gains with `an character add-gaze`. Optional — never in
`REQUIRED_PARTS`: a pre-Wave-6 rig without them still renders, and gaze is
a no-op on it.

### cutan.characters.factory.HAIR_LENGTHS *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), ...]* *= ('short', 'medium', 'long')*

`short` (nothing below the crown — the default), `medium`
(falling beside the face to the jaw) and `long` (past the chin, in locks
that keep clear of the neck and the collar).

* **Type:**
  Hair lengths

### cutan.characters.factory.HAIR_STYLES *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), ...]* *= ('peak', 'bald', 'bun', 'curly')*

`peak` (the factory’s original hair, a widow’s peak — the
default), `bald`, `bun` (the hair gathered in a bun on the crown) and
`curly` (a halo of curls around the crown). Every style keeps the default
hairline over the forehead — none draws lower over the brows (tests) — so a
hair style never costs brow acting.

* **Type:**
  Hair styles

### cutan.characters.factory.HATS *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), ...]* *= ('none', 'cap', 'beanie', 'bowler', 'bicorne')*

The hats [`new_character()`](#cutan.characters.factory.new_character) can draw.

### cutan.characters.factory.HEAD_ART_ROLES *: [frozenset](https://docs.python.org/3/builtins/stdtypes.html#frozenset)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)]* *= frozenset({'hair', 'skin'})*

The roles a head’s own art carries. On a head the factory did not draw
(DiceBear) they are left untagged everywhere, never half-tagged.

### cutan.characters.factory.LID_COVER_PAD *: [int](https://docs.python.org/3/builtins/functions.html#int)* *= 3*

How much farther than the eye white the FILLED closed lid reaches, in eye
view-box units (cutan#66). A lid exactly the sclera’s ellipse leaves the
white’s anti-aliased edge showing as a light ring round a closed eye:
measured at a 720p silhouette’s eye size (0.34 px a unit), a grey of 63 on
black with no pad, 4 with 2 units, none with 3.

### cutan.characters.factory.MAX_HEAD_SCALE *: [float](https://docs.python.org/3/builtins/functions.html#float)* *= 2.5*

The largest head scale accepted — past it the head no longer fits the
1024-unit view box above a regular body.

### cutan.characters.factory.MAX_RECIPE_STEPS *: [int](https://docs.python.org/3/builtins/functions.html#int)* *= 8*

The most drawing steps a recipe may replay, and the most bytes of JSON its
parameters may take: the replay runs on whoever reads the descriptor, so
its cost is bounded here, not by the recipe’s author (review-292 R3).

### cutan.characters.factory.OUTLINE_COLOUR *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= '#222222'*

it is the
drawing’s ink, not a costume colour.

* **Type:**
  The outline every synthesized body part is stroked in. Untagged

### cutan.characters.factory.PALETTE_ROLES *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), ...]* *= ('skin', 'hair', 'clothing', 'leg', 'accessory')*

The roles `new_character(palette=...)` takes. They are `StylePack` role
names on purpose: a palette chosen at authoring time and a pack applied at
compile time speak one vocabulary, and the factory records each as a colour
role so the pack can reach what the palette drew.

### cutan.characters.factory.PUPIL_COLOUR *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= '#1a1a1a'*

The pupil, in its own part (or the pre-gaze open eye). Role `pupil`.

### cutan.characters.factory.RECIPE_KEY *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'factory'*

every
drawing call that made the character, in order, with its parameters — so
the factory’s bytes can be re-derived anywhere ([`redraw_digests()`](#cutan.characters.factory.redraw_digests)).

* **Type:**
  The descriptor `metadata` key holding the factory’s recipe (an#292)

### cutan.characters.factory.RECIPE_VERSION *: [int](https://docs.python.org/3/builtins/functions.html#int)* *= 1*

The version of the recipe’s format.

### cutan.characters.factory.SHOE_COLOUR *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= '#1a1a1a'*

The shoe, drawn in the leg part. Untagged.

### cutan.characters.factory.SIDE_EYE_SHIFT *: [float](https://docs.python.org/3/builtins/functions.html#float)* *= 14.0*

how far the near eye, its stack and brow slide toward
the face’s edge, and the mouth with them (view_box units at head_scale 1);
the mouth is narrowed, seen edge-on.

* **Type:**
  Profile (facing right)

### cutan.characters.factory.SIDE_LEG_OFFSET *: [float](https://docs.python.org/3/builtins/functions.html#float)* *= 0.25*

both hang from under the body, the near leg
(`leg_r`, drawn over the far one) a little forward and the far leg a
little back, overlapping at the hip — each hip sits `SIDE_LEG_OFFSET` leg
widths off the centre line — and splayed so the FEET part: the shoe centres
land `SIDE_FOOT_SPREAD` leg widths apart, on every build (a stubby leg
splays more). Both legs show, even as one silhouette, and a walk in profile
has two legs to alternate (an#203). A stick leg is thinner than its shoe,
so leg widths alone would leave the two shoes on top of each other — a
one-legged stand; the shoes part by at least `SIDE_FOOT_MIN_SHOES` shoe
lengths (a floor every other build already clears, so they are unchanged).

* **Type:**
  Profile legs (facing right)

### cutan.characters.factory.THREE_QUARTER_FACE_SHIFT *: [float](https://docs.python.org/3/builtins/functions.html#float)* *= 20.0*

the whole face slides toward the facing side,
the far eye narrows, the far arm tucks in toward the body and the legs in.

* **Type:**
  Three-quarter (facing right)

### cutan.characters.factory.add_gaze(char_dir, , skin=None, overwrite_eyes=False)

Give a character the eye stack (an#99): three sibling slots per eye under
the head — `<side>_sclera` (white fill) below `<side>_pupil` below
`<side>_eye` (the existing slot, now the lid, drawn above the pupil) —
with synthesized parts, an outline-only open eye, a FILLED closed lid, the
`gaze_travel` clamp, and draw orders that put the lid over the pupil.
Idempotent: a rig that already has the stack is rewritten to the same
state. Returns the descriptor path.

The open and closed eye parts are REWRITTEN (outline-only, filled lid), so
on a rig whose eyes are not this factory’s drawings — a promoted hand rig —
it refuses unless `overwrite_eyes=True`: the stack’s geometry is the
synthesized eye’s, and an illustrator’s eyes would be silently replaced
(an#99 review). Such a rig wants its own outline-only open eye, filled
lid, sclera and pupil parts drawn to its own geometry.

This is the **expand** step for a pre-Wave-6 descriptor: no migration
inserts pupil slots, because their art would be absent and absent art is
fatal under `strict_assets` — every existing character would stop
rendering on the bench.

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

### cutan.characters.factory.add_views(char_dir)

Give a factory character its turnaround (an#197): `back`, `side` and
`three_quarter` head and torso art beside the front, a `view` swap set
projected onto those two slots, and a pose per view (`swap_poses`) — so
`{kind: set, target: <entity>, property: view, value: side}` or
[`cutan.motion.turn()`](cutan.motion.md#cutan.motion.turn) turns the whole character. Idempotent. Returns the
descriptor path.

The views are REDRAWN from the recorded knobs (seed, palette, build, hat,
hair style and length, sash, head scale), so it refuses a rig whose head is not this factory’s
drawing for them — a DiceBear head (its face is baked, and there is no
back of it to draw), a promoted hand rig, or an edited head: its views are
an illustrator’s to draw, declared the same way (a `view` set whose keys
name attachments on the head and torso slots, and `swap_poses`).

Every colour is role-tagged like the front’s, so a StylePack recolours the
views exactly as it recolours the front (an#191). The existing art is not
touched: a shot that never sets a view renders byte-identically.

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

### cutan.characters.factory.brow_cover_unknowable(desc)

Whether `desc` is a factory head with a hat whose drawing is not the
factory’s for its recorded knobs (edited by hand), so its brow cover cannot
be derived: only a declared `occluded` can say (an#284).

* **Return type:**
  [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

### cutan.characters.factory.declare_mouth_variants(descriptor, variants)

Declare a `viseme@<form>` set per variant on `descriptor` — the set’s
keys map to `mouth_<shape>_<form>` attachments, which are added to the
default skin’s `mouth` slot with the neutral mouth’s geometry. The
neutral set is the SSOT for which shapes exist; a variant mirrors it.

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### cutan.characters.factory.derived_brow_cover(desc)

What covers a FACTORY head’s brows, derived from its recorded knobs
(an#284, ADR 0002 decision 2): its hat, as drawn (`_worn_seat()`),
measured against the brows’ acting range
([`seat_overlap()`](cutan.characters.brows.md#cutan.characters.brows.seat_overlap)). `None` when nothing does,
when the head is not the factory’s (drawn art: an illustrator declares
`occluded`), or when it cannot be told (an edited factory head).

Derived, never stored: a character made before hats were seated (an#252)
reports the brim that covers its brows, and the answer follows the
measurement if the brows’ range moves.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### cutan.characters.factory.factory_descriptor_source(source_svg)

The descriptor-level source of a character this factory drew, pinned to its drawing.

The digest is that of the descriptor’s `source_svg` — the drawing every
part was cut from. Like a part stamp it speaks only for bytes it pins: the
asset library and `an credits` read every file of the character that no
stamp pins (a part re-carved later, a file added by hand) as UNVERIFIED,
never as the factory’s (`an.credits._part_credits()`).

* **Return type:**
  `AssetSource`

```pycon
>>> s = factory_descriptor_source(b"<svg/>")
>>> (s.provider, s.license, len(s.sha256))
('an character factory', 'cc0-1.0', 64)
```

### cutan.characters.factory.factory_source(data)

The per-part source of a part this factory drew, pinned to its bytes.

* **Return type:**
  `AssetSource`

```pycon
>>> factory_source(b"<svg/>").license, len(factory_source(b"<svg/>").sha256)
('cc0-1.0', 64)
```

### cutan.characters.factory.gaze_travel_for(rx=14, ry=10, pupil_r=5)

The pupil’s travel per axis, in view-box units: the sclera’s clearance
minus the pupil’s radius — the semi-axes of the inner ellipse the gaze
axes’ unit circle maps onto. The compiler clamps the summed gaze to 0.95
of that circle (`GAZE_ELLIPSE_MARGIN`), which is what keeps the pupil disc
inside the white at every angle without a runtime mask.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`float`](https://docs.python.org/3/builtins/functions.html#float)]

```pycon
>>> gaze_travel_for()
{'x': 9.0, 'y': 5.0}
```

### cutan.characters.factory.new_character(out_dir, , name, seed=None, style='lorelei', voice_ref=None, use_dicebear=True, acknowledge_attribution=False, overwrite=False, mouth_variants=None, gaze=True, palette=None, build='regular', head_scale=1.0, hat='none', sash=False, views=True, hair_style='peak', hair_length='short', feet_origin=False)

Build a complete character on disk.

**Variety knobs** (every default reproduces the pre-knob character byte for
byte, which a golden test holds):

- `palette` — `{role: "#rrggbb"}` over [`PALETTE_ROLES`](#cutan.characters.factory.PALETTE_ROLES) (`skin`,
  `hair`, `clothing`, `leg`, `accessory`) — the SAME role names a
  `StylePack` uses. Unset roles keep the seed’s colours.
  > `skin` also paints the hands and the gaze lid; `hair` the brows and
  > the collar. On a DiceBear head only the body follows (its face is baked).
- `build` — a key of [`BUILDS`](#cutan.characters.factory.BUILDS): `regular`, `squat` (round body,
  short legs), `tall`, `stick` (small blocky body, stick limbs).
- `head_scale` — the head and its whole face (eyes, brows, mouths, their
  offsets, the pupil travel) scaled together, so a big head keeps its face.
- `hat` — a key of [`HATS`](#cutan.characters.factory.HATS) (offline head only), in `accessory`,
  worn above the brows’ acting range at this head scale (an#252): lifted,
  and flattened toward its crown when lifting is not enough. A hat that
  still covers the brows (a very small head) is recorded in the
  descriptor’s `occluded`, so the character does not afford
  `face.brows` and expressions fall to the lids, gaze and mouth.
- `hair_style` — [`HAIR_STYLES`](#cutan.characters.factory.HAIR_STYLES): `peak` (the default), `bald`,
  `bun`, `curly`; `hair_length` — [`HAIR_LENGTHS`](#cutan.characters.factory.HAIR_LENGTHS): `short`
  (the default), `medium`, `long` (offline head only). Drawn in the
  `hair` role (the palette’s `hair` colours them), in every view.
- `sash` — a diagonal band across the torso, in `accessory`.
- `views` (an#197) — draw the turnaround: `back`, `side` (a profile
  facing the viewer’s right) and `three_quarter` beside the front, as a
  `view` swap set with a pose per view ([`add_views()`](#cutan.characters.factory.add_views)), so
  [`cutan.motion.turn()`](cutan.motion.md#cutan.motion.turn) can turn the character around. Offline head only
  > (a DiceBear face is baked into its art); ignored for a DiceBear head.

  Additive: a shot that never sets a view renders exactly as without it.
- `feet_origin` (an#285) — declare the rig’s `origin` at its ROOT bone,
  the ground contact, so `stage.at` is where the feet stand and every
  build placed at one `y` stands on one line (`stage_extent`’s
  `feet` is then 0). `an character new` turns it on by default (the
  maintainer’s decision on an#423, 2026-10-09); here it stays off by
  default, so code that rebuilds a character (goldens, a recipe’s replay,
  the demos) draws exactly what it drew. [`stand_on_feet()`](#cutan.characters.factory.stand_on_feet) converts an
  existing character, one at a time.

Every colour the factory draws in a role is recorded in the descriptor’s
`colour_roles` so a style pack can recolour it later (palette swapping,
[`cutan.characters.colour_roles`](cutan.characters.colour_roles.md#module-cutan.characters.colour_roles)).

`gaze` (an#99) adds the eye stack — sclera and pupil slots under each
lid, a filled closed lid, the `gaze_travel` clamp — through
[`add_gaze()`](#cutan.characters.factory.add_gaze), so `gaze_x`/`gaze_y` and the ambient saccades reach the
pupils. Off, the eye is the single pre-stack drawing.

`mouth_variants` (an#98) — `{form: smile offset}` — writes one more
9-shape mouth set per form (`mouth_<shape>_<form>.svg`) and declares it
as the `viseme@<form>` swap set, with its attachments in the default
skin’s `mouth` slot, so an expression preset preferring that form
selects it. `None` means [`DEFAULT_MOUTH_VARIANTS`](cutan.characters.mouth_set.md#cutan.characters.mouth_set.DEFAULT_MOUTH_VARIANTS)
(happy, sad); `{}` means the neutral set only.

Steps:

1. Fetch a DiceBear avatar (skip if `use_dicebear=False` — useful for
   offline tests).
2. Wrap it into the canonical `an` cutout SVG (skeleton + illustration
   groups), saved as `<name>.svg`.
3. Slice each part into `parts/<part>.svg`.
4. Write the 9-shape default mouth set into `parts/mouth/`.
5. Synthesize a few derived parts (open/closed eyes, brows) so the
   character is complete out of the box.
6. Emit a `character.json` descriptor.

Returns the path to the created `character.json`.

Raises [`FileExistsError`](https://docs.python.org/3/builtins/exceptions.html#FileExistsError) if `out_dir/name` already exists and
`overwrite=False`.

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

### cutan.characters.factory.recording_drawn(char_dir)

Log what the body writes, then record the factory-stamped bytes it wrote at `char_dir`.

For a drawing path outside this module (`an character mouths`): only
bytes written through [`cutan.characters.drawn`](cutan.characters.drawn.md#module-cutan.characters.drawn) inside the block, and
stamped by the factory, are recorded.

### cutan.characters.factory.redraw_digests(descriptor)

`{path: sha256}` of every file the factory draws from `descriptor`’s recipe (an#292).

The factory is deterministic: replaying the recorded drawing calls, with
their recorded parameters, into a scratch folder re-derives the very
bytes — anywhere, on any machine. Whatever bytes it draws are the
factory’s own work, so a recipe can only ever confirm the factory’s
output: carved or hand-drawn bytes are never what it draws. `{}` when the
descriptor records no replayable recipe (none, an older format, a DiceBear
head, a parameter JSON could not hold). Memoised per recipe.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

### cutan.characters.factory.scale_part_files(paths, scale)

Rewrite each part SVG’s root size by `scale` (its drawing untouched):
the compiler draws a part at its own raster size, so that IS its size on
screen. Missing files are skipped.

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### cutan.characters.factory.stage_extent(desc)

How far a character’s art reaches above and below its stage point, in
scene pixels at `stage.scale: 1`: `{"top", "feet", "height"}`.

The stage point (`stage.at`) is the rig’s declared `origin` when it
has one (an#338); otherwise it is not the feet: the compiler places a rig
by the middle of its bones’ extent, between the neck and the feet, so
where the feet land depends on the build and the head scale (a squat
figure’s feet sit about half as far below the point as a tall one’s).
Read from the compiler’s own placement rule (`an.stage.rig.rig_origin`)
and the head’s art, so this is what the compiled scene does, not a second
guess at it. Multiply by
`stage.scale`. The head reaches its drawing’s top edge (a hat stays
inside it).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`float`](https://docs.python.org/3/builtins/functions.html#float)]

```pycon
>>> e = stage_extent(CharacterDescriptor(name="c"))
>>> round(e["top"]), round(e["feet"])
(169, 94)
```

### cutan.characters.factory.stamp_factory_descriptor(char_dir)

Record the factory as the source of the character it just drew at `char_dir`.

Only a descriptor that declares no source is stamped (a DiceBear head
carries DiceBear’s); the stamp pins the bytes of its `source_svg`. Called
by [`new_character()`](#cutan.characters.factory.new_character) on what it has just drawn, never on a character
someone may have edited since.

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

### cutan.characters.factory.stamp_factory_parts(char_dir, paths, , skip=())

Give each part the factory drew a `cc0` per-part source pinned to its digest.

Rights in the asset library attach to the BYTES (an#236): a file is as
restricted as the strictest thing any library says about its SHA-256, and an
asset-level licence speaks for every file the asset does not itemise. The
factory’s parts are byte-identical across characters (the default mouths,
the eyes), so without this stamp a carved character built on a factory body
would make every other character’s shared parts private. The stamp pins the
digest, so a part later re-drawn or re-carved no longer matches it and stops
being itemised as the factory’s — the stamp cannot launder new bytes.

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

paths: the relative paths this call has just DRAWN — required (an#249
: R4-N1): a stamp says “the factory made these bytes”, so only the code
  that made them may write it. Stamping every part by default would label
  a part re-carved since as the factory’s `cc0`. A part carrying some
  other provider’s source is never re-stamped.

### cutan.characters.factory.stamp_generated_head(char_dir, source)

Pin a generator’s `source` (DiceBear’s) to the bytes it produced at `char_dir`.

The head part(s) the generator drew (`parts/head.svg`) carry the source
with their own digest, and the descriptor carries it with the digest of its
`source_svg`. Like the factory’s stamps, it then speaks only for those
bytes: a part re-carved since, or a file added, is UNVERIFIED in `an
credits` and `unknown` in the asset library. Called by
[`new_character()`](#cutan.characters.factory.new_character) on what it has just written.

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

### cutan.characters.factory.stand_on_feet(char_dir, , undo=False)

Convert an existing character to stand on its feet (an#285), or back.

Declares the rig’s `origin` at its ROOT bone, the ground contact, the
way `an character new` does for a new character: `stage.at` is then
where its feet stand. Existing characters are never converted implicitly
(that would move them in every scene already made), so this is the opt-in,
one character at a time. `undo` removes the declared origin, back to the
middle of the bones.

Only `character.json`’s `origin` changes; every other key is kept as
written. Returns `{"before", "after"}` ([`stage_extent()`](#cutan.characters.factory.stage_extent) of each)
and `shift`: how many scene pixels (at `stage.scale: 1`) to ADD to the
character’s `stage.at` y in a scene made before, to keep it where it
stood (negative after `undo`).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### cutan.characters.factory.view_poses(body=BodyBuild(torso_size=(256, 256), torso_radius=40, torso_inset_bottom=20, arm_width=36, arm_length=256, hand_radius=20, limb_stroke=4, leg_width=40, leg_length=300.0, shoe_size=(32, 18), shoulder=(90, 240), hip_x=50, neck_height=260), , head_scale=1.0, slots=None)

`{view: {slot: SlotPose}}` for the factory’s rig built as `body` — what
a view does besides swapping art: the back hides the face, the side hides
the far eye and arm and slides the near eye and mouth to the profile edge.

Face offsets scale with `head_scale` (the face was drawn at it), limb
offsets come from the build’s own joints. `slots` limits the poses to the
slots a rig has (a rig without the eye stack has no pupils to pose).

* **Return type:**
  dict[str, dict[str, ‘SlotPose’]]

```pycon
>>> poses = view_poses()
>>> sorted(poses)
['back', 'front', 'side', 'three_quarter']
>>> poses["front"], poses["back"]["mouth"].alpha, poses["side"]["arm_r"].x
({}, 0.0, -90.0)
```
