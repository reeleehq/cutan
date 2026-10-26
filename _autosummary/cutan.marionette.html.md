# cutan.marionette

The marionette style’s joints: a control bar, strings, hips (cutan#104).

A marionette is a cut-out figure hung from strings: the figure’s parts are
free bodies under gravity, the strings are the solver’s `string` joints (a
distance held at most, so one may go slack), and the **control bar** is a prop
the author moves (`tween` its `x`, `y`, `rotation`): the figure follows
on its strings, swings, and settles. This is the first puppet style on the
constraint layer (an#497, ADR 0008); the table of what is tied where is the
style spec’s `joints` block ([`cutan.styles`](cutan.styles.html.md#module-cutan.styles), `marionette.yaml`), and
this module turns it into the joints of one shot.

- [`write_control_bar()`](#cutan.marionette.write_control_bar) writes the bar prop, sized in scene pixels.
- [`marionette_joints()`](#cutan.marionette.marionette_joints) returns the shot’s `joints:`: one `string` per
  tied part and a hip hinge from each leg to the torso (the factory’s legs hang
  from the root, not the torso, so nothing else joins them).

A shot then has the character with `overrides: {free: true}` (its parts hang
from the strings instead of staying where they were staged), the bar, those
joints, and the style pack’s gravity (`meta.style_pack: marionette`):

```yaml
entities:
  - {kind: character, id: ned, store: characters, ref: ned, overrides: {free: true}}
  - {kind: prop, id: bar, store: props, ref: control_bar, stage: {at: [0, -120], after: ned}}
joints: <marionette_joints("ned", "bar")>
actions:
  - {kind: tween, target: bar, property: x, from: 0, to: 150, duration: 1.5}
```

```pycon
>>> [j["name"] for j in marionette_joints("ned", "bar")]
['ned.hip_l', 'ned.hip_r', 'ned.head', 'ned.hand_l', 'ned.hand_r', 'ned.knee_l', 'ned.knee_r']
>>> marionette_joints("ned", "bar")[2]
{'type': 'string', 'a': 'ned/head@0.5,0.0', 'b': 'bar@0.5,0.5', 'name': 'ned.head'}
```

### Module Attributes

| [`STYLE`](#cutan.marionette.STYLE)   | The style whose `joints` block holds the tables.   |
|----------------------------------------------------------|----------------------------------------------------|

### Functions

| [`marionette_joints`](#cutan.marionette.marionette_joints)(character, bar, \*[, rig, ...])   | The `joints:` of a shot that hangs `character` from `bar`.                        |
|------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------|
| [`write_control_bar`](#cutan.marionette.write_control_bar)(props_dir[, name, ...])           | Write a control bar prop `width_px` wide at `stage.scale: 1`; returns its folder. |

### cutan.marionette.STYLE *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'marionette'*

The style whose `joints` block holds the tables.

### cutan.marionette.marionette_joints(character, bar, , rig=None, style='marionette', strings=None)

The `joints:` of a shot that hangs `character` from `bar`.

`rig` is the character’s descriptor (a model or its document): a rig with
`hand_l`/`hand_r` bones (`add_forearms`) is tied by its hands, else by
the end of its arms. `style` is a spec (a shipped name or a mapping) whose
`joints` block says what is tied where, so another puppet style reuses
this builder with its own table; `strings` keeps only the named ones (a
puppet with its knees untied). Each joint is a plain mapping a shot’s
`joints` accepts, named `<character>.<string>`.

```pycon
>>> sorted({j["type"] for j in marionette_joints("ned", "bar")})
['hinge', 'string']
>>> [j["a"] for j in marionette_joints("ned", "bar", strings=["hand_l"], rig={"bones": [{"name": "hand_l"}]})][-1]
'ned/hand_l@hand_l'
```

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]]

### cutan.marionette.write_control_bar(props_dir, name='control_bar', , width_px=140.0, colour='#6b4e2e')

Write a control bar prop `width_px` wide at `stage.scale: 1`; returns its folder.

A plain horizontal bar, a drawing to replace with an illustrator’s. The strings are tied to fractions of the bar’s width
(`bar: [u, v]` in the style table), so a wider bar spreads them.

```pycon
>>> import tempfile
>>> with tempfile.TemporaryDirectory() as d:
...     folder = write_control_bar(d, width_px=100)
...     sorted(p.name for p in folder.iterdir())
['parts', 'prop.json']
```

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)
