# cutan.expression.binding

How the axes reach a character: the binding and the mouth-set resolver (an#98).

Renderer-free, like [`cutan.characters.play`](cutan.characters.play.html.md#module-cutan.characters.play) — `an validate`,
`an character validate` and the cutout face solver all call the same
functions here, so the three cannot disagree about whether an expression can
resolve on a character.

- A **channel binding** maps a numeric axis onto `(slot, property, gain)`:
  the solver emits `rest + Σ axis·gain` on that slot’s node. The brow angle’s
  per-side sign lives in the gain — the two sides rotate in opposite screen
  directions for one axis sign.
- A **set binding** maps a lid axis onto a slot’s swap set (`eyelid`); the
  solver reads a key off the ladder in [`cutan.expression.axes`](cutan.expression.axes.html.md#module-cutan.expression.axes).
- `resolve_mouth_set` is the ONE chain for “which mouth set does this line
  use”: `viseme@<form>` if declared **and** it covers the keys the line
  uses, else `viseme` with a warning naming the missing keys, else an
  [`ExpressionResolutionError`](#cutan.expression.binding.ExpressionResolutionError) (a speaking overlay face with no neutral
  > mouth set).

```pycon
>>> from cutan.characters.schema import CharacterDescriptor
>>> desc = CharacterDescriptor(name="m")
>>> sorted({b.axis for b in default_binding(desc)})
['brow_angle_l', 'brow_angle_r', 'brow_height_l', 'brow_height_r', 'lid_open_l', 'lid_open_r']
>>> resolve_mouth_set(desc, None, keys_used=["A", "X"])
'viseme'
>>> import warnings
>>> with warnings.catch_warnings(record=True) as w:
...     warnings.simplefilter("always")
...     resolve_mouth_set(desc, "happy", keys_used=["A", "X"])
'viseme'
>>> "viseme@happy" in str(w[0].message)
True
```

### Module Attributes

| [`BROW_HEIGHT_TRAVEL`](#cutan.expression.binding.BROW_HEIGHT_TRAVEL)   | Brow travel per unit of `brow_height_*`, in the rig's view-box units (scaled to scene pixels by the entity's rig factor).                             |
|-----------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`BROW_ANGLE_TRAVEL`](#cutan.expression.binding.BROW_ANGLE_TRAVEL)    | Brow rotation per unit of `brow_angle_*`, radians.                                                                                                    |
| [`GAZE_TRAVEL`](#cutan.expression.binding.GAZE_TRAVEL)          | Pupil travel per unit of `gaze_*`, in view-box units — the default when a descriptor declares no travel of its own (`add_gaze` writes `gaze_travel`). |
| [`LID_SQUASH_GAIN`](#cutan.expression.binding.LID_SQUASH_GAIN)      | On a rig whose eye squashes instead of swapping art, a lid offset scales the eye by this much per unit.                                               |

### Functions

| [`binding_for`](#cutan.expression.binding.binding_for)(desc)                                | The descriptor's declared `expression_binding` (additive field), else the default.                                                                                                                                                                                                                                                               |
|---------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`declared_mouth_variants`](#cutan.expression.binding.declared_mouth_variants)(desc)                    | `{form: set name}` for every `viseme@<form>` set the descriptor declares.                                                                                                                                                                                                                                                                        |
| [`default_binding`](#cutan.expression.binding.default_binding)(desc)                            | The binding the default rig implies, from the slots it actually has.                                                                                                                                                                                                                                                                             |
| [`expression_problems`](#cutan.expression.binding.expression_problems)(desc, \*, preset[, axes])    | Every reason an expression cannot resolve on `desc` — empty means it can.                                                                                                                                                                                                                                                                        |
| [`preset_axes`](#cutan.expression.binding.preset_axes)(preset, \*[, axes, intensity])       | The numeric axis offsets an expression asks for: the preset's, with `axes` layered over them, scaled by `intensity` and clamped.                                                                                                                                                                                                                 |
| [`missing_mouth_form`](#cutan.expression.binding.missing_mouth_form)(desc, preset, \*[, who])      | Why `preset`'s mouth form will not show on `desc` — the descriptor declares no `viseme@<form>` set, so the mouth stays on the neutral chart, silent or speaking (an#253) — with the command that adds it; `None` when the preset has no form, the set exists, or there is no overlay mouth to change (a baked face, a rig with no `viseme` set). |
| [`lid_rung_problems`](#cutan.expression.binding.lid_rung_problems)(desc, preset, \*[, axes, ...]) | What an expression's lids ask for that `desc`'s eyelid art cannot show (an#272): a rig whose `eyelid` set draws `OPEN` and `CLOSED` picks a DRAWING per lid state (the ladder: wide, open, half, closed), so a partial lid on a rig with no `HALF` drawing shows `OPEN`, the same picture as no expression at all.                               |
| [`resolve_mouth_set`](#cutan.expression.binding.resolve_mouth_set)(desc, preset, \*, keys_used)   | Which mouth set a line under `preset` uses — the one chain, shared.                                                                                                                                                                                                                                                                              |
| [`touches_gaze`](#cutan.expression.binding.touches_gaze)(axes)                               | Whether any of `axes` is a gaze axis (a no-op on a rig without pupils).                                                                                                                                                                                                                                                                          |
| [`variant_set_name`](#cutan.expression.binding.variant_set_name)(form)                           | The swap-set name for a mouth form (`@` is a legal set-name character).                                                                                                                                                                                                                                                                          |

### Classes

| [`ChannelBinding`](#cutan.expression.binding.ChannelBinding)(axis, slot, property, gain[, ...])   | A numeric axis driving one transform property of one slot's node.   |
|------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------|
| [`SetBinding`](#cutan.expression.binding.SetBinding)(axis, slot[, set_family])                | A lid axis driving one slot's swap set through the ladder.          |

### Exceptions

| [`ExpressionResolutionError`](#cutan.expression.binding.ExpressionResolutionError)(who, problems)   | An expression that cannot resolve on a character; `problems` says why.   |
|---------------------------------------------------------------------------------------------|--------------------------------------------------------------------------|

### cutan.expression.binding.BROW_ANGLE_TRAVEL *: [float](https://docs.python.org/3/builtins/functions.html#float)* *= 0.35*

Brow rotation per unit of `brow_angle_*`, radians. Art direction.

### cutan.expression.binding.BROW_HEIGHT_TRAVEL *: [float](https://docs.python.org/3/builtins/functions.html#float)* *= 10.0*

Brow travel per unit of `brow_height_*`, in the rig’s view-box units
(scaled to scene pixels by the entity’s rig factor). Art direction; about
the synthesized eye’s half-height.

### *class* cutan.expression.binding.ChannelBinding(axis, slot, property, gain, rig_scaled=False)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A numeric axis driving one transform property of one slot’s node.

#### rig_scaled *: [bool](https://docs.python.org/3/builtins/functions.html#bool)* *= False*

Whether the gain is a view-box length (scaled by the rig factor).

### *exception* cutan.expression.binding.ExpressionResolutionError(who, problems)

Bases: [`ValueError`](https://docs.python.org/3/builtins/exceptions.html#ValueError)

An expression that cannot resolve on a character; `problems` says why.

### cutan.expression.binding.GAZE_TRAVEL *: [float](https://docs.python.org/3/builtins/functions.html#float)* *= 6.0*

Pupil travel per unit of `gaze_*`, in view-box units — the default when a
descriptor declares no travel of its own (`add_gaze` writes `gaze_travel`).

### cutan.expression.binding.LID_SQUASH_GAIN *: [float](https://docs.python.org/3/builtins/functions.html#float)* *= 0.5*

On a rig whose eye squashes instead of swapping art, a lid offset scales
the eye by this much per unit.

### *class* cutan.expression.binding.SetBinding(axis, slot, set_family='eyelid')

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A lid axis driving one slot’s swap set through the ladder.

### cutan.expression.binding.binding_for(desc)

The descriptor’s declared `expression_binding` (additive field), else the default.

A declared binding is a list of dicts in the two dataclasses’ shapes
(`{"axis", "slot", "property", "gain"[, "rig_scaled"]}` or
`{"axis", "slot", "set_family"}`). An unknown axis in it is an error.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[`Union`[[`ChannelBinding`](#cutan.expression.binding.ChannelBinding), [`SetBinding`](#cutan.expression.binding.SetBinding)]]

### cutan.expression.binding.declared_mouth_variants(desc)

`{form: set name}` for every `viseme@<form>` set the descriptor declares.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

```pycon
>>> declared_mouth_variants(CharacterDescriptor(name="m"))
{}
```

### cutan.expression.binding.default_binding(desc)

The binding the default rig implies, from the slots it actually has.

The brow angle’s screen sign: PixiJS rotation is clockwise-positive with y
down, so on the LEFT brow (screen-left) a clockwise turn drops the inner
end while on the RIGHT brow it lifts it — the axis says “+ = inner end
up”, hence `-travel` on the left and `+travel` on the right.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[`Union`[[`ChannelBinding`](#cutan.expression.binding.ChannelBinding), [`SetBinding`](#cutan.expression.binding.SetBinding)]]

### cutan.expression.binding.expression_problems(desc, , preset, axes=(), who)

Every reason an expression cannot resolve on `desc` — empty means it can.

Shared by `an validate` (each becomes an error Finding) and the compiler
(which raises [`ExpressionResolutionError`](#cutan.expression.binding.ExpressionResolutionError) with the same list).

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

```pycon
>>> expression_problems(CharacterDescriptor(name="m"), preset="joyful", who="m")
["unknown expression preset 'joyful' (known: neutral, happy, sad, angry, surprised, afraid, disgusted, thinking, skeptical, amused)"]
>>> expression_problems(CharacterDescriptor(name="m", face_overlay=False), preset="happy", who="m")[0].startswith("'m' has its face baked")
True
```

### cutan.expression.binding.lid_rung_problems(desc, preset, , axes=None, intensity=1.0, who=None)

What an expression’s lids ask for that `desc`’s eyelid art cannot show
(an#272): a rig whose `eyelid` set draws `OPEN` and `CLOSED` picks a
DRAWING per lid state (the ladder: wide, open, half, closed), so a partial
lid on a rig with no `HALF` drawing shows `OPEN`, the same picture as no
expression at all. One sentence per lid axis that falls short; empty for a
preset with no lid, a rig whose lids squash (no closed art: continuous), or
a baked face.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

```pycon
>>> d = CharacterDescriptor(name="bob", asset_sets={"eyelid": {"OPEN": "o", "CLOSED": "c"}})
>>> lid_rung_problems(d, None, axes={"lid_open_l": -0.45})
["bob's eyelids have no 'HALF' drawing, so lid_open_l -0.45 shows 'OPEN' (its eyelid set: CLOSED, OPEN): add a HALF eyelid drawing to the set (`an character add-half-lid bob` makes one from the rig's own lids), or use -0.85 or lower to close the lid"]
>>> lid_rung_problems(d, None, axes={"lid_open_l": -0.9})
[]
```

### cutan.expression.binding.missing_mouth_form(desc, preset, , who=None)

Why `preset`’s mouth form will not show on `desc` — the descriptor
declares no `viseme@<form>` set, so the mouth stays on the neutral chart,
silent or speaking (an#253) — with the command that adds it; `None` when
the preset has no form, the set exists, or there is no overlay mouth to
change (a baked face, a rig with no `viseme` set).

One sentence for `an validate` (an `expression` and a dialogue
`[emotion]`) and the compiler’s silent-mouth hold.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

```pycon
>>> d = CharacterDescriptor(name="ned", asset_sets={"viseme": {"X": "mouth_x"}})
>>> missing_mouth_form(d, "angry")
"ned declares no 'viseme@angry' set, so under 'angry' its mouth keeps the neutral chart, silent or speaking: add it with `an character mouths ned --variants angry`"
>>> missing_mouth_form(d, "thinking") is None
True
```

### cutan.expression.binding.preset_axes(preset, , axes=None, intensity=1.0)

The numeric axis offsets an expression asks for: the preset’s, with
`axes` layered over them, scaled by `intensity` and clamped. Only
non-zero offsets are returned, so a neutral expression is `{}`.

An unknown preset or axis is a `ValueError` — validate reports it as an
error, the compiler refuses it.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`float`](https://docs.python.org/3/builtins/functions.html#float)]

### cutan.expression.binding.resolve_mouth_set(desc, preset, , keys_used, who=None)

Which mouth set a line under `preset` uses — the one chain, shared.

`viseme@<form>` if the preset prefers a form the descriptor declares and
that set covers `keys_used`; else `viseme` with a warning naming what
was missing; else [`ExpressionResolutionError`](#cutan.expression.binding.ExpressionResolutionError). A descriptor with no
`viseme` set and no covering variant cannot speak at all — that is the
error, not a fallback.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### cutan.expression.binding.touches_gaze(axes)

Whether any of `axes` is a gaze axis (a no-op on a rig without pupils).

* **Return type:**
  [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

```pycon
>>> touches_gaze(["gaze_x"]), touches_gaze(["brow_angle_l"])
(True, False)
```

### cutan.expression.binding.variant_set_name(form)

The swap-set name for a mouth form (`@` is a legal set-name character).

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

```pycon
>>> variant_set_name("happy")
'viseme@happy'
```
