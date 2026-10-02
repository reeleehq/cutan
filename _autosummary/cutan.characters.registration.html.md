# cutan.characters.registration

The character side of the cut-out genre, as declarations: `play` and `character`.

What the cut-out genre ([`cutan.genre`](cutan.genre.html.md#module-cutan.genre)) registers from here (ADR 0001
§First slice):

- the **\`\`play\`\` action kind** — [`PlayAction`](#cutan.characters.registration.PlayAction), how long a
  duration-less play occupies a `sequence` (its natural length, through the
  caller’s extent resolver), and its `scene.md` spelling;
- the **\`\`character\`\` entity kind** — a rigged character, whose nodes are
  nodes of the 2D stage engine (the `stage.node` property space).

Plain declarations: importing this module registers nothing.

```pycon
>>> PLAY.name, CHARACTER.space
('play', 'stage.node')
```

### Functions

| [`default_play_extent`](#cutan.characters.registration.default_play_extent)(action)                  | A duration-less play's extent when no descriptor is known: a motion preset's natural length over `speed`, else `0.0`.   |
|-----------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------|
| [`play`](#cutan.characters.registration.play)(target, animation, \*[, duration, ...]) | Play a named animation of the target entity's descriptor (an#7).                                                        |
| [`play_duration`](#cutan.characters.registration.play_duration)(action, extent)                | The span a `play` occupies: its `duration`, else its natural extent.                                                    |
| [`read_play_md`](#cutan.characters.registration.read_play_md)(item, \*, index)                | `{kind: play, target, animation, [duration], [speed], [loop], [args]}`.                                                 |
| [`write_play_md`](#cutan.characters.registration.write_play_md)(leaf)                          | The `scene.md` entry for `leaf` (`read_play_md`'s inverse).                                                             |

### Classes

| [`PlayAction`](#cutan.characters.registration.PlayAction)(\*\*data)   | Play a named animation of the target entity's descriptor (an#7).   |
|-------------------------------------------------------------------------|--------------------------------------------------------------------|

### *class* cutan.characters.registration.PlayAction(\*\*data)

Bases: `ExtensionAction`

Play a named animation of the target entity’s descriptor (an#7).

`animation` names an entry of `CharacterDescriptor.animations` (the
seeded `idle_breath` and `blink`, or anything an author adds); the
compiler resolves its tracks into channels on the entity’s nodes. A name
the descriptor does NOT declare — or any name on an entity with no
descriptor (a procedural rig, a prop) — falls back to the motion presets
of `an.motion.PRESETS` (`hop`, `nod`, …), which expand to
ordinary tweens at the target’s built rest pose; a descriptor animation of
the same name wins (an#166). Both halves are decided by
[`cutan.characters.play.play_problems()`](cutan.characters.play.html.md#cutan.characters.play.play_problems), the one resolver `an validate`
and the compiler share. For a preset, `args` are its parameters,
`duration` stretches the whole move to that length, `speed` divides
it, and `loop: true` is refused (a preset is a one-shot).
`duration` widens/narrows the placement window; `None` means the
animation’s own duration — or, when the resolved `loop` is true, the
rest of the shot, because a loop bounded by its own natural duration
never loops. `loop` overrides the animation’s declared `loop`
(`None` = use the descriptor’s). Inside a `sequence` a play with
`duration=None` occupies its NATURAL length — a motion preset’s own
length, a non-looping descriptor animation’s `duration`, both over
`speed` — so the next sibling starts when it ends; a looping one runs to
the shot end and occupies ZERO (`an.characters.play.play_extent()`).

#### args *: [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)] | [None](https://docs.python.org/3/builtins/constants.html#None)*

Parameters of a MOTION PRESET (an#166) — `{"height": 30}` for a
`hop` — passed to its `an.motion.PRESETS` function as keyword
arguments. `None` (the default, omitted from JSON) means the preset’s
own defaults. A descriptor animation takes none, and one given to it is
refused; `rest` is never one — it is read off the built scene.

#### model_config *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[ConfigDict]* *= {'extra': 'allow', 'populate_by_name': True, 'validate_by_alias': True, 'validate_by_name': True}*

Configuration for the model, should be a dictionary conforming to [`ConfigDict`][pydantic.config.ConfigDict].

### cutan.characters.registration.default_play_extent(action)

A duration-less play’s extent when no descriptor is known: a motion
preset’s natural length over `speed`, else `0.0`.

The one resolver is `cutan.characters.play.play_extent()`; this is it with
`desc=None`.

* **Return type:**
  [`float`](https://docs.python.org/3/builtins/functions.html#float)

```pycon
>>> default_play_extent(PlayAction(target="a", animation="hop"))
0.5
>>> default_play_extent(PlayAction(target="a", animation="not_a_preset"))
0.0
```

### cutan.characters.registration.play(target, animation, , duration=None, speed=1.0, loop=None, args=None)

Play a named animation of the target entity’s descriptor (an#7).

`duration=None` fills the animation’s natural length — or the shot’s
remainder for a looping one. In a `sequence` a play with no `duration`
occupies its **natural** length (a motion preset’s own length divided by
`speed`; a non-looping descriptor animation’s likewise), so the sibling
after it starts when it ends; a looping one runs to the shot end and
occupies **zero**:

* **Return type:**
  [`PlayAction`](#cutan.characters.registration.PlayAction)

```pycon
>>> [f.start for f in flatten(sequence(play("a", "idle_breath"), delay(1.0), play("a", "blink")))]
[0.0, 1.0]
>>> [f.start for f in flatten(sequence(play("a", "idle_breath", duration=2.0), play("a", "blink")))]
[0.0, 2.0]
>>> [f.start for f in flatten(sequence(play("a", "hop"), play("a", "nod")))]
[0.0, 0.5]
>>> [f.start for f in flatten(sequence(play("a", "hop", speed=2.0), play("a", "nod")))]
[0.0, 0.25]
```

(Bare `flatten` knows only the presets, by name; `an validate` and the
compiler pass the entity’s descriptor too — `cutan.characters.play.play_extent()`
— so a descriptor animation that shares a preset’s name is measured as the
descriptor’s.)

A name the descriptor does not declare falls back to a motion preset of
`an.motion.PRESETS`, with `args` as its parameters (an#166):

```pycon
>>> play("charlie", "hop", args={"height": 30}).args
{'height': 30}
```

### cutan.characters.registration.play_duration(action, extent)

The span a `play` occupies: its `duration`, else its natural extent.

`extent` is the caller’s resolver (the compiler and `an validate` pass
one bound to the entity’s descriptor); without one, a motion preset’s own
length ([`default_play_extent()`](#cutan.characters.registration.default_play_extent)).

* **Return type:**
  [`float`](https://docs.python.org/3/builtins/functions.html#float)

```pycon
>>> play_duration(PlayAction(target="a", animation="hop", duration=2.0), None)
2.0
>>> play_duration(PlayAction(target="a", animation="hop"), None)
0.5
```

### cutan.characters.registration.read_play_md(item, , index)

`{kind: play, target, animation, [duration], [speed], [loop], [args]}`.

Resolved at compile against the target entity’s descriptor `animations`
(an#7), falling back to the motion presets of `an.motion.PRESETS` for a
name the descriptor does not declare, with `args` as the preset’s
parameters (an#166). `loop` omitted means the animation’s own. This
reader accepted the shape from the start, then #24 made it refuse (nothing
resolved a play) while the writer kept emitting it — three days of a
project’s own scene.md failing to parse.

* **Return type:**
  [`PlayAction`](#cutan.characters.registration.PlayAction)

### cutan.characters.registration.write_play_md(leaf)

The `scene.md` entry for `leaf` (`read_play_md`’s inverse).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]
