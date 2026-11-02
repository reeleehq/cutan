# cutan.verify.critic

A vision critic for body-depicting props: narrow yes/no questions over probe frames (cutan#95).

The deterministic body-continuity check ([`cutan.verify.body`](cutan.verify.body.html.md#module-cutan.verify.body)) trusts the
sockets a prop declares: it cannot see whether a drawing’s sleeves really end
where its sockets say, or whether hands were drawn from the camera’s side. A
production shipped exactly that: a steering wheel with the driver’s hands drawn
from the driver’s seat, laid over a driver seen through the windscreen.

This critic looks. For each shot holding a prop that declares a
`metadata.body_attachment`, it probes frames of the shot (`an.probe.frames()`,
the path a render draws), asks a vision model a short checklist of yes/no
questions answerable from appearance, chosen by the prop’s declared `view`
([`CHECKLISTS`](#cutan.verify.critic.CHECKLISTS): a first-person prop’s arms DO come from the bottom edge),
and reports each answer that differs from the one a correct drawing gives as a
**warning**: never the gate. Free-form “does this look right?” is not asked:
vision models answer camera-perspective questions at about 34-47%
(ViewSpatial-Bench, arXiv 2505.21500); narrow questions about what is visible
fare better.

It is optional and costs money, so nothing runs it by default (the issue’s
`critic=None` keyword on the check’s function would not do: that check runs
inside `an validate`, which never renders). [`critique_body_props()`](#cutan.verify.critic.critique_body_props) takes
the judge (default: `an`’s paid seam, `an.verify.vision.judge_envelope()`)
and the frame source as keywords. A configured judge that fails is a failure (an
`error` finding), never a silent pass. Every call is recorded in the report
(shot, prop, frames, model): what it cost.

```pycon
>>> parse_answers('{"answers": [{"n": "1", "answer": "No."}]} Note: {x}', CHECKLISTS["front"])[0]
{'n': 1, 'answer': 'no', 'why': ''}
```

### Module Attributes

| [`CHECKLISTS`](#cutan.verify.critic.CHECKLISTS)          | Narrow questions about a prop that depicts a character's limbs, answerable from appearance, by the prop's declared `view` (`"*"`: any view not listed).   |
|----------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`FAR_PLATE_CHECKLIST`](#cutan.verify.critic.FAR_PLATE_CHECKLIST) | What a `far` plate of a travelling shot must not hold (ADR 0007 of `an`): anything nearer than the far range stands still while the streams move.         |

### Functions

| [`critique_body_props`](#cutan.verify.critic.critique_body_props)(project, \*[, judge, ...])   | Ask each body-depicting prop of `project`'s shots its view's checklist.                                                                                            |
|---------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`critique_far_plates`](#cutan.verify.critic.critique_far_plates)(project, \*[, judge, ...])   | Ask whether each `far` plate of `project`'s travel holds anything near (cutan#166): a tree baked into a plate stands still while the streams move.                 |
| [`checklist_for`](#cutan.verify.critic.checklist_for)(view[, checklists])                | The questions for a prop declared in `view`: a mapping's entry for it (else its `"*"`), or `checklists` itself when it is one list.                                |
| [`checklist_prompt`](#cutan.verify.critic.checklist_prompt)(checklist, \*, prop, character) | The prompt asking `checklist` about `prop` held by `character`.                                                                                                    |
| [`parse_answers`](#cutan.verify.critic.parse_answers)(reply, checklist)                  | The answers in a judge's reply, one per question (`answer` is `yes`, `no` or `unsure`: read from its leading word); `None` when the reply holds no answers at all. |

### Classes

| [`Question`](#cutan.verify.critic.Question)(text, expected)          | A yes/no question, and the answer a correct drawing gives.          |
|------------------------------------------------------------------------------------|---------------------------------------------------------------------|
| [`CritiqueReport`](#cutan.verify.critic.CritiqueReport)([findings, calls]) | The critic's findings, and every judge call it made (what it cost). |

### cutan.verify.critic.CHECKLISTS *: [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[Question](#cutan.verify.critic.Question), ...]]* *= {'\*': (Question(text='Does every sleeve or forearm touching the {prop} continue towards a shoulder of {character}, the person visible in the picture?', expected='yes'), Question(text="Do any forearms enter the picture from its bottom edge, as if they were the camera's own arms?", expected='no')), 'first_person': (Question(text="Do the forearms holding the {prop} enter the picture from its bottom edge, as if they were the camera's own arms?", expected='yes'), Question(text='Is the face of the person holding the {prop} visible in the picture?', expected='no')), 'front': (Question(text='Does every sleeve or forearm touching the {prop} continue towards a shoulder of {character}, the person visible in the picture?', expected='yes'), Question(text="Do any forearms enter the picture from its bottom edge, as if they were the camera's own arms?", expected='no'), Question(text="Are the hands on the {prop} seen from the same side as {character}'s face (both from the front)?", expected='yes'))}*

Narrow questions about a prop that depicts a character’s limbs, answerable
from appearance, by the prop’s declared `view` (`"*"`: any view not
listed). `{prop}` and `{character}` are filled in per shot.

### *class* cutan.verify.critic.CritiqueReport(findings=list(), calls=list())

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

The critic’s findings, and every judge call it made (what it cost).

### cutan.verify.critic.FAR_PLATE_CHECKLIST *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[Question](#cutan.verify.critic.Question), ...]* *= (Question(text='Does the picture show the ground or a road close to the viewer?', expected='no'), Question(text="Are there trees, poles, fences, signs or buildings near the viewer: large, or cut off by the picture's edges?", expected='no'), Question(text='Is everything shown far away: sky, horizon, distant hills or mountains?', expected='yes'))*

What a `far` plate of a travelling shot must not hold (ADR 0007 of `an`):
anything nearer than the far range stands still while the streams move.

### *class* cutan.verify.critic.Question(text, expected)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A yes/no question, and the answer a correct drawing gives.

### cutan.verify.critic.checklist_for(view, checklists={'\*': (Question(text='Does every sleeve or forearm touching the {prop} continue towards a shoulder of {character}, the person visible in the picture?', expected='yes'), Question(text="Do any forearms enter the picture from its bottom edge, as if they were the camera's own arms?", expected='no')), 'first_person': (Question(text="Do the forearms holding the {prop} enter the picture from its bottom edge, as if they were the camera's own arms?", expected='yes'), Question(text='Is the face of the person holding the {prop} visible in the picture?', expected='no')), 'front': (Question(text='Does every sleeve or forearm touching the {prop} continue towards a shoulder of {character}, the person visible in the picture?', expected='yes'), Question(text="Do any forearms enter the picture from its bottom edge, as if they were the camera's own arms?", expected='no'), Question(text="Are the hands on the {prop} seen from the same side as {character}'s face (both from the front)?", expected='yes'))})

The questions for a prop declared in `view`: a mapping’s entry for it
(else its `"*"`), or `checklists` itself when it is one list.

```pycon
>>> [q.expected for q in checklist_for("first_person")]
['yes', 'no']
>>> len(checklist_for("side"))
2
```

* **Return type:**
  [`Sequence`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[`Question`](#cutan.verify.critic.Question)]

### cutan.verify.critic.checklist_prompt(checklist, , prop, character)

The prompt asking `checklist` about `prop` held by `character`.

```pycon
>>> "1. Does every sleeve" in checklist_prompt(CHECKLISTS["front"], prop="wheel", character="ned")
True
```

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### cutan.verify.critic.critique_body_props(project, , judge=None, checklists={'\*': (Question(text='Does every sleeve or forearm touching the {prop} continue towards a shoulder of {character}, the person visible in the picture?', expected='yes'), Question(text="Do any forearms enter the picture from its bottom edge, as if they were the camera's own arms?", expected='no')), 'first_person': (Question(text="Do the forearms holding the {prop} enter the picture from its bottom edge, as if they were the camera's own arms?", expected='yes'), Question(text='Is the face of the person holding the {prop} visible in the picture?', expected='no')), 'front': (Question(text='Does every sleeve or forearm touching the {prop} continue towards a shoulder of {character}, the person visible in the picture?', expected='yes'), Question(text="Do any forearms enter the picture from its bottom edge, as if they were the camera's own arms?", expected='no'), Question(text="Are the hands on the {prop} seen from the same side as {character}'s face (both from the front)?", expected='yes'))}, at=(0.5,), frames=None, model=None)

Ask each body-depicting prop of `project`’s shots its view’s checklist.

project: a loaded `an.project.Project` or its folder
judge: `judge(frames, *, prompt)` returning the reply text, or an envelope

> with `reply` and `model` (default: `an`’s
> `judge_envelope()`, a paid call, with `model`)

checklists: questions by declared view ([`CHECKLISTS`](#cutan.verify.critic.CHECKLISTS)), or one list for all
at: the probe instants, as fractions of each shot’s length, in [0, 1]
frames: `frames(project, shot_id, times) -> [png bytes]` (default:

```default
:func:`an.probe.frames`, which needs the renderer's headless browser)
```

model: the default judge’s model; recorded with each call

A finding is `(severity, ir path, message)`: a `warning` per answer that
differs from a correct drawing’s, an `info` per `unsure`, an `error`
when the judge or the probe fails or the reply holds no answers. A prop
whose character is not in the shot is not asked (a first-person prop’s is
off screen by design, so it is).

* **Return type:**
  [`CritiqueReport`](#cutan.verify.critic.CritiqueReport)

### cutan.verify.critic.critique_far_plates(project, , judge=None, checklist=(Question(text='Does the picture show the ground or a road close to the viewer?', expected='no'), Question(text="Are there trees, poles, fences, signs or buildings near the viewer: large, or cut off by the picture's edges?", expected='no'), Question(text='Is everything shown far away: sky, horizon, distant hills or mountains?', expected='yes')), model=None, max_side=1024)

Ask whether each `far` plate of `project`’s travel holds anything near
(cutan#166): a tree baked into a plate stands still while the streams move.

The plate’s own image is judged, not a render: no probe, one call per plate
(at most `max_side` px long; a plane’s `fit` never crops, so the image
holds everything a pan could show). An SVG plate (drawn by hand, its content
known to its author) and a plane with no picture are not judged, each said
as an `info`. Only the plates a travel LISTS `far` are judged; a plane at
infinity because its frame is coupled `far` is not yet (cutan#177).
Findings and calls as [`critique_body_props()`](#cutan.verify.critic.critique_body_props).

* **Return type:**
  [`CritiqueReport`](#cutan.verify.critic.CritiqueReport)

### cutan.verify.critic.parse_answers(reply, checklist)

The answers in a judge’s reply, one per question (`answer` is `yes`,
`no` or `unsure`: read from its leading word); `None` when the reply
holds no answers at all.

```pycon
>>> parse_answers('{"answers": [{"n": 2, "answer": "yes, clearly"}]}', CHECKLISTS["front"])[1]
{'n': 2, 'answer': 'yes', 'why': ''}
>>> parse_answers("I cannot tell", CHECKLISTS["front"]) is None
True
```

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]] | [`None`](https://docs.python.org/3/builtins/constants.html#None)
