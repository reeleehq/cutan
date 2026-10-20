# cutan.body_attachment

Props that depict part of a character’s body: the declaration, the geometry, the placement.

A steering wheel with the driver’s hands on it, a sleeve holding a cup, a pair of
forearms on a table: art that shows *somebody’s* limbs, drawn as one prop and laid
over a rigged character. Three mistakes reached a viewer in one production, and
no check that existed could see any of them:

1. **The art was drawn from the wrong viewpoint.** The image model drew the wheel
   from the driver’s seat (forearms coming from the camera), while the shot looked
   at the driver from in front, through the windscreen.
2. **The art did not meet the body.** Placed by hand, the wheel sat to the right of
   the driver’s head and was wider than his body, so the arms in it could not come
   from his shoulders.
3. **The relation drifted between framings.** The two-shot and the close-up each
   placed the wheel by hand, so the driver’s size relative to his own hands changed
   at the cut.

All three are now one contract, declared ONCE in the character’s own units (its
bones) and derived for every framing. The declaration lives in the prop’s
document, under `metadata.body_attachment` (the persisted key
[`BODY_ATTACHMENT_KEY`](#cutan.body_attachment.BODY_ATTACHMENT_KEY)), because what a drawing depicts is a property of the
drawing:

```json
{"kind": "PropDescriptor", "name": "wheel_hands", "...": "...",
 "metadata": {"body_attachment": {
     "schema_version": "0.1.0",
     "character": "paul",
     "view": "front",
     "sockets": [
         {"bone": "arm_l", "at": [0.20, 0.45]},
         {"bone": "arm_r", "at": [0.80, 0.45]}
     ]}}}
```

- `character` (optional): the character whose body the art shows, by scene
  entity id, else store ref. A scene entity binds a reusable prop to another
  character with `overrides: {body_of: jerry}` ([`BODY_OF_OVERRIDE`](#cutan.body_attachment.BODY_OF_OVERRIDE)).
- `view`: the character’s view the art is drawn in, in the rig’s own words
  (`front`, `three_quarter`, `side`, `back`, or any key of the
  character’s `view` swap set), or [`FIRST_PERSON`](#cutan.body_attachment.FIRST_PERSON) when the camera IS the
  character (valid only while the character is not on screen).
- `sockets`: where each depicted limb meets the body, in the character’s REST
  view. `bone` names the character’s bone (`arm_l` is the bone at the viewer’s
  left on the factory rig, unmirrored); `at` is where that bone’s joint would be,
  in the art’s `(u, v)` (0..1 of the drawn image, like an attachment
  `anchor`). It may lie outside the image: forearms that vanish behind a wheel
  still say where their shoulders are.
- `scale` (optional): the prop’s `stage.scale` relative to the character’s.
  Two sockets measure it; one socket needs it.
- `tolerance` (default `DFLT_TOLERANCE`): how far a socket may land from
  its bone, as a fraction of the span between the sockets’ bones on screen.
  `scale_tolerance` (default `DFLT_SCALE_TOLERANCE`): how far the prop’s
  size relative to the character may differ from the declared relation.

Unknown keys are kept (forward-compatible): a later field is not “malformed” to
an older `cutan`.

**Placement is derived, not authored.** A body-attached prop with no
`stage.at` is placed by its body in every shot (the `body_placement` compile
pass, [`cutan.compile.body`](cutan.compile.body.html.md#module-cutan.compile.body)), so the relation cannot drift between a two-shot
and a close-up. [`place_body_prop()`](#cutan.body_attachment.place_body_prop) is the same derivation as a function.
[`cutan.verify.body`](cutan.verify.body.html.md#module-cutan.verify.body) checks a prop that IS placed by hand against it.

```pycon
>>> ba = BodyAttachment(character="paul", view="front", sockets=[
...     {"bone": "arm_l", "at": [0.2, 0.45]}, {"bone": "arm_r", "at": [0.8, 0.45]}])
>>> [s.bone for s in ba.sockets], ba.tolerance, ba.scale_tolerance
(['arm_l', 'arm_r'], 0.25, 0.05)
```

### Module Attributes

| [`BODY_ATTACHMENT_KEY`](#cutan.body_attachment.BODY_ATTACHMENT_KEY)   | The persisted key under a prop document's `metadata`.                                |
|------------------------------------------------------------------------|--------------------------------------------------------------------------------------|
| [`BODY_OF_OVERRIDE`](#cutan.body_attachment.BODY_OF_OVERRIDE)      | The scene entity's `overrides` key that binds a prop to a character.                 |
| [`FIRST_PERSON`](#cutan.body_attachment.FIRST_PERSON)          | The view of art seen through the character's own eyes (the camera is the character). |

### Functions

| [`body_attachment_of`](#cutan.body_attachment.body_attachment_of)(prop_doc)                       | The prop's [`BodyAttachment`](#cutan.body_attachment.BodyAttachment), or `None` when it declares none.                                                                                                                                                                                                                                     |
|-----------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`bound_character`](#cutan.body_attachment.bound_character)(shot, prop_entity, ba)             | `(the character entity, its name)` the prop is bound to in `shot`: the entity's `overrides.body_of` first, else the declaration's `character`; by entity id, else by store ref when exactly one entity has it.                                                                                                                                   |
| [`start_state`](#cutan.body_attachment.start_state)(shot)                                  | `{entity id: {property: value}}` from the `set` actions at the shot's start, on the entities' own nodes (a part's are ignored).                                                                                                                                                                                                                  |
| [`entity_pose`](#cutan.body_attachment.entity_pose)(entity[, poses, sets])                 | The entity node's pose at the shot's start: the built pose when `poses` has it, else its `stage` placement, then any `set` at the start.                                                                                                                                                                                                         |
| [`character_view`](#cutan.body_attachment.character_view)(char_entity, char_desc, sets)       | The character's view at the shot's start: a `view` set at 0, else its `rest_view`, else `front`.                                                                                                                                                                                                                                                 |
| [`rig_point_on_stage`](#cutan.body_attachment.rig_point_on_stage)(desc, point, pose)              | Where `point` (view_box units of the rig `desc`) lands on the stage when the entity's node has `pose` (`x`, `y`, `scale_x`, `scale_y`, `rotation` in radians, as `an.motion.stage_poses()` reports it).                                                                                                                                          |
| [`socket_rig_point`](#cutan.body_attachment.socket_rig_point)(prop_desc, socket, \*, art_size)  | The socket's `at` as a point of the prop's rig (view_box units).                                                                                                                                                                                                                                                                                 |
| [`fit_placement`](#cutan.body_attachment.fit_placement)(sockets, targets, \*[, scale])       | The `(offset, scale)` that best maps `sockets` onto `targets`: `targets ≈ offset + scale * sockets` (least squares, uniform scale, no rotation, since a stage placement has none).                                                                                                                                                               |
| [`solve_placement`](#cutan.body_attachment.solve_placement)(prop, char, ba, \*, art_size, ...) | The placement the declaration gives for a character at `character_pose` (unmirrored, unrotated: [`NotChecked`](#cutan.body_attachment.NotChecked) otherwise): `{"at", "scale", "residual_px", "span_px", "targets", "local"}` where `targets` are the bones on stage and `local` the sockets in the prop's own stage units at scale 1. |
| [`place_body_prop`](#cutan.body_attachment.place_body_prop)(prop_desc, character_desc, ...)    | Where to put a body-depicting prop so its sockets meet the character's bones.                                                                                                                                                                                                                                                                    |
| [`derivable_placement`](#cutan.body_attachment.derivable_placement)(shot, prop_entity, mall)       | The derived placement of `prop_entity` in `shot`, or `None` ([`derive_placement()`](#cutan.body_attachment.derive_placement) says why).                                                                                                                                                                                                      |
| [`derive_placement`](#cutan.body_attachment.derive_placement)(shot, prop_entity, mall)          | `(the derived placement, "")` of `prop_entity` in `shot`, or `(None, why not)`.                                                                                                                                                                                                                                                                  |
| [`character_model`](#cutan.body_attachment.character_model)(doc)                               | A `CharacterDescriptor` from a stored mapping (migrated), or the model as given.                                                                                                                                                                                                                                                                 |
| [`prop_model`](#cutan.body_attachment.prop_model)(doc)                                    | A `PropDescriptor` from a stored mapping (migrated), or the model as given.                                                                                                                                                                                                                                                                      |

### Classes

| [`BodyAttachment`](#cutan.body_attachment.BodyAttachment)(\*[, schema_version, ...])   | A prop's declaration that it depicts part of a character's body.   |
|----------------------------------------------------------------------------------------------|--------------------------------------------------------------------|
| [`Socket`](#cutan.body_attachment.Socket)(\*, bone, at[, slot])                | Where one depicted limb meets the character's body.                |

### Exceptions

| [`NotChecked`](#cutan.body_attachment.NotChecked)   | The geometry cannot be computed for a reason that is a limit of this check, not a fault of the art (a nested slot, a posed bone, unmeasurable art, a mirrored or rotated character): reported as `info`.   |
|---------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`CrossedLimbs`](#cutan.body_attachment.CrossedLimbs) | The art's left limb would meet the body's right: drawn from the other side.                                                                                                                                |

### cutan.body_attachment.BODY_ATTACHMENT_KEY *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'body_attachment'*

The persisted key under a prop document’s `metadata`. Never renamed.

### cutan.body_attachment.BODY_OF_OVERRIDE *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'body_of'*

The scene entity’s `overrides` key that binds a prop to a character.

### *class* cutan.body_attachment.BodyAttachment(\*, schema_version='0.1.0', character=None, view, sockets=<factory>, scale=None, tolerance=0.25, scale_tolerance=0.05, \*\*extra_data)

Bases: `BaseModel`

A prop’s declaration that it depicts part of a character’s body.

```pycon
>>> BodyAttachment(view="")
Traceback (most recent call last):
...
pydantic_core._pydantic_core.ValidationError: 1 validation error for BodyAttachment
...
>>> BodyAttachment(view="front", grip="later field").model_dump()["grip"]
'later field'
```

#### model_config *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [`ConfigDict`][pydantic.config.ConfigDict].

### *exception* cutan.body_attachment.CrossedLimbs

Bases: [`ValueError`](https://docs.python.org/3/builtins/exceptions.html#ValueError)

The art’s left limb would meet the body’s right: drawn from the other side.

### cutan.body_attachment.FIRST_PERSON *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'first_person'*

The view of art seen through the character’s own eyes (the camera is the character).

### *exception* cutan.body_attachment.NotChecked

Bases: [`ValueError`](https://docs.python.org/3/builtins/exceptions.html#ValueError)

The geometry cannot be computed for a reason that is a limit of this
check, not a fault of the art (a nested slot, a posed bone, unmeasurable art,
a mirrored or rotated character): reported as `info`.

### *class* cutan.body_attachment.Socket(, bone, at, slot=None, \*\*extra_data)

Bases: `BaseModel`

Where one depicted limb meets the character’s body.

```pycon
>>> Socket(bone="arm_l", at=(0.2, -0.4)).at
(0.2, -0.4)
```

#### at *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[float](https://docs.python.org/3/builtins/functions.html#float), [float](https://docs.python.org/3/builtins/functions.html#float)]*

That joint, in the art’s `(u, v)` (0..1 of the drawn image; outside is allowed).

#### bone *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)*

The character’s bone the limb belongs to; its joint is the meeting point.

#### model_config *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [`ConfigDict`][pydantic.config.ConfigDict].

#### slot *: [Optional](https://docs.python.org/3/library/typing.html#typing.Optional)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)]*

the prop’s first slot.

* **Type:**
  The prop’s slot whose art `at` is measured on. `None`

### cutan.body_attachment.body_attachment_of(prop_doc)

The prop’s [`BodyAttachment`](#cutan.body_attachment.BodyAttachment), or `None` when it declares none.

`prop_doc` is a `PropDescriptor` or the stored mapping. A malformed
declaration raises (pydantic’s `ValidationError`): the check reports it.

```pycon
>>> body_attachment_of({"metadata": {}}) is None
True
>>> body_attachment_of({"metadata": ["not a mapping"]}) is None
True
>>> body_attachment_of({"metadata": {"body_attachment": {"view": "front"}}}).view
'front'
```

* **Return type:**
  [`BodyAttachment`](#cutan.body_attachment.BodyAttachment) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### cutan.body_attachment.bound_character(shot, prop_entity, ba)

`(the character entity, its name)` the prop is bound to in `shot`:
the entity’s `overrides.body_of` first, else the declaration’s
`character`; by entity id, else by store ref when exactly one entity has
it. The entity is `None` when absent or ambiguous; the name is `""` when
nothing binds the prop.

* **Return type:**
  [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

### cutan.body_attachment.character_model(doc)

A `CharacterDescriptor` from a stored mapping (migrated), or the model as given.

* **Return type:**
  [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

### cutan.body_attachment.character_view(char_entity, char_desc, sets)

The character’s view at the shot’s start: a `view` set at 0, else its
`rest_view`, else `front`.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### cutan.body_attachment.derivable_placement(shot, prop_entity, mall)

The derived placement of `prop_entity` in `shot`, or `None`
([`derive_placement()`](#cutan.body_attachment.derive_placement) says why). Never raises.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### cutan.body_attachment.derive_placement(shot, prop_entity, mall)

`(the derived placement, "")` of `prop_entity` in `shot`, or
`(None, why not)`. Never raises.

* **Return type:**
  [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict) | [`None`](https://docs.python.org/3/builtins/constants.html#None), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

### cutan.body_attachment.entity_pose(entity, poses=None, sets=None)

The entity node’s pose at the shot’s start: the built pose when `poses`
has it, else its `stage` placement, then any `set` at the start.
`None` when neither places it (the default layout, without built poses).

```pycon
>>> from an.ir.schema import AssetRef, StagePlacement
>>> e = AssetRef(kind="prop", id="w", store="props", ref="w", stage=StagePlacement(at=(1, 2), scale=3))
>>> entity_pose(e, None, {"x": 5})
{'x': 5.0, 'y': 2.0, 'scale_x': 3.0, 'scale_y': 3.0, 'rotation': 0.0}
```

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`float`](https://docs.python.org/3/builtins/functions.html#float)] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### cutan.body_attachment.fit_placement(sockets, targets, , scale=1.0)

The `(offset, scale)` that best maps `sockets` onto `targets`:
`targets ≈ offset + scale * sockets` (least squares, uniform scale, no
rotation, since a stage placement has none). With one socket (or sockets that
coincide) the scale cannot be measured and `scale` is kept.

A non-positive scale means the limbs are crossed.

```pycon
>>> fit_placement([(0, 0), (10, 0)], [(100, 50), (120, 50)])
((100.0, 50.0), 2.0)
>>> fit_placement([(5, 5)], [(100, 50)], scale=3.0)
((85.0, 35.0), 3.0)
>>> fit_placement([(0, 0), (10, 0)], [(120, 50), (100, 50)])[1]
-2.0
```

* **Return type:**
  [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`float`](https://docs.python.org/3/builtins/functions.html#float), [`float`](https://docs.python.org/3/builtins/functions.html#float)], [`float`](https://docs.python.org/3/builtins/functions.html#float)]

### cutan.body_attachment.place_body_prop(prop_desc, character_desc, , character_at, character_scale=1.0, art_size)

Where to put a body-depicting prop so its sockets meet the character’s bones.

Returns `{"at": [x, y], "scale": s, "residual_px": r}`: the prop’s
`stage.at` and `stage.scale` for a character standing at
`character_at` with `stage.scale` `character_scale` in its rest view,
and the largest distance left between a socket and its bone. The compile
pass does this for every prop placed without `stage.at`; call it for a
hand-placed one.

```pycon
>>> from an.stage.props import PropDescriptor
>>> from cutan.characters.schema import CharacterDescriptor
>>> paul = CharacterDescriptor(name="paul")
>>> wheel = PropDescriptor.model_validate({"name": "w", "slots": [
...     {"name": "body", "bone": "root", "attachment": "w"}],
...     "skins": {"default": {"slots": {"body": {"w": {"path": "parts/w.png"}}}}},
...     "metadata": {"body_attachment": {"character": "paul", "view": "front",
...         "sockets": [{"bone": "arm_l", "at": [0.1, 0.0]},
...                     {"bone": "arm_r", "at": [0.9, 0.0]}]}}})
>>> place_body_prop(wheel, paul, character_at=(200, 400), character_scale=2.0,
...                 art_size=(500, 300))
{'at': [200.0, 270.288], 'scale': 0.9, 'residual_px': 0.0}
```

The relation is the character’s: at another framing the prop’s scale moves
with the character’s, in proportion.

```pycon
>>> place_body_prop(wheel, paul, character_at=(0, 0), character_scale=3.0,
...                 art_size=(500, 300))["scale"]
1.35
```

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### cutan.body_attachment.prop_model(doc)

A `PropDescriptor` from a stored mapping (migrated), or the model as given.

* **Return type:**
  [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

### cutan.body_attachment.rig_point_on_stage(desc, point, pose)

Where `point` (view_box units of the rig `desc`) lands on the stage when
the entity’s node has `pose` (`x`, `y`, `scale_x`, `scale_y`,
`rotation` in radians, as `an.motion.stage_poses()` reports it).

```pycon
>>> from types import SimpleNamespace as NS
>>> rig = NS(view_box=(0, 0, 345, 345), origin=(100, 100), bones=[])
>>> rig_point_on_stage(rig, (110, 100), {"x": 5, "y": 0, "scale_x": 2, "scale_y": 2})
(25.0, 0.0)
```

* **Return type:**
  [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`float`](https://docs.python.org/3/builtins/functions.html#float), [`float`](https://docs.python.org/3/builtins/functions.html#float)]

### cutan.body_attachment.socket_rig_point(prop_desc, socket, , art_size)

The socket’s `at` as a point of the prop’s rig (view_box units).

`art_size` is what the slot’s drawn art rasterises at (pixels for a
raster, the SVG’s size), as the compiler’s probe measures it, or a function
of the attachment’s `path` returning it (`None`: unmeasurable); a
declared `width`/`height` on the attachment wins, keeping the art’s
aspect. Raises [`NotChecked`](#cutan.body_attachment.NotChecked) for what this v1 does not compute: a
missing slot or art, unmeasurable art, a nested slot, a posed bone.

```pycon
>>> from an.stage.props import PropDescriptor
>>> p = PropDescriptor.model_validate({"name": "w", "skins": {"default": {"slots": {
...     "body": {"w": {"path": "parts/w.png"}}}}}, "slots": [
...     {"name": "body", "bone": "root", "attachment": "w"}]})
>>> socket_rig_point(p, Socket(bone="arm_l", at=(0.0, 0.5)), art_size=(400, 200))
(312.0, 512.0)
```

* **Return type:**
  [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`float`](https://docs.python.org/3/builtins/functions.html#float), [`float`](https://docs.python.org/3/builtins/functions.html#float)]

### cutan.body_attachment.solve_placement(prop, char, ba, , art_size, character_pose)

The placement the declaration gives for a character at `character_pose`
(unmirrored, unrotated: [`NotChecked`](#cutan.body_attachment.NotChecked) otherwise):
`{"at", "scale", "residual_px", "span_px", "targets", "local"}` where
`targets` are the bones on stage and `local` the sockets in the prop’s
own stage units at scale 1. Raises [`CrossedLimbs`](#cutan.body_attachment.CrossedLimbs), [`NotChecked`](#cutan.body_attachment.NotChecked),
or `ValueError` for a bone the character lacks.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### cutan.body_attachment.start_state(shot)

`{entity id: {property: value}}` from the `set` actions at the shot’s
start, on the entities’ own nodes (a part’s are ignored).

```pycon
>>> from an.ir.schema import SetAction, Shot
>>> start_state(Shot(id="s", actions=[SetAction(target="p", property="view", value="side")]))
{'p': {'view': 'side'}}
```

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]]
