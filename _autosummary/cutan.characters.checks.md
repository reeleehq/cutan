# cutan.characters.checks

The cut-out genre’s semantic checks: `play`, `expression`, turns, views and character refs.

Moved from `an.ir.validate` (an#225, an#246): the core’s validator runs whatever checks a genre registers
(`cutan.genre.CUTOUT`), and these are the cut-out ones.

### Functions

| [`check_character_refs`](#cutan.characters.checks.check_character_refs)(ctx)              | The cut-out genre's missing-character warning.                              |
|-----------------------------------------------------------------------------------------|-----------------------------------------------------------------------------|
| [`check_expression_actions`](#cutan.characters.checks.check_expression_actions)(ctx)          | The cut-out genre's `expression` / `[emotion]` check.                       |
| [`check_hidden_mouth_while_speaking`](#cutan.characters.checks.check_hidden_mouth_while_speaking)(ctx) | The cut-out genre's mouth-hidden-by-a-view warning.                         |
| [`check_play_actions`](#cutan.characters.checks.check_play_actions)(ctx)                | The cut-out genre's `play` check (`_check_play_actions()`).                 |
| [`check_turns`](#cutan.characters.checks.check_turns)(ctx)                       | The cut-out genre's contradicted-turn warning (`_check_turns()`).           |
| [`check_view_continuity`](#cutan.characters.checks.check_view_continuity)(ctx)             | The cut-out genre's view-across-a-cut warning (`_check_view_continuity()`). |

### Classes

| [`CharacterSwapChecks`](#cutan.characters.checks.CharacterSwapChecks)()   | The `character` entity kind's swap-reference checks (`EntityKind.swap_checks`).   |
|--------------------------------------------------------------------------|-----------------------------------------------------------------------------------|

### *class* cutan.characters.checks.CharacterSwapChecks

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

The `character` entity kind’s swap-reference checks (`EntityKind.swap_checks`).

#### *static* missing_set_hint(prop)

What to add to “names no declared asset set” for a missing `view` set.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

#### *static* whole_entity(action, desc, prop, keys, entity_id, , where, report, art_exists)

A swap on the character ITSELF is judged slot by slot (an#197, an#201).

* **Return type:**
  [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

### cutan.characters.checks.check_character_refs(ctx)

The cut-out genre’s missing-character warning. A WARNING: the compiler
falls back to the built-in placeholder rig and the scene still renders.
Deliberately not escalated — an asset-less project rendering placeholders
is a supported way to work.

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### cutan.characters.checks.check_expression_actions(ctx)

The cut-out genre’s `expression` / `[emotion]` check.

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### cutan.characters.checks.check_hidden_mouth_while_speaking(ctx)

The cut-out genre’s mouth-hidden-by-a-view warning.

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### cutan.characters.checks.check_play_actions(ctx)

The cut-out genre’s `play` check (`_check_play_actions()`).

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### cutan.characters.checks.check_turns(ctx)

The cut-out genre’s contradicted-turn warning (`_check_turns()`).

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### cutan.characters.checks.check_view_continuity(ctx)

The cut-out genre’s view-across-a-cut warning (`_check_view_continuity()`).

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)
