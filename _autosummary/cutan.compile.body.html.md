# cutan.compile.body

Derive a body-attached prop’s placement from its character, in every shot.

A prop that declares `metadata.body_attachment` ([`cutan.body_attachment`](cutan.body_attachment.html.md#module-cutan.body_attachment))
and is placed WITHOUT `stage.at` is placed by its body: before the scene is
built (the `body_placement` compile pass, order 90), its `stage.at` and
`stage.scale` are derived from where its character stands in this shot, by
[`cutan.body_attachment.place_body_prop()`](cutan.body_attachment.html.md#cutan.body_attachment.place_body_prop). The attachment is then declared
once, in the character’s own units (its bones), and every framing (a two-shot,
a close-up) derives the same relation: the prop’s size relative to the
character and its anchor on the body cannot drift between shots.

A prop placed WITH `stage.at` keeps the author’s placement, and
`cutout.body_attachment` checks it against the same derivation.

**The prop follows the body through the shot** (cutan#104, the constraint
layer): a prop placed by its body whose character moves in the shot (an
authored tween or play on it or its parts, or a joint, a verb or a hold that
makes the shot solve) gets one `pin` per socket, from the socket’s point on
its art to the character’s bone, held for the whole shot. The `solve` pass
then keeps the sockets on the bones as the torso nods or the shoulders move,
and `an validate` (`cutout.body_attachment`, which reads the compiled
shot’s solve report: the pins are added at compile, after the core’s joint
checks look) reports a pin the motion pulls off its bone, with the time, and a
prop whose sockets do not fit the bones, which is placed once. A prop with authored motion of its own is
left to that motion. A shot where the character holds still gets none, and
compiles as it always did.

Nothing changes for a stored scene: no prop declared a body attachment before
this existed, and a prop that declares none is never touched.

```pycon
>>> from an.ir.schema import Shot
>>> derive_body_placements(Shot(id="s"), {}).id
's'
```

### Module Attributes

| [`PIN_RESIDUAL_PX`](#cutan.compile.body.PIN_RESIDUAL_PX)   | How far (px) the derived placement may leave a socket from its bone and still be followed by a pin: a hard pin holds the point exactly, so a mismatch beyond this would drag the prop off its derived place (and, with several sockets, fight the others and be given up).   |
|--------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`MOTION_KINDS`](#cutan.compile.body.MOTION_KINDS)      | The action kinds that move the parts of the entity they name.                                                                                                                                                                                                                |
| [`MOTION_PROPERTIES`](#cutan.compile.body.MOTION_PROPERTIES) | The properties of a `tween` that move a part (not its look).                                                                                                                                                                                                                 |

### Functions

| [`body_attachment_pins`](#cutan.compile.body.body_attachment_pins)(shot, prop_entity, mall, \*)   | The `pin` actions that keep a body-attached prop's sockets on its character's bones.                                                   |
|------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------|
| [`why_not_followed`](#cutan.compile.body.why_not_followed)(shot, prop_entity, mall, \*)       | Why a body-attached prop that moves with its character is NOT given pins ('' when it is followed, or when there is nothing to follow). |
| [`derive_body_placements`](#cutan.compile.body.derive_body_placements)(shot, mall)                  | `shot` with every body-attached prop that has no `stage.at` placed by its body.                                                        |

### cutan.compile.body.MOTION_KINDS *: [frozenset](https://docs.python.org/3/builtins/stdtypes.html#frozenset)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)]* *= frozenset({'play', 'tween'})*

The action kinds that move the parts of the entity they name.

### cutan.compile.body.MOTION_PROPERTIES *: [frozenset](https://docs.python.org/3/builtins/stdtypes.html#frozenset)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)]* *= frozenset({'rotation', 'rotation_rad', 'scale_x', 'scale_y', 'x', 'y'})*

The properties of a `tween` that move a part (not its look).

### cutan.compile.body.PIN_RESIDUAL_PX *: [float](https://docs.python.org/3/builtins/functions.html#float)* *= 0.5*

How far (px) the derived placement may leave a socket from its bone and still
be followed by a pin: a hard pin holds the point exactly, so a mismatch beyond
this would drag the prop off its derived place (and, with several sockets,
fight the others and be given up). Such a prop is placed once, as before.

### cutan.compile.body.body_attachment_pins(shot, prop_entity, mall, , placed=None)

The `pin` actions that keep a body-attached prop’s sockets on its character’s bones.

One per socket, from the socket’s point on the prop’s art
(`<prop>/<slot>@u,v`) to the bone, on the part of the character that sits
on it (`<character>/<slot>@<bone>`), for the whole shot. Empty unless the
character moves (`_moves()`, or the shot already solves: a joint, a
verb or a hold), the prop has no motion of its own, and every socket’s bone
carries a part, and the derived placement leaves every socket within
[`PIN_RESIDUAL_PX`](#cutan.compile.body.PIN_RESIDUAL_PX) of its bone (`placed`: the derivation, else made
here). Never raises: a prop that cannot be followed is placed once, as it
always was ([`why_not_followed()`](#cutan.compile.body.why_not_followed) says why, for `an validate`).

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### cutan.compile.body.derive_body_placements(shot, mall)

`shot` with every body-attached prop that has no `stage.at` placed by
its body. Returns `shot` itself when nothing is derived. A prop whose
placement cannot be derived (no character in the shot, the character in the
default layout or mirrored, a socket naming a missing bone, unmeasurable
art, crossed limbs) is left as it is: `cutout.body_attachment` says why.

* **Return type:**
  [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

### cutan.compile.body.why_not_followed(shot, prop_entity, mall, , placed=None)

Why a body-attached prop that moves with its character is NOT given pins
(’’ when it is followed, or when there is nothing to follow). For `an
validate`: the prop would be placed once and left behind by the motion.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)
