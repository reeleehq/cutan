# cutan.expression.registration

The face side of the cut-out genre, as declarations: `expression` and `[emotion]`.

What the cut-out genre ([`cutan.genre`](cutan.genre.html.md#module-cutan.genre)) registers from here:

- the **\`\`expression\`\` action kind** — [`ExpressionAction`](#cutan.expression.registration.ExpressionAction)
  (hold a facial expression, an#98): zero-width in a `sequence` when it runs
  to the shot end, and its `scene.md` spelling;
- the **\`\`[emotion]\`\` dialogue sugar** — `maya [happy]: Hi!` fills
  `an.ir.schema.Dialogue.emotion`, which the expression provider turns
  > into an expression over the line, in memory only.

Plain declarations: importing this module registers nothing.

```pycon
>>> EXPRESSION.name, EMOTION.opener, EMOTION.parse(" Happy ")
('expression', '[', 'happy')
```

### Module Attributes

| [`DFLT_EXPRESSION_BLEND_S`](#cutan.expression.registration.DFLT_EXPRESSION_BLEND_S)   | Default ramp in/out of an expression, seconds (0 = cut).   |
|----------------------------------------------------------------------------|------------------------------------------------------------|
| [`EMOTION_NAME_RE`](#cutan.expression.registration.EMOTION_NAME_RE)           | a preset name (`happy`, `wry-smile`).                      |

### Functions

| [`expression`](#cutan.expression.registration.expression)(target[, preset, axes, ...])   | Hold a facial expression on an entity (an#98).                                    |
|--------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------|
| [`expression_duration`](#cutan.expression.registration.expression_duration)(action, extent)       | An expression's span: its `duration`, else zero (it runs to the shot end).        |
| [`format_emotion`](#cutan.expression.registration.format_emotion)(line)                      | The `[…]` content for `line`, or `None` when it carries no emotion.               |
| [`parse_emotion`](#cutan.expression.registration.parse_emotion)(content)                    | `[happy]`'s content to the line's emotion, lower-cased; refuse a non-name.        |
| [`read_expression_md`](#cutan.expression.registration.read_expression_md)(item, \*, index)       | `{kind: expression, target, [preset], [axes], [intensity], [duration], [blend]}`. |
| [`write_expression_md`](#cutan.expression.registration.write_expression_md)(leaf)                 | The `scene.md` entry for `leaf` (`read_expression_md`'s inverse).                 |

### Classes

| [`ExpressionAction`](#cutan.expression.registration.ExpressionAction)(\*\*data)   | Hold a facial expression on an entity (an#98, epic #9 Wave 6).   |
|-------------------------------------------------------------------------------|------------------------------------------------------------------|

### cutan.expression.registration.DFLT_EXPRESSION_BLEND_S *: [float](https://docs.python.org/3/builtins/functions.html#float)* *= 0.15*

Default ramp in/out of an expression, seconds (0 = cut). The dialogue
`[emotion]` sugar uses its own in `an.expression.provider`.

### cutan.expression.registration.EMOTION_NAME_RE *= re.compile('[\\\\w-]+')*

a preset name (`happy`, `wry-smile`).

* **Type:**
  What an emotion name may be

### *class* cutan.expression.registration.ExpressionAction(\*\*data)

Bases: `ExtensionAction`

Hold a facial expression on an entity (an#98, epic #9 Wave 6).

`preset` names one of `an.expression.presets.PRESETS`; `axes`
are per-axis overrides layered on it (axis units, see
`an.expression.axes`); `None` + no axes is a cheap “return to
rest”. `duration=None` runs to the shot end (the looping-play rule) and
is **zero-width in a sequence**, like a looping `play`. `blend` ramps the
intensity in and out; two overlapping expressions cross-fade because the
face solver sums offsets. The dialogue `speaker [emotion]: …` bracket is
sugar for one of these over the line, desugared in memory only.

A leaf action, flattened like `play`: the compiler resolves it in the
face solver (one channel per `(node, property)`), never per action.

The ramp is a min over the two ends, so a span shorter than `2·blend`
never reaches full intensity (a 0.2 s expression at the default 0.15 s
blend peaks at 0.67) and a `duration=0` expression shows only where a
frame lands on it with `blend=0` — cut the blend for a flash.

#### model_config *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[ConfigDict]* *= {'extra': 'allow', 'populate_by_name': True, 'validate_by_alias': True, 'validate_by_name': True}*

Configuration for the model, should be a dictionary conforming to [`ConfigDict`][pydantic.config.ConfigDict].

### cutan.expression.registration.expression(target, preset=None, , axes=None, intensity=1.0, duration=None, blend=0.15)

Hold a facial expression on an entity (an#98).

`duration=None` runs to the shot end and counts as **zero** in a
`sequence`, as a looping `play` does:

* **Return type:**
  [`ExpressionAction`](#cutan.expression.registration.ExpressionAction)

```pycon
>>> [f.start for f in flatten(sequence(expression("a", "happy"), delay(1.0), expression("a", "sad")))]
[0.0, 1.0]
>>> flatten(expression("a", "angry", duration=2.0))[0].end
2.0
```

### cutan.expression.registration.expression_duration(action, extent)

An expression’s span: its `duration`, else zero (it runs to the shot end).

* **Return type:**
  [`float`](https://docs.python.org/3/builtins/functions.html#float)

```pycon
>>> expression_duration(ExpressionAction(target="a", duration=2.0), None)
2.0
>>> expression_duration(ExpressionAction(target="a"), None)
0.0
```

### cutan.expression.registration.format_emotion(line)

The `[…]` content for `line`, or `None` when it carries no emotion.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### cutan.expression.registration.parse_emotion(content)

`[happy]`’s content to the line’s emotion, lower-cased; refuse a non-name.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### cutan.expression.registration.read_expression_md(item, , index)

`{kind: expression, target, [preset], [axes], [intensity], [duration], [blend]}`.

Landed with its writer and round trip in one commit (an#98): the writer
skips unknown leaves, so a parser-only entry would vanish from scene.md on
the next sync and then from the JSON on the next md edit.

* **Return type:**
  [`ExpressionAction`](#cutan.expression.registration.ExpressionAction)

### cutan.expression.registration.write_expression_md(leaf)

The `scene.md` entry for `leaf` (`read_expression_md`’s inverse).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]
