# cutan.characters.placement

Where an attachment’s anchor is drawn at rest, and placing it somewhere else.

The position is the one the core’s rig builder gives the attachment’s node
(`an.stage.rig.build_rig_subtree`), read from the same rules it reads
(`bone_positions`, `rig_origin`, `slot_parent_chain`, `nesting_of`,
`drawn_attachment`, `rest_transform`), in \*\*view_box units from the rig’s
origin\*\*: a node’s scene position divided by the builder’s `k`.

- [`rest_anchor()`](#cutan.characters.placement.rest_anchor) says where an attachment’s anchor is drawn, and how its
  picture is turned and scaled there (its bone’s rest pose, composed with the
  parts it nests under).
- [`place_attachment()`](#cutan.characters.placement.place_attachment) sets the attachment’s `x`/`y` so its anchor is
  drawn at a given point.

An attachment is named as [`cutan.characters.set_part.part_path()`](cutan.characters.set_part.html.md#cutan.characters.set_part.part_path) names it
(`name`, or `slot/name`). Both raise `SetPartError` for an unknown or
ambiguous attachment, a slot or bone the rig does not declare, a bone cycle, or
a part nested under one that draws nothing.

### Functions

| [`find_attachment`](#cutan.characters.placement.find_attachment)(desc, attachment)                 | `(skin, slot, name, Attachment)` for `name` or `slot/name` in the descriptor `desc`: from the skin the builder draws when it carries it, else from the first skin that does.                             |
|----------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`place_attachment`](#cutan.characters.placement.place_attachment)(char_dir, attachment, \*, world) | Set `attachment`'s `x`/`y` so its anchor is drawn at `world` (view_box units from the rig's origin, as [`rest_anchor()`](#cutan.characters.placement.rest_anchor) gives it); return where it now is. |
| [`rest_anchor`](#cutan.characters.placement.rest_anchor)(char_dir, attachment)                 | Where `attachment`'s anchor is drawn at rest (see [`RestAnchor`](#cutan.characters.placement.RestAnchor)).                                                                                          |

### Classes

| [`RestAnchor`](#cutan.characters.placement.RestAnchor)(slot, name, skin, world, frame, ...)   | Where an attachment's anchor is drawn at rest.   |
|----------------------------------------------------------------------------------------------------|--------------------------------------------------|

### *class* cutan.characters.placement.RestAnchor(slot, name, skin, world, frame, linear, anchor)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Where an attachment’s anchor is drawn at rest.

slot, name, skin: the attachment found (the skin is the one the builder draws
: when it carries the attachment, else the first that does)

world: the anchor’s position, view_box units from the rig’s origin
frame: how the parts it nests under map an offset of its node (identity

> when none of them is turned or scaled)

linear: how its picture is drawn there (`frame` times its bone’s rest pose)
anchor: the anchor, 0..1 of its picture

#### *property* posed *: [bool](https://docs.python.org/3/builtins/functions.html#bool)*

Whether its picture is drawn turned or scaled (a point of it moves off
`world + offset`).

### cutan.characters.placement.find_attachment(desc, attachment)

`(skin, slot, name, Attachment)` for `name` or `slot/name` in the
descriptor `desc`: from the skin the builder draws when it carries it, else
from the first skin that does. Raises `SetPartError` when no slot, or
more than one, carries it.

* **Return type:**
  [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### cutan.characters.placement.place_attachment(char_dir, attachment, , world)

Set `attachment`’s `x`/`y` so its anchor is drawn at `world` (view_box
units from the rig’s origin, as [`rest_anchor()`](#cutan.characters.placement.rest_anchor) gives it); return where it
now is. The attachments of the same slot and skin drawn by the same file move
with it (one picture, one place); other slots, skins and files are left alone.

```pycon
>>> import tempfile
>>> from cutan.characters import new_character
>>> d = new_character(tempfile.mkdtemp(), name="n", seed="n", use_dicebear=False).parent
>>> place_attachment(d, "arm_l", world=(-100.0, -240.0)).world
(-100.0, -240.0)
```

* **Return type:**
  [`RestAnchor`](#cutan.characters.placement.RestAnchor)

### cutan.characters.placement.rest_anchor(char_dir, attachment)

Where `attachment`’s anchor is drawn at rest (see [`RestAnchor`](#cutan.characters.placement.RestAnchor)).

```pycon
>>> import tempfile
>>> from cutan.characters import new_character
>>> d = new_character(tempfile.mkdtemp(), name="n", seed="n", use_dicebear=False).parent
>>> rest_anchor(d, "torso").world  # the torso bone, from the rig's origin
(0.0, -20.0)
```

* **Return type:**
  [`RestAnchor`](#cutan.characters.placement.RestAnchor)
