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

**Rights are never loosened by accident.** A descriptor with no `source`
means “we made this” to `an`, so a carving with no provenance is refused
unless the caller says the art is its own (`ours=True`). A `source=` that
would loosen the carving’s licence class is refused unless `relicense=`
says who decided and why (`an`’s own rule for relaxing rights); the
carving’s source is kept beside it as `extra.carved_from` either way.

### Module Attributes

| [`ROOT_BONE`](#cutan.carve.prop.ROOT_BONE)   | The bone every carved prop hangs from, at the carving's anchor.   |
|--------------------------------------------------------------|-------------------------------------------------------------------|
| [`BASE_SLOT`](#cutan.carve.prop.BASE_SLOT)   | The slot of the base art (a single-part prop's only slot).        |

### Functions

| [`write_prop`](#cutan.carve.prop.write_prop)(carved, folder, \*[, name, unit, ...])   | Write `carved` to `folder` as `prop.json` + `parts/*.png`; return the descriptor.   |
|------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------|

### cutan.carve.prop.BASE_SLOT *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'body'*

The slot of the base art (a single-part prop’s only slot).

### cutan.carve.prop.ROOT_BONE *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'root'*

The bone every carved prop hangs from, at the carving’s anchor.

### cutan.carve.prop.write_prop(carved, folder, , name=None, unit=None, max_side=None, display_name=None, source=None, ours=False, relicense=None, overwrite=False)

Write `carved` to `folder` as `prop.json` + `parts/*.png`; return the descriptor.

* **Return type:**
  `PropDescriptor`

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

A [`PartSet`](cutan.carve.md#cutan.carve.PartSet) is written with its carving’s provenance:
build one with [`split_parts()`](cutan.carve.md#cutan.carve.split_parts) (its parts are cut from
that carving), never by hand from other carvings’ parts.

The root bone sits at the carving’s anchor. A split prop gets one bone per
part, at its pivot, parented to the root, and one slot per part above the
base, in the order the parts were listed. Nothing is written unless the
whole descriptor is valid.
