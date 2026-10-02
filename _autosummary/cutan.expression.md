# cutan.expression

Facial expression for the cutout face (an#98, epic #9 Wave 6).

The vocabulary ([`axes`](cutan.expression.axes.md#module-cutan.expression.axes)), our presets
([`presets`](cutan.expression.presets.md#module-cutan.expression.presets)), how they reach a character’s slots and which
mouth set a line uses ([`binding`](cutan.expression.binding.md#module-cutan.expression.binding)), the provider seam that
turns authored leaves and dialogue sugar into per-frame curves
([`provider`](cutan.expression.provider.md#module-cutan.expression.provider)), and the 52-coefficient import/export
mapping ([`blendshapes`](cutan.expression.blendshapes.md#module-cutan.expression.blendshapes)). Renderer-free throughout: the
cutout compiler’s face solver consumes these; `an validate` and
`an character validate` share the same resolution.

### Functions

| [`binding_for`](#cutan.expression.binding_for)(desc)                              | The descriptor's declared `expression_binding` (additive field), else the default.                                               |
|-------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------|
| [`clamp_axes`](#cutan.expression.clamp_axes)(values)                             | Clamp every numeric axis to its range; an unknown axis is an error.                                                              |
| [`declared_mouth_variants`](#cutan.expression.declared_mouth_variants)(desc)                  | `{form: set name}` for every `viseme@<form>` set the descriptor declares.                                                        |
| [`default_binding`](#cutan.expression.default_binding)(desc)                          | The binding the default rig implies, from the slots it actually has.                                                             |
| [`expression_problems`](#cutan.expression.expression_problems)(desc, \*, preset[, axes])  | Every reason an expression cannot resolve on `desc` — empty means it can.                                                        |
| [`expression_spans`](#cutan.expression.expression_spans)(shot, entity_id)              | Every expression contributor on `entity_id`: authored leaves, then dialogue sugar.                                               |
| [`from_blendshapes`](#cutan.expression.from_blendshapes)(coefficients)                 | Fold unipolar coefficients onto the axes (summed, then clamped).                                                                 |
| [`known_presets`](#cutan.expression.known_presets)()                                | The preset names, in declaration order.                                                                                          |
| [`lid_key`](#cutan.expression.lid_key)(value, \*, available)                  | The eyelid key a lid state selects, degraded to the art the rig declares.                                                        |
| [`mouth_form_of`](#cutan.expression.mouth_form_of)(preset)                          | The `viseme@<form>` a preset prefers, or `None` for the neutral set.                                                             |
| [`preset_axes`](#cutan.expression.preset_axes)(preset, \*[, axes, intensity])     | The numeric axis offsets an expression asks for: the preset's, with `axes` layered over them, scaled by `intensity` and clamped. |
| [`resolve_mouth_set`](#cutan.expression.resolve_mouth_set)(desc, preset, \*, keys_used) | Which mouth set a line under `preset` uses — the one chain, shared.                                                              |
| [`variant_set_name`](#cutan.expression.variant_set_name)(form)                         | The swap-set name for a mouth form (`@` is a legal set-name character).                                                          |

### Classes

| [`Axis`](#cutan.expression.Axis)(name, lo, hi[, rest])                        | One numeric axis: its range and its rest (neutral) value.                          |
|----------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------|
| [`AxisCurve`](#cutan.expression.AxisCurve)(axis, samples)                          | One axis sampled at the frame times `0, 1/fps, …, n/fps` (offline, deterministic). |
| [`ChannelBinding`](#cutan.expression.ChannelBinding)(axis, slot, property, gain[, ...]) | A numeric axis driving one transform property of one slot's node.                  |
| [`DefaultExpressionProvider`](#cutan.expression.DefaultExpressionProvider)()                       | Sum of the shot's expression spans on the entity, ramped, per frame.               |
| [`ExpressionProvider`](#cutan.expression.ExpressionProvider)(\*args, \*\*kwargs)            | The seam: whatever produces per-axis curves for one entity of one shot.            |
| [`ExpressionSpan`](#cutan.expression.ExpressionSpan)(start, end, preset[, axes, ...])   | One expression contributor on one entity, in absolute shot time.                   |
| [`Preset`](#cutan.expression.Preset)(name[, axes, mouth_form, anchor])          | A named expression: axis offsets, the mouth form it prefers, its anchor.           |
| [`SetBinding`](#cutan.expression.SetBinding)(axis, slot[, set_family])              | A lid axis driving one slot's swap set through the ladder.                         |

### Exceptions

| [`ExpressionResolutionError`](#cutan.expression.ExpressionResolutionError)(who, problems)   | An expression that cannot resolve on a character; `problems` says why.   |
|---------------------------------------------------------------------------------------------|--------------------------------------------------------------------------|

### *class* cutan.expression.Axis(name, lo, hi, rest=0.0)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

One numeric axis: its range and its rest (neutral) value.

### *class* cutan.expression.AxisCurve(axis, samples)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

One axis sampled at the frame times `0, 1/fps, …, n/fps` (offline, deterministic).

### *class* cutan.expression.ChannelBinding(axis, slot, property, gain, rig_scaled=False)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A numeric axis driving one transform property of one slot’s node.

#### rig_scaled *: [bool](https://docs.python.org/3/builtins/functions.html#bool)* *= False*

Whether the gain is a view-box length (scaled by the rig factor).

### *class* cutan.expression.DefaultExpressionProvider

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Sum of the shot’s expression spans on the entity, ramped, per frame.

#### mouth_preset_at(shot, entity_id, t)

The preset whose mouth form is in force at `t`: the heaviest span
at `t` that prefers a form, or `None` (the neutral set).

Whole-line by construction when called at a line’s start — the solver
asks once per line, never per frame, so at most one mouth swap
property is live per instant.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### *class* cutan.expression.ExpressionProvider(\*args, \*\*kwargs)

Bases: [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol)

The seam: whatever produces per-axis curves for one entity of one shot.

### *exception* cutan.expression.ExpressionResolutionError(who, problems)

Bases: [`ValueError`](https://docs.python.org/3/builtins/exceptions.html#ValueError)

An expression that cannot resolve on a character; `problems` says why.

### *class* cutan.expression.ExpressionSpan(start, end, preset, axes=<factory>, intensity=1.0, blend=0.0, source='action')

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

One expression contributor on one entity, in absolute shot time.

#### offsets()

The unscaled axis offsets this span asks for.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`float`](https://docs.python.org/3/builtins/functions.html#float)]

#### source *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'action'*

`"action"` for an authored leaf, `"dialogue"` for the `[emotion]` sugar.

#### weight_at(t)

The ramped intensity at `t`: 0 outside, ramping over `blend` at each end.

* **Return type:**
  [`float`](https://docs.python.org/3/builtins/functions.html#float)

### *class* cutan.expression.Preset(name, axes=<factory>, mouth_form=None, anchor='')

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A named expression: axis offsets, the mouth form it prefers, its anchor.

#### anchor *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= ''*

FACS AU cross-reference (a comment, never a source).

#### mouth_form *: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None)* *= None*

The `viseme@<form>` set this preset’s mouth prefers; `None` = `viseme`.

### *class* cutan.expression.SetBinding(axis, slot, set_family='eyelid')

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A lid axis driving one slot’s swap set through the ladder.

### cutan.expression.binding_for(desc)

The descriptor’s declared `expression_binding` (additive field), else the default.

A declared binding is a list of dicts in the two dataclasses’ shapes
(`{"axis", "slot", "property", "gain"[, "rig_scaled"]}` or
`{"axis", "slot", "set_family"}`). An unknown axis in it is an error.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[`Union`[[`ChannelBinding`](cutan.expression.binding.md#cutan.expression.binding.ChannelBinding), [`SetBinding`](cutan.expression.binding.md#cutan.expression.binding.SetBinding)]]

### cutan.expression.clamp_axes(values)

Clamp every numeric axis to its range; an unknown axis is an error.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`float`](https://docs.python.org/3/builtins/functions.html#float)]

```pycon
>>> clamp_axes({"brow_height_l": 2.0, "lid_open_r": -3.0})
{'brow_height_l': 1.0, 'lid_open_r': -1.0}
>>> clamp_axes({"eyebrow": 1.0})
Traceback (most recent call last):
...
ValueError: unknown expression axis 'eyebrow' (known: brow_angle_l, ...)
```

### cutan.expression.declared_mouth_variants(desc)

`{form: set name}` for every `viseme@<form>` set the descriptor declares.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

```pycon
>>> declared_mouth_variants(CharacterDescriptor(name="m"))
{}
```

### cutan.expression.default_binding(desc)

The binding the default rig implies, from the slots it actually has.

The brow angle’s screen sign: PixiJS rotation is clockwise-positive with y
down, so on the LEFT brow (screen-left) a clockwise turn drops the inner
end while on the RIGHT brow it lifts it — the axis says “+ = inner end
up”, hence `-travel` on the left and `+travel` on the right.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[`Union`[[`ChannelBinding`](cutan.expression.binding.md#cutan.expression.binding.ChannelBinding), [`SetBinding`](cutan.expression.binding.md#cutan.expression.binding.SetBinding)]]

### cutan.expression.expression_problems(desc, , preset, axes=(), who)

Every reason an expression cannot resolve on `desc` — empty means it can.

Shared by `an validate` (each becomes an error Finding) and the compiler
(which raises [`ExpressionResolutionError`](#cutan.expression.ExpressionResolutionError) with the same list).

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

```pycon
>>> expression_problems(CharacterDescriptor(name="m"), preset="joyful", who="m")
["unknown expression preset 'joyful' (known: neutral, happy, sad, angry, surprised, afraid, disgusted, thinking, skeptical, amused)"]
>>> expression_problems(CharacterDescriptor(name="m", face_overlay=False), preset="happy", who="m")[0].startswith("'m' has its face baked")
True
```

### cutan.expression.expression_spans(shot, entity_id)

Every expression contributor on `entity_id`: authored leaves, then
dialogue sugar. `duration=None` runs to the shot end (the looping-play
rule); a span never extends past the shot.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`ExpressionSpan`](cutan.expression.provider.md#cutan.expression.provider.ExpressionSpan)]

### cutan.expression.from_blendshapes(coefficients)

Fold unipolar coefficients onto the axes (summed, then clamped).

Unknown names raise — a misspelt coefficient must not vanish quietly.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`float`](https://docs.python.org/3/builtins/functions.html#float)]

### cutan.expression.known_presets()

The preset names, in declaration order.

* **Return type:**
  [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`...`](https://docs.python.org/3/builtins/constants.html#Ellipsis)]

```pycon
>>> known_presets()[:3]
('neutral', 'happy', 'sad')
```

### cutan.expression.lid_key(value, , available)

The eyelid key a lid state selects, degraded to the art the rig declares.

`wide` above +0.25, `open`, `half` below −0.35, `closed` below −0.85;
a rig without `half` stays open until the lower threshold and one without
`wide` stays open above the upper one — never a blend of two drawings.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### cutan.expression.mouth_form_of(preset)

The `viseme@<form>` a preset prefers, or `None` for the neutral set.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

```pycon
>>> mouth_form_of("amused"), mouth_form_of("thinking"), mouth_form_of(None)
('happy', None, None)
```

### cutan.expression.preset_axes(preset, , axes=None, intensity=1.0)

The numeric axis offsets an expression asks for: the preset’s, with
`axes` layered over them, scaled by `intensity` and clamped. Only
non-zero offsets are returned, so a neutral expression is `{}`.

An unknown preset or axis is a `ValueError` — validate reports it as an
error, the compiler refuses it.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`float`](https://docs.python.org/3/builtins/functions.html#float)]

### cutan.expression.resolve_mouth_set(desc, preset, , keys_used, who=None)

Which mouth set a line under `preset` uses — the one chain, shared.

`viseme@<form>` if the preset prefers a form the descriptor declares and
that set covers `keys_used`; else `viseme` with a warning naming what
was missing; else [`ExpressionResolutionError`](#cutan.expression.ExpressionResolutionError). A descriptor with no
`viseme` set and no covering variant cannot speak at all — that is the
error, not a fallback.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### cutan.expression.variant_set_name(form)

The swap-set name for a mouth form (`@` is a legal set-name character).

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

```pycon
>>> variant_set_name("happy")
'viseme@happy'
```

### Modules

| [`axes`](cutan.expression.axes.md#module-cutan.expression.axes)                 | The facial expression axes: what a cutout face can be asked to do (an#98).           |
|----------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------|
| [`binding`](cutan.expression.binding.md#module-cutan.expression.binding)           | How the axes reach a character: the binding and the mouth-set resolver (an#98).      |
| [`blendshapes`](cutan.expression.blendshapes.md#module-cutan.expression.blendshapes)   | The 52-coefficient blendshape vocabulary, as an import/export mapping (an#98).       |
| [`presets`](cutan.expression.presets.md#module-cutan.expression.presets)           | Expression presets: our art direction on the axes (an#98).                           |
| [`provider`](cutan.expression.provider.md#module-cutan.expression.provider)         | The expression provider: authored leaves + dialogue sugar → per-axis curves (an#98). |
| [`registration`](cutan.expression.registration.md#module-cutan.expression.registration) | The face side of the cut-out genre, as declarations: `expression` and `[emotion]`.   |
