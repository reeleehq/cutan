# cutan.carve.prop

Write a carving (or a carving split into parts) as a library-ready prop folder.

The folder is the layout every `an` project store and the library read:
`prop.json` (a `PropDescriptor`) and `parts/*.png`.
The descriptor’s `source` is the carving’s provenance, recipe and quality
included, so publishing it records the rights without a single flag:

```default
from an.library import open_library, publish_dir
publish_dir(open_library("cutan"), folder, "prop.wall-clock", origin="carved")
```

(`an library publish <folder> prop.wall-clock --package cutan --origin carved`
from a shell.) One pixel of the carving is one view_box unit times `unit`,
and each part declares its size, so the prop draws the same whatever the
resolution the art was carved at.

**Where a hand holds it.** `landmarks=` names points of the prop (a sabre’s
grip and its tip, a mug’s handle) in the source’s pixels, the same frame as
`point`. Each is written as a bone with no slot, hung from the root: what
`an` reads as a rig’s named point (`an.stage.rig.rig_structure`’s
`anchors`), so a scene addresses it as `<prop>@<name>` (a joint’s
`wheel@grip`), and a bone called [`GRIP`](#cutan.carve.prop.GRIP) is where the hold verbs take
the prop by default (an#502). Two landmarks give an axis: `grip` and `tip`
say which way the blade points from the hand.

**Rights are never loosened by accident.** A descriptor with no `source`
means “we made this” to `an`, so a carving with no provenance is refused
unless the caller says the art is its own (`ours=True`). A `source=` that
would loosen the carving’s licence class is refused unless `relicense=`
says who decided and why (`an`’s own rule for relaxing rights); the
carving’s source is kept beside it as `extra.carved_from` either way.

### Module Attributes

| [`ROOT_BONE`](#cutan.carve.prop.ROOT_BONE)   | The bone every carved prop hangs from, at the carving's anchor.                                                     |
|--------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------|
| [`BASE_SLOT`](#cutan.carve.prop.BASE_SLOT)   | The slot of the base art (a single-part prop's only slot).                                                          |
| [`GRIP`](#cutan.carve.prop.GRIP)        | The landmark a hand takes a prop by when a scene names no other (an's hold verbs read a bone of this name; an#502). |

### Functions

| [`write_prop`](#cutan.carve.prop.write_prop)(carved, folder, \*[, name, unit, ...])   | Write `carved` to `folder` as `prop.json` + `parts/*.png`; return the descriptor.   |
|------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------|

### cutan.carve.prop.BASE_SLOT *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'body'*

The slot of the base art (a single-part prop’s only slot).

### cutan.carve.prop.GRIP *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'grip'*

The landmark a hand takes a prop by when a scene names no other (an’s hold
verbs read a bone of this name; an#502).

### cutan.carve.prop.ROOT_BONE *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'root'*

The bone every carved prop hangs from, at the carving’s anchor.

### cutan.carve.prop.write_prop(carved, folder, , name=None, unit=None, max_side=None, display_name=None, source=None, ours=False, relicense=None, landmarks=None, overwrite=False)

Write `carved` to `folder` as `prop.json` + `parts/*.png`; return the descriptor.

name: the prop’s name (default: the folder’s name)
unit: view_box units per carved pixel (default 1); or `max_side`: the

> unit that makes the longer side that many units (never above 1)

source: overrides the carving’s provenance (its recipe and quality are
: still recorded in `extra.carve`, its source in `extra.carved_from`)

ours: the pixels are the caller’s own art (a carving with no source)
relicense: `{"by": who, "reason": why}` (both non-empty), required for a

> `source` that loosens the carving’s licence class. Recorded in the
> descriptor’s `source.extra.relicensed`; `an library publish` does not
> read it, so say it again there (`relicense=`) when publishing.

landmarks: named points of the prop in the source’s pixels, each written
: as a slotless bone on the root: `{"grip": (x, y), "tip": (x, y)}`
  (`grip`, [`GRIP`](#cutan.carve.prop.GRIP), is where a hand takes it). See the module
  docstring. They are points of the prop as a whole: on a split prop a
  landmark does not follow a part that turns (a grip on a moving lid).

A [`PartSet`](cutan.carve.html.md#cutan.carve.PartSet) is written with its carving’s provenance:
build one with [`split_parts()`](cutan.carve.html.md#cutan.carve.split_parts) (its parts are cut from
that carving), never by hand from other carvings’ parts.

The root bone sits at the carving’s anchor, and the descriptor declares it
the rig’s `origin`: the prop stands where it is put by its anchor, whatever
other bones (parts, landmarks) it has. A split prop gets one bone per
part, at its pivot, parented to the root, and one slot per part above the
base, in the order the parts were listed. Nothing is written unless the
whole descriptor is valid.

* **Return type:**
  `PropDescriptor`
