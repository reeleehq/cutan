# cutan.characters.limits

Hinge limits per part type: how far a cut-out figure’s joints may turn (cutan#104).

A rig’s bones are hinges (`an.stage.rig.rig_structure`: `Bone.parent` is the
joint, `Bone.limits` its range). Until now the factory wrote none, so a solved
arm could fold through its own shoulder. The genre knows what a neck, a shoulder,
an elbow, a wrist, a hip and a knee are, so it states the ranges, once, by \*part
type\*, and a style may loosen or tighten them (a marionette’s joints are loose;
`joints.limits` in a style spec, [`cutan.styles`](cutan.styles.html.md#module-cutan.styles)).

**Convention.** A range is `(lo, hi)` degrees about the bone’s rest angle,
written for the figure’s RIGHT side (the bone ending `_r`, at the viewer’s
right on the unmirrored front view). A positive angle turns the part clockwise
on screen, so a hanging right arm swings its hand toward the viewer’s LEFT,
that is toward the body: positive is *inward* (flexion), negative *outward*.
The left side is the mirror image, `(-hi, -lo)`. A part that is not sided
(the head) is symmetric by construction.

```pycon
>>> part_type("forearm_r"), part_type("arm_l"), part_type("head"), part_type("torso")
('elbow', 'shoulder', 'neck', None)
>>> limits_for("forearm_r"), limits_for("forearm_l")
((-10.0, 150.0), (-150.0, 10.0))
```

A style spec overrides by part type; the other types keep the genre’s:

```pycon
>>> limits_table({"joints": {"limits": {"elbow": [0, 90]}}})["elbow"]
(0.0, 90.0)
>>> limits_for("forearm_l", table=limits_table({"joints": {"limits": {"elbow": [0, 90]}}}))
(-90.0, 0.0)
```

Nothing here changes a character until [`apply_limits()`](#cutan.characters.limits.apply_limits) (or the factory’s
`add_limits`) writes the ranges onto its bones, and a bone’s range only acts
when a shot declares a joint, a verb (`pin`, `pull`, `join`) or a hold: a
scene that declares none of them compiles byte for byte as it did. A bone added
later (a split arm’s) has none until `add_limits` runs again.

### Module Attributes

| [`PART_TYPES`](#cutan.characters.limits.PART_TYPES)   | a `forearm_r` is an elbow before it is an arm.                                                         |
|---------------------------------------------------------------|--------------------------------------------------------------------------------------------------------|
| [`GENRE_LIMITS`](#cutan.characters.limits.GENRE_LIMITS) | `{part type: (lo, hi)}` degrees about the rest pose, for the right side (see the module's convention). |
| [`LOOSE_LIMITS`](#cutan.characters.limits.LOOSE_LIMITS) | what a puppet on strings has (the marionette style's `joints.limits`).                                 |

### Functions

| [`apply_limits`](#cutan.characters.limits.apply_limits)(bones, \*[, table, overwrite])   | Write each typed bone's range onto `bones` (in place); returns the names written.                                           |
|------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------|
| [`limits_for`](#cutan.characters.limits.limits_for)(bone, \*[, table])                 | The range of a bone by its name, mirrored for the left side; `None` for a bone with no type.                                |
| [`limits_table`](#cutan.characters.limits.limits_table)([style])                         | `{part type: (lo, hi)}`: the genre's defaults under a style's `joints.limits`.                                              |
| [`part_type`](#cutan.characters.limits.part_type)(bone)                               | The part type a bone's name stands for (a key of [`GENRE_LIMITS`](#cutan.characters.limits.GENRE_LIMITS)), or `None`. |

### cutan.characters.limits.GENRE_LIMITS *: [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[float](https://docs.python.org/3/builtins/functions.html#float), [float](https://docs.python.org/3/builtins/functions.html#float)]]* *= {'ankle': (-40.0, 40.0), 'elbow': (-10.0, 150.0), 'hip': (-80.0, 80.0), 'knee': (-5.0, 140.0), 'neck': (-45.0, 45.0), 'shoulder': (-180.0, 60.0), 'wrist': (-70.0, 70.0)}*

`{part type: (lo, hi)}` degrees about the rest pose,
for the right side (see the module’s convention). A person’s joint, as a
cartoon uses it: an elbow folds inward and barely hyperextends, a shoulder
swings overhead outward but only crosses the chest so far, a neck tilts but
does not roll the head upside down.

* **Type:**
  The genre’s defaults

### cutan.characters.limits.LOOSE_LIMITS *: [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[float](https://docs.python.org/3/builtins/functions.html#float), [float](https://docs.python.org/3/builtins/functions.html#float)]]* *= {'ankle': (-80.0, 80.0), 'elbow': (-170.0, 170.0), 'hip': (-120.0, 120.0), 'knee': (-170.0, 170.0), 'neck': (-90.0, 90.0), 'shoulder': (-180.0, 180.0), 'wrist': (-120.0, 120.0)}*

what a puppet on strings has (the marionette
style’s `joints.limits`). Everything can still not fold through itself.

* **Type:**
  Limits that hardly constrain

### cutan.characters.limits.PART_TYPES *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [Pattern](https://docs.python.org/3/library/re.html#re.Pattern)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)]], ...]* *= (('neck', re.compile('(neck|head)')), ('elbow', re.compile('(forearm|fore|lower_arm|elbow)')), ('wrist', re.compile('(hand|wrist)')), ('shoulder', re.compile('(arm|upper_arm|shoulder)')), ('knee', re.compile('(shin|calf|lower_leg|knee)')), ('ankle', re.compile('(foot|ankle)')), ('hip', re.compile('(leg|thigh|upper_leg|hip)')))*

a
`forearm_r` is an elbow before it is an arm. Each pattern reads the bone’s
name WITHOUT its side suffix (`_l`/`_r`). The names are the factory’s
(`arm`, `forearm`, `hand`, `leg`, `shin`) and the ones an
illustrator’s skeleton uses (`upper_arm`, `fore`, `thigh`, `calf`).

* **Type:**
  The part types a bone name stands for, in the order they are tried

### cutan.characters.limits.apply_limits(bones, , table=None, overwrite=False)

Write each typed bone’s range onto `bones` (in place); returns the names written.

A bone that already has `limits` is the artist’s and is kept, unless
`overwrite`.

```pycon
>>> from cutan.characters.schema import Bone
>>> rig = [Bone(name="arm_r"), Bone(name="fore_r", parent="arm_r"), Bone(name="root"),
...        Bone(name="hand_r", parent="fore_r", limits=(-5, 5))]
>>> apply_limits(rig)
['arm_r', 'fore_r']
>>> [(b.name, b.limits) for b in rig]
[('arm_r', (-180.0, 60.0)), ('fore_r', (-10.0, 150.0)), ('root', None), ('hand_r', (-5.0, 5.0))]
```

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

### cutan.characters.limits.limits_for(bone, , table=None)

The range of a bone by its name, mirrored for the left side; `None` for a bone with no type.

```pycon
>>> limits_for("head"), limits_for("arm_r"), limits_for("arm_l"), limits_for("root")
((-45.0, 45.0), (-180.0, 60.0), (-60.0, 180.0), None)
```

* **Return type:**
  [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`float`](https://docs.python.org/3/builtins/functions.html#float), [`float`](https://docs.python.org/3/builtins/functions.html#float)] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### cutan.characters.limits.limits_table(style=None)

`{part type: (lo, hi)}`: the genre’s defaults under a style’s `joints.limits`.

`style` is anything [`cutan.styles.resolve_style_spec()`](cutan.styles.html.md#cutan.styles.resolve_style_spec) reads (a
shipped name, a path, a spec mapping) or `None` for the genre’s defaults.
An unknown part type or a malformed range is refused, by name.

```pycon
>>> limits_table() == GENRE_LIMITS
True
>>> limits_table({"joints": {"limits": {"elbow": [-170, 170]}}})["elbow"]
(-170.0, 170.0)
>>> limits_table({"joints": {"limits": {"tail": [0, 10]}}})
Traceback (most recent call last):
...
ValueError: style joints.limits: unknown part type 'tail'; known: ankle, elbow, hip, knee, neck, shoulder, wrist
```

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`float`](https://docs.python.org/3/builtins/functions.html#float), [`float`](https://docs.python.org/3/builtins/functions.html#float)]]

### cutan.characters.limits.part_type(bone)

The part type a bone’s name stands for (a key of [`GENRE_LIMITS`](#cutan.characters.limits.GENRE_LIMITS)), or `None`.

A bone with no limbed name (`root`, `torso`, a prop’s `grip`) has no
type and no range.

```pycon
>>> [part_type(n) for n in ("neck", "arm_r", "fore_r", "hand_l", "leg_l", "shin_r", "root")]
['neck', 'shoulder', 'elbow', 'wrist', 'hip', 'knee', None]
```

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)
