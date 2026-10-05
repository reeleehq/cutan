# cutan.compile.passes

The cut-out passes over the stage compiler, and the helpers only they use.

Moved from `an.stage.compile` (an#225). The stage compiler keeps the passes every
genre shares (scene, actions, camera, parallax, checks) and the helpers both sides use;
this module holds what only the cut-out genre reaches: the `speech`, `swap_pose`,
`view_spans`, `visemes` and `face` passes (registered by `cutan.genre.CUTOUT`
as `"cutan.compile.passes:<name>"`) and the character rig builder.

### Module Attributes

| [`PLACEHOLDER_PARTS`](#cutan.compile.passes.PLACEHOLDER_PARTS)      | The parts the built-in placeholder rig draws when a character ref has no descriptor and no `parts`: arms, no legs (so a walk on it glides).                                                                                                                                                                  |
|-------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`DFLT_LEG_COLOUR`](#cutan.compile.passes.DFLT_LEG_COLOUR)        | The procedural rig's leg colour — a literal the palette table never carried, which is why it is a named constant rather than two copies of a string.                                                                                                                                                         |
| [`DFLT_PUPIL_COLOUR`](#cutan.compile.passes.DFLT_PUPIL_COLOUR)      | The procedural rig's pupil colour.                                                                                                                                                                                                                                                                           |
| [`COARTICULATION_ENABLED`](#cutan.compile.passes.COARTICULATION_ENABLED) | Co-articulation on/off (an#97).                                                                                                                                                                                                                                                                              |
| [`PROCEDURAL_MOUTH_KEYS`](#cutan.compile.passes.PROCEDURAL_MOUTH_KEYS)  | The procedural (drawn) mouth's swap vocabulary, DECLARED as data on its visual exactly as the runtime declares it (`g._anDrawSets = {viseme: ...}`) and as an SVG mouth carries its projection.                                                                                                              |
| [`EYE_NODE_NAMES`](#cutan.compile.passes.EYE_NODE_NAMES)         | the default rig's eye slots ARE its node names, on both the procedural and the descriptor path.                                                                                                                                                                                                              |
| [`PUPIL_NODE_NAMES`](#cutan.compile.passes.PUPIL_NODE_NAMES)       | The pupil nodes of the gaze stack (an#99); a rig without them takes gaze as a no-op.                                                                                                                                                                                                                         |
| [`GAZE_ELLIPSE_MARGIN`](#cutan.compile.passes.GAZE_ELLIPSE_MARGIN)    | The summed gaze (x, y), in axis units, is clamped to a circle of this radius — the declared travel maps the unit circle onto the sclera's inner ellipse, and 0.95 keeps the whole pupil disc inside it at every angle (measured on the synthesized eye: 1.0 pokes out by 2% of the ellipse at the diagonal). |

### Functions

| [`blink_phase`](#cutan.compile.passes.blink_phase)(entity_id)   | The entity's blink phase in [0, 1): the runtime's rule, ported exactly.                                                                                                                                                                                                                           |
|---------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`preset_context_of`](#cutan.compile.passes.preset_context_of)(vocab) | `(entity_id, play) -> PresetContext` for the extent resolver (`cutan.characters.play.play_extent_for()`): exactly the `gait` and `scale` `_with_view_and_posed_parts()` will fill in before the expansion, read off the same vocabulary, so a `sequence` waits for what the walk runs (cutan#12). |

### cutan.compile.passes.COARTICULATION_ENABLED *: [bool](https://docs.python.org/3/builtins/functions.html#bool)* *= True*

Co-articulation on/off (an#97). ON is the product; OFF reproduces the
pre-#97 mouth CHOICE — the raw provider track thinned by the old drop-not-hold
condenser — over the new frame-ceiled clip window (so not byte-for-byte the
old emission: OFF still closes the mouth after a line) and exists so the `lipsync-coarticulation` demo and a test can
render the two side by side. Not a RenderContext knob: nobody should ship
the old behaviour, and a module flag rebound for one render is the shape
the bench’s levers already use.

### cutan.compile.passes.DFLT_LEG_COLOUR *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= '#2c3e50'*

The procedural rig’s leg colour — a literal the palette table never
carried, which is why it is a named constant rather than two copies of a
string. A `StylePack`’s `leg` role replaces it.

### cutan.compile.passes.DFLT_PUPIL_COLOUR *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= '#1a1a1a'*

The procedural rig’s pupil colour. `makeEye` reads it from the document —
the eye WHITE beside it is a literal and cannot be reached, which is the
split `REACHABLE_ROLES` / `UNREACHABLE_ROLES` records.

### cutan.compile.passes.EYE_NODE_NAMES *: [frozenset](https://docs.python.org/3/builtins/stdtypes.html#frozenset)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)]* *= frozenset({'left_eye', 'right_eye'})*

the default rig’s eye slots ARE its node
names, on both the procedural and the descriptor path.

* **Type:**
  The nodes that blink, by name

### cutan.compile.passes.GAZE_ELLIPSE_MARGIN *: [float](https://docs.python.org/3/builtins/functions.html#float)* *= 0.95*

The summed gaze (x, y), in axis units, is clamped to a circle of this radius
— the declared travel maps the unit circle onto the sclera’s inner ellipse,
and 0.95 keeps the whole pupil disc inside it at every angle (measured on
the synthesized eye: 1.0 pokes out by 2% of the ellipse at the diagonal).

### cutan.compile.passes.PLACEHOLDER_PARTS *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), ...]* *= ('head', 'torso', 'left_arm', 'right_arm')*

The parts the built-in placeholder rig draws when a character ref has no
descriptor and no `parts`: arms, no legs (so a walk on it glides).

### cutan.compile.passes.PROCEDURAL_MOUTH_KEYS *: [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [str](https://docs.python.org/3/builtins/stdtypes.html#str)]* *= {'A': 'A', 'B': 'B', 'C': 'C', 'D': 'D', 'E': 'E', 'F': 'F', 'G': 'G', 'H': 'H', 'X': 'X'}*

The procedural (drawn) mouth’s swap vocabulary, DECLARED as data on its
visual exactly as the runtime declares it (`g._anDrawSets = {viseme: ...}`)
and as an SVG mouth carries its projection. A drawn mouth has no textures,
so each key maps to itself — the code the runtime’s shape table draws. The
compiler never branches on the set’s NAME: the drawn mouth is just a node
whose visual carries a `viseme` set (an#87).

### cutan.compile.passes.PUPIL_NODE_NAMES *: [frozenset](https://docs.python.org/3/builtins/stdtypes.html#frozenset)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)]* *= frozenset({'left_pupil', 'right_pupil'})*

The pupil nodes of the gaze stack (an#99); a rig without them takes gaze as a no-op.

### cutan.compile.passes.blink_phase(entity_id)

The entity’s blink phase in [0, 1): the runtime’s rule, ported exactly.

* **Return type:**
  [`float`](https://docs.python.org/3/builtins/functions.html#float)

```pycon
>>> blink_phase("charlie")
0.762
```

### cutan.compile.passes.preset_context_of(vocab)

`(entity_id, play) -> PresetContext` for the extent resolver
(`cutan.characters.play.play_extent_for()`): exactly the `gait` and
`scale` `_with_view_and_posed_parts()` will fill in before the
expansion, read off the same vocabulary, so a `sequence` waits for what
the walk runs (cutan#12).
