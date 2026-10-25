# cutan.characters.hands

A character’s hands as named points: `ned@hand_r` (an#502, reeleehq/cutan#104).

The core’s hold verbs (`grasp`, `place`, `release`, `handover`,
`swap`: `an.ir.holds`) move a point of a body, and the core knows no part
by name. A cut-out character’s rig contract does: its arms are the slots
`arm_l` and `arm_r` (`arm_l` the viewer’s left on the unmirrored rig),
and whatever hangs from them (a forearm under `nesting: bones`, a `hand_r`
part) is the rest of the arm. So the genre names the hands for the core
(`an.genres.EntityKind.landmarks`):

- a rig with a `hand_l` / `hand_r` BONE needs nothing from here: the core
  reads a bone as a point first (a grip landmark, cutan#104’s hand bone);
- a rig with a `hand_l` / `hand_r` SLOT (a drawn hand) holds at the
  middle of that drawing;
- otherwise the hand is the far end of the last part of the arm’s chain (the
  arm itself on a one-piece arm, the forearm on a bent one): its end effector.

So `{kind: grasp, by: stu@hand_r, item: musket}` works on a factory
character, a carved one with one-stroke arms, and one with an elbow, and keeps
working when the rig gains hand bones.

### Module Attributes

| [`HANDS`](#cutan.characters.hands.HANDS)   | The hands the genre names, and the arm slot each one ends.   |
|----------------------------------------------------------|--------------------------------------------------------------|

### Functions

| [`character_landmarks`](#cutan.characters.hands.character_landmarks)(desc)   | `{hand: (slot, point)}` for a character descriptor: the slot whose part holds things for that hand, and the point on it (a fraction of its drawing, or `None`: its far end).   |
|------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|

### cutan.characters.hands.HANDS *: [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [str](https://docs.python.org/3/builtins/stdtypes.html#str)]* *= {'hand_l': 'arm_l', 'hand_r': 'arm_r'}*

The hands the genre names, and the arm slot each one ends.

### cutan.characters.hands.character_landmarks(desc)

`{hand: (slot, point)}` for a character descriptor: the slot whose part
holds things for that hand, and the point on it (a fraction of its drawing,
or `None`: its far end).

```pycon
>>> rig = {"bones": [{"name": "torso"}, {"name": "arm_r", "parent": "torso"},
...                  {"name": "fore_r", "parent": "arm_r"}, {"name": "arm_l", "parent": "torso"}],
...        "slots": [{"name": "torso", "bone": "torso"}, {"name": "arm_r", "bone": "arm_r"},
...                  {"name": "fore_r", "bone": "fore_r"}, {"name": "arm_l", "bone": "arm_l"}]}
>>> character_landmarks(rig)
{'hand_l': ('arm_l', None), 'hand_r': ('fore_r', None)}
>>> rig["slots"].append({"name": "hand_l", "bone": "arm_l"})
>>> character_landmarks(rig)["hand_l"]
('hand_l', (0.5, 0.5))
```

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`float`](https://docs.python.org/3/builtins/functions.html#float), [`float`](https://docs.python.org/3/builtins/functions.html#float)] | [`None`](https://docs.python.org/3/builtins/constants.html#None)]]
