# cutan.characters.feet

A character’s feet as named points: `paul@foot_l` (an#519, cutan#201).

The core’s support check (`{type: support, a: paul, b: ground}`, an#797) needs
the points of a body that touch what it stands on. The core derives them from
the rig’s origin or its ink when the genre names none; a cut-out character’s rig
contract names them: its legs are the slots `leg_l` and `leg_r`, so the genre
gives the core `foot_l` / `foot_r`
(`an.genres.EntityKind.contacts`), as [`cutan.characters.hands`](cutan.characters.hands.html.md#module-cutan.characters.hands) gives
it the hands:

- a rig with a `foot_l` / `foot_r` BONE needs nothing from here (the core
  reads a bone as a point first);
- a rig with a `foot_l` / `foot_r` SLOT (a drawn shoe) stands on the bottom
  centre of that drawing, its sole;
- otherwise the foot is the far end of the last part of the leg’s chain, from
  its pivot: the leg’s drawn bottom. A factory rig has no foot bone, so this is
  its foot; for a leg that swings from the hip it sweeps an arc, so a hip-swing
  walk’s feet leave the floor at the contact pose by `L * (1 - cos(stride))`
  (the geometry of a cut-out walk, recorded in cutan#201).

A rig with no leg slots gives nothing and the core falls to the rig’s origin.

### Module Attributes

| [`FEET`](#cutan.characters.feet.FEET)      | The feet the genre names, and the leg slot each one ends (the rig contract's leg names, `cutan.motion.WALK_LEG_NAMES`).   |
|------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------|
| [`FOOT_SOLE`](#cutan.characters.feet.FOOT_SOLE) | the bottom centre of its drawing, the sole.                                                                               |

### Functions

| [`character_contacts`](#cutan.characters.feet.character_contacts)(desc)   | `{foot: (slot, point)}` for a character descriptor: the slot whose part touches the ground for that foot, and the point on it (a fraction of its drawing, or `None`: its far end from its pivot).   |
|-----------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|

### cutan.characters.feet.FEET *: [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [str](https://docs.python.org/3/builtins/stdtypes.html#str)]* *= {'foot_l': 'leg_l', 'foot_r': 'leg_r'}*

The feet the genre names, and the leg slot each one ends (the rig contract’s
leg names, `cutan.motion.WALK_LEG_NAMES`).

### cutan.characters.feet.FOOT_SOLE *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[float](https://docs.python.org/3/builtins/functions.html#float), [float](https://docs.python.org/3/builtins/functions.html#float)]* *= (0.5, 1.0)*

the bottom centre of its drawing, the sole.

* **Type:**
  Where a drawn foot stands

### cutan.characters.feet.character_contacts(desc)

`{foot: (slot, point)}` for a character descriptor: the slot whose part
touches the ground for that foot, and the point on it (a fraction of its
drawing, or `None`: its far end from its pivot).

```pycon
>>> rig = {"bones": [{"name": "root"}, {"name": "leg_l", "parent": "root"}],
...        "slots": [{"name": "leg_l", "bone": "leg_l"}]}
>>> character_contacts(rig)
{'foot_l': ('leg_l', None)}
>>> rig["slots"].append({"name": "foot_l", "bone": "leg_l"})
>>> character_contacts(rig)["foot_l"]
('foot_l', (0.5, 1.0))
>>> character_contacts({"bones": [], "slots": []})
{}
```

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`float`](https://docs.python.org/3/builtins/functions.html#float), [`float`](https://docs.python.org/3/builtins/functions.html#float)] | [`None`](https://docs.python.org/3/builtins/constants.html#None)]]
