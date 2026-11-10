# cutan.characters.carved_arms

Split a carved character’s one-stroke raster arms at the elbow (cutan#208).

The factory’s [`cutan.characters.factory.add_forearms()`](cutan.characters.factory.html.md#cutan.characters.factory.add_forearms) splits an arm it drew
itself (an SVG sleeve and a round hand). A character carved from a video frame has
arms that are pixels: the OverSimplified persona’s arms are one black stroke each,
a `(` and a `)` beside the body, with no drawn hand. Such an arm can still bend
at the elbow, the way OverSimplified draws a figure carrying a cup (the upper arm
down the side, the forearm across the front):

- each arm’s drawing is cut across the stroke at `elbow_at` of its painted
  length: the upper part keeps the `arm_*` slot and bone, the lower part becomes
  a `forearm_*` slot on a `forearm_*` bone hinged at the stroke’s centre line
  on the cut, so at rest the arm looks exactly as it did;
- both halves get a round cap of the stroke’s own ink on the cut (the stroke’s
  width, its median colour), so the elbow reads as a joint at any bend instead of
  showing the flat ends of the cut;
- the hand is a slotless `hand_*` bone at the end of the stroke (half a stroke
  width back from its last painted row, on the centre line), so `stu@hand_r`
  holds things exactly at the end of the drawn arm;
- the rig turns to `nesting: bones`, so a forearm follows its upper arm.

**Nesting changes what a swap pose hides.** Under `nesting: bones` a slot on a
child bone draws inside its parent’s part: the carved persona’s `face` slot (on
a `face` bone under `head`) would draw inside the head, so a face pose that
hides the head (`head: {alpha: 0}`: the drawn face replaces the round head) would
hide the face as well. [`split_carved_arms()`](#cutan.characters.carved_arms.split_carved_arms) hoists such a bone to the hidden
part’s parent (the `face` bone under the torso, at the same rest place), as the
flat rig drew it, and reports it. A hoisted face does not turn with a tween of the
head: tween it as well (`stu/torso/face`).

Opt-in, one character at a time; idempotent at the same `elbow_at`. The new
part files are derived from the character’s own art and keep its provenance (the
descriptor’s `source`); `metadata.arms` records `"split-carved"`.

### Module Attributes

| [`CARVED_ELBOW_AT`](#cutan.characters.carved_arms.CARVED_ELBOW_AT)   | Where the elbow sits on the painted length of the stroke, shoulder to hand.                                                   |
|--------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------|
| [`RASTER_SUFFIXES`](#cutan.characters.carved_arms.RASTER_SUFFIXES)   | Part files this module can cut (what [`cutan.carve`](cutan.carve.html.md#module-cutan.carve) writes). |

### Functions

| [`has_raster_arms`](#cutan.characters.carved_arms.has_raster_arms)(desc)                       | Whether both of `desc`'s arms are drawn as raster images (a carved rig).                   |
|----------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------|
| [`split_carved_arms`](#cutan.characters.carved_arms.split_carved_arms)(char_dir, \*[, elbow_at]) | Split a carved character's raster one-stroke arms at the elbow (see the module docstring). |

### Classes

| [`ArmSplit`](#cutan.characters.carved_arms.ArmSplit)(side, elbow, hand, stroke_width)   | Where one arm was cut, in its drawing's pixels: the elbow (on the stroke's centre line at the cut), the hand (the end of the stroke) and the stroke's width at the elbow.                             |
|----------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`CarvedArmsReport`](#cutan.characters.carved_arms.CarvedArmsReport)(descriptor[, arms, ...])   | What [`split_carved_arms()`](#cutan.characters.carved_arms.split_carved_arms) did: the descriptor written, each arm's cut, and the bones it hoisted out of a part a swap pose hides (`(bone, from, to)`). |

### *class* cutan.characters.carved_arms.ArmSplit(side, elbow, hand, stroke_width)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Where one arm was cut, in its drawing’s pixels: the elbow (on the stroke’s
centre line at the cut), the hand (the end of the stroke) and the stroke’s
width at the elbow.

### cutan.characters.carved_arms.CARVED_ELBOW_AT *: [float](https://docs.python.org/3/builtins/functions.html#float)* *= 0.5*

Where the elbow sits on the painted length of the stroke, shoulder to hand.

### *class* cutan.characters.carved_arms.CarvedArmsReport(descriptor, arms=(), hoisted=(), already_split=False)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

What [`split_carved_arms()`](#cutan.characters.carved_arms.split_carved_arms) did: the descriptor written, each arm’s cut,
and the bones it hoisted out of a part a swap pose hides (`(bone, from, to)`).

### cutan.characters.carved_arms.RASTER_SUFFIXES *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), ...]* *= ('.png', '.webp')*

Part files this module can cut (what [`cutan.carve`](cutan.carve.html.md#module-cutan.carve) writes).

### cutan.characters.carved_arms.has_raster_arms(desc)

Whether both of `desc`’s arms are drawn as raster images (a carved rig).

```pycon
>>> from types import SimpleNamespace as NS
>>> att = lambda p: {"a": NS(path=p)}
>>> rig = NS(slots=[NS(name="arm_l", attachment="a"), NS(name="arm_r", attachment="a")],
...          skins={"default": NS(slots={"arm_l": att("parts/arm_l.png"), "arm_r": att("parts/arm_r.png")})})
>>> has_raster_arms(rig)
True
>>> rig.skins["default"].slots["arm_r"] = att("parts/arm_r.svg")
>>> has_raster_arms(rig)
False
```

* **Return type:**
  [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

### cutan.characters.carved_arms.split_carved_arms(char_dir, , elbow_at=0.5)

Split a carved character’s raster one-stroke arms at the elbow (see the module docstring).

Writes `parts/arm_<side>_upper.png` and `parts/forearm_<side>.png` next to the
character’s parts, the bones `forearm_<side>` (hinged at the cut) and
`hand_<side>` (slotless, at the stroke’s end), the `forearm_<side>` slots
(drawn just above their upper arm), and `nesting: bones`. Refuses a rig whose
arms are not raster drawings, one already nested, one whose bones carry a rest
rotation or scale, an arm drawing with a declared size, not anchored at the top
of its stroke or crossing it twice on a row, and an `elbow_at` outside 0.1..0.9.
Every cut is measured before anything is written. Idempotent at the same
`elbow_at`. Every part path moves under the torso (`stu/arm_r` becomes
`stu/torso/arm_r`, `stu/head` `stu/torso/head`), and a descriptor animation
on the torso now carries the arms and the head with it.

* **Return type:**
  [`CarvedArmsReport`](#cutan.characters.carved_arms.CarvedArmsReport)
