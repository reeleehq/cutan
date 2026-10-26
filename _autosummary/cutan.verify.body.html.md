# cutan.verify.body

Body continuity: a prop that depicts a character’s limbs must meet that character’s body.

Two checks `an validate` runs, over every prop entity whose document declares a
`metadata.body_attachment` ([`cutan.body_attachment`](cutan.body_attachment.html.md#module-cutan.body_attachment)):

`cutout.body_attachment`, once per shot, at the shot’s start:

- **the character is there** when the art shows it from outside: a body part
  whose character is not on stage is a warning. `first_person` art (the camera
  IS the character) is the one view that needs the character OFF screen; with
  it on screen it is an error;
- **the view agrees**: the view the art declares is the character’s view (a
  `view` set at the start, else its `rest_view`, else `front`). Art drawn
  from the driver’s seat laid over a driver seen through the windscreen is this
  error;
- **the relation holds**, for a prop placed by hand (one placed without
  `stage.at` is derived by the `body_placement` pass and holds by
  construction): every socket lands within `tolerance` × the span between the
  sockets’ bones of that bone; the prop’s size relative to the character is the
  declared one within `scale_tolerance`; the limbs are not crossed; a mirrored
  character carries a mirrored prop. The error says where the derivation puts it.

`cutout.body_attachment_consistency`, once per scene: the same prop on the
same character has the same size relative to the character, and the same anchor
on the body in the character’s units, in every shot (the framings must not
drift apart at a cut).

Placements are the compiler’s: the entity nodes of the shot’s built stage
(`an.motion.stage_poses()`, built only when a shot holds a declaring prop),
with any `set` at the shot’s start applied.

\*\*Reported as `info` and not checked (v1):\*\* the geometry while the
character is in a view other than its rest view (sockets are declared on the
rest view’s bones; a side view moves and hides arms), a rotated prop or
character, a socket on a nested slot or a posed bone, art the store cannot
measure. **Motion during the shot** (cutan#98) is not measured here: when the
character moves, the `body_placement` pass lowers the sockets to `pin`
joints ([`cutan.compile.body.body_attachment_pins()`](cutan.compile.body.html.md#cutan.compile.body.body_attachment_pins)) and this check says,
with the time, when the motion pulls one off its bone (`_follow_findings()`). **Not checked at all:** whether the
declaration is TRUE of the pixels: the sockets are the art author’s statement
(a critic over probe frames is cutan#95).

```pycon
>>> from an.ir.schema import Shot
>>> body_attachment_findings(Shot(id="s"), {})
[]
```

### Module Attributes

| [`BODY_ATTACHMENT_CONSISTENCY`](#cutan.verify.body.BODY_ATTACHMENT_CONSISTENCY)   | The cross-shot check as a constraint on the shared interface (cutan#104, an#508): size conservation of a body-attached prop against its character.   |
|--------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------|

### Functions

| [`body_attachment_findings`](#cutan.verify.body.body_attachment_findings)(shot, stores, \*[, ...])   | `[(severity, ir path, message)]` for every body-depicting prop in `shot`.                                                                                                                                                 |
|------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`check_body_attachments`](#cutan.verify.body.check_body_attachments)(ctx)                         | The cut-out genre's per-shot body-continuity check ([`body_attachment_findings()`](#cutan.verify.body.body_attachment_findings)).                                                                                         |
| [`check_body_attachment_consistency`](#cutan.verify.body.check_body_attachment_consistency)(ctx)              | The cut-out genre's cross-shot body-continuity check ([`consistency_findings()`](#cutan.verify.body.consistency_findings)).                                                                                           |
| [`consistency_findings`](#cutan.verify.body.consistency_findings)(records)                       | The same prop on the same character across shots: one finding per pair whose size relative to the character, or anchor on the body (in the character's units), differs between shots beyond the declaration's tolerances. |

### cutan.verify.body.BODY_ATTACHMENT_CONSISTENCY *= Constraint(name='cutout.body_attachment_consistency', check=<function check_body_attachment_consistency>, stage='finish', order=11, description='a body-attached prop keeps its size and place relative to its character across shots', term=None)*

The cross-shot check as a constraint on the shared interface (cutan#104,
an#508): size conservation of a body-attached prop against its character.
Lint-only (no solver term): the placement is derived from the character in
every shot, so a drift can only come from a hand placement. The persisted
name is the check’s, unchanged.

### cutan.verify.body.body_attachment_findings(shot, stores, , poses=None, path='', records=None, index=None)

`[(severity, ir path, message)]` for every body-depicting prop in `shot`.

`stores` are the project’s stores by mall name (`props`, `characters`);
a prop or character whose store is absent is not checked. `poses` are the
shot’s built entity poses (`an.motion.stage_poses()`), or a function
returning them (called only when a prop declares an attachment); `None`
reads placements off the entities’ `stage`, after deriving the placements
the compiler derives. `records`, when given, receives one measurement per
checked prop for [`consistency_findings()`](#cutan.verify.body.consistency_findings). Never raises.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]]

### cutan.verify.body.check_body_attachment_consistency(ctx)

The cut-out genre’s cross-shot body-continuity check ([`consistency_findings()`](#cutan.verify.body.consistency_findings)).

It reads the measurements `cutout.body_attachment` leaves in the
validation’s memo, so the two must be selected together (`only=`).

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### cutan.verify.body.check_body_attachments(ctx)

The cut-out genre’s per-shot body-continuity check ([`body_attachment_findings()`](#cutan.verify.body.body_attachment_findings)).

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### cutan.verify.body.consistency_findings(records)

The same prop on the same character across shots: one finding per pair
whose size relative to the character, or anchor on the body (in the
character’s units), differs between shots beyond the declaration’s
tolerances.

```pycon
>>> r = lambda shot, ratio, ax: {"shot": shot, "where": f"timeline/{shot}/entities/1",
...     "prop": "wheel", "character": "paul", "ratio": ratio, "anchor": (ax, 0.0),
...     "span": 50.0, "tolerance": 0.25, "scale_tolerance": 0.05}
>>> consistency_findings([r(0, 0.43, 0.0), r(3, 0.43, 1.0)])
[]
>>> [f[0] for f in consistency_findings([r(0, 0.43, 0.0), r(3, 0.52, 0.0)])]
['error']
```

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]]
