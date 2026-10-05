# cutan.compile.lowering

How the stage compiler lowers the cut-out genre’s actions, and reads a character’s swap sets.

The stage compiler (`an.stage.compile`) knows no cut-out kind by name. A genre
hands it an *action lowering* (`an.genres.ActionKind.lowering`) for each
kind that is more than a tween or set, and an *entity swap declaration*
(`an.genres.EntityKind.swap_declaration`) saying what a descriptor declares.
Both live here; the code they call is [`cutan.compile.passes`](cutan.compile.passes.html.md#module-cutan.compile.passes).

```pycon
>>> from cutan.characters.registration import PlayAction
>>> PLAY_LOWERING.extent_resolver(None)(PlayAction(target="a", animation="hop"))
0.5
```

### Module Attributes

| [`CHARACTERS_STORE`](#cutan.compile.lowering.CHARACTERS_STORE)   | The mall store holding character descriptors (a persisted name).   |
|---------------------------------------------------------------------|--------------------------------------------------------------------|

### Functions

| [`character_swap_declaration`](#cutan.compile.lowering.character_swap_declaration)(entity, mall)   | What a character's (migrated) descriptor declares, for the swap vocabulary.   |
|---------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------|

### Classes

| [`ExpressionLowering`](#cutan.compile.lowering.ExpressionLowering)()   | The `expression` action kind: the face solver's input, so it makes no clip of its own.   |
|-------------------------------------------------------------------------|------------------------------------------------------------------------------------------|
| [`PlayLowering`](#cutan.compile.lowering.PlayLowering)()         | The `play` action kind, as the stage compiler lowers it (an#7, an#166, an#220).          |

### cutan.compile.lowering.CHARACTERS_STORE *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'characters'*

The mall store holding character descriptors (a persisted name).

### *class* cutan.compile.lowering.ExpressionLowering

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

The `expression` action kind: the face solver’s input, so it makes no clip of its own.

#### expand(flat_list, \*\*kw)

Drop the `expression` leaves: `_add_face_clips` sums them per (node, property).

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)

### *class* cutan.compile.lowering.PlayLowering

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

The `play` action kind, as the stage compiler lowers it (an#7, an#166, an#220).

#### clip(action, \*\*kw)

The clip of one descriptor `play` (the presets were expanded already).

#### expand(flat_list, \*\*kw)

Replace each `play` of a motion preset by the tweens and sets it stands for.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)

#### extent_resolver(vocab)

`play -> seconds` for a play that names no duration, read off its
descriptor — and, for a walk, off the gait and scale the expansion will
fill in ([`cutan.compile.passes.preset_context_of()`](cutan.compile.passes.html.md#cutan.compile.passes.preset_context_of), cutan#12).

* **Return type:**
  [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)], [`float`](https://docs.python.org/3/builtins/functions.html#float)]

#### view_of(entity_swaps, vocab, , duration)

`flat -> the view its entity is in then`, for characters with per-view face sets.

### cutan.compile.lowering.character_swap_declaration(entity, mall)

What a character’s (migrated) descriptor declares, for the swap vocabulary.

`None` when the store has no descriptor for the entity (a procedural or
placeholder rig: its built nodes’ sets ARE its declaration).

* **Return type:**
  `SwapDeclaration` | [`None`](https://docs.python.org/3/builtins/constants.html#None)
