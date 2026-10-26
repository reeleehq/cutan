# cutan.characters.set_part

Replace a factory part’s drawing with a picture (cutan#92).

A factory character draws every attachment as an SVG (`parts/head.svg`). An
illustrator, an image generator or a carve can instead supply a picture with an
alpha channel (PNG, WebP, JPEG): [`replace_part_art()`](#cutan.characters.set_part.replace_part_art) copies it beside the
rig, points every attachment that drew the old file at it, and keeps the box the
attachment already declared (or the old drawing’s root size, an#220), so the
slot draws it where and as large as the factory’s did. The old drawing’s
`colour_roles` and pinned source go with it: a picture’s pixels are not the
factory’s and a pack cannot recolour them. Nothing else in the descriptor moves,
so the swap channels and the rig contract are untouched.

[`set_part()`](#cutan.characters.set_part.set_part) is the by-name front: `an character set-part <name>
<attachment> <file>`.

### Functions

| [`part_path`](#cutan.characters.set_part.part_path)(char_dir, attachment)                    | The file `attachment` (`name`, or `slot/name` when several slots carry that name) is drawn by, as the descriptor records it (`parts/head.svg`).                                                                      |
|-----------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`replace_part_art`](#cutan.characters.set_part.replace_part_art)(char_dir, old_rel, picture, \*)   | Draw every attachment that used `old_rel` (`parts/head.svg`) with `picture`.                                                                                                                                         |
| [`set_part`](#cutan.characters.set_part.set_part)(char_dir, attachment, picture, \*[, ...]) | Replace the drawing of `attachment` (see [`part_path()`](#cutan.characters.set_part.part_path)) with `picture`; `anchor` and `source` as [`replace_part_art()`](#cutan.characters.set_part.replace_part_art). |

### Classes

| [`PartReplacement`](#cutan.characters.set_part.PartReplacement)(descriptor, new_path[, derived])   | What [`replace_part_art()`](#cutan.characters.set_part.replace_part_art) did: the descriptor written, and the factory drawings DERIVED from the old part (`<stem>_*`: its views, lid states, mouth variants) that are still referenced and still the factory's, which a painted part would not match.   |
|-----------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|

### Exceptions

| [`SetPartError`](#cutan.characters.set_part.SetPartError)   | A part cannot be replaced; the message says what to do.   |
|-----------------------------------------------------------------|-----------------------------------------------------------|

### *class* cutan.characters.set_part.PartReplacement(descriptor, new_path, derived=list())

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

What [`replace_part_art()`](#cutan.characters.set_part.replace_part_art) did: the descriptor written, and the factory
drawings DERIVED from the old part (`<stem>_*`: its views, lid states,
mouth variants) that are still referenced and still the factory’s, which a
painted part would not match.

### *exception* cutan.characters.set_part.SetPartError

Bases: [`ValueError`](https://docs.python.org/3/builtins/exceptions.html#ValueError)

A part cannot be replaced; the message says what to do.

### cutan.characters.set_part.part_path(char_dir, attachment)

The file `attachment` (`name`, or `slot/name` when several slots carry
that name) is drawn by, as the descriptor records it (`parts/head.svg`).
Raises [`SetPartError`](#cutan.characters.set_part.SetPartError) when it names no attachment or an ambiguous one.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### cutan.characters.set_part.replace_part_art(char_dir, old_rel, picture, , anchor=None, source=None)

Draw every attachment that used `old_rel` (`parts/head.svg`) with `picture`.

The attachment keeps the WIDTH the old drawing rasterised at (`art_size`,
declared only when it declared none: the picture’s height follows its own
aspect, so a differently shaped picture is not squashed). `anchor` (`(u, v)`
in 0..1 of the picture) replaces the attachments’ anchor (default: keep it);
`source` is pinned to them as the picture’s provenance. Raises [`SetPartError`](#cutan.characters.set_part.SetPartError) when no attachment
draws `old_rel`, when `picture` is not a readable PNG/JPEG/WebP, or when
a path leaves the character’s folder.

* **Return type:**
  [`PartReplacement`](#cutan.characters.set_part.PartReplacement)

### cutan.characters.set_part.set_part(char_dir, attachment, picture, , anchor=None, source=None)

Replace the drawing of `attachment` (see [`part_path()`](#cutan.characters.set_part.part_path)) with
`picture`; `anchor` and `source` as [`replace_part_art()`](#cutan.characters.set_part.replace_part_art).

* **Return type:**
  [`PartReplacement`](#cutan.characters.set_part.PartReplacement)
