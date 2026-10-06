# cutan.characters.methods

The cut-out genre’s methods and aspects, and their compile-time resolution (ADR 0002).

The first two aspects of ADR 0002’s first slice, as registry data:

| aspect     | method (spelled)                       | requires                           | chain      |
|------------|----------------------------------------|------------------------------------|------------|
| locomotion | `loco.legged_cycle` (`legs`)           | `limbs.legs`                       | 1st        |
| locomotion | `loco.profile_cycle` (`profile`)       | `limbs.legs`,<br/>`swap.view:side` | by request |
| locomotion | `loco.shuffle` (`shuffle`)             | `limbs.legs`                       | by request |
| locomotion | `loco.hem_sway` (`hem`)                | `limbs.legs`                       | by request |
| locomotion | `loco.waddle` (`waddle`)               | nothing                            | by request |
| locomotion | `loco.hop` (`hop`)                     | nothing                            | by request |
| locomotion | `loco.bounce` (`bounce`)               | nothing                            | by request |
| locomotion | `loco.rock` (`rock`)                   | nothing                            | by request |
| locomotion | `loco.glide` (`glide`)                 | nothing                            | last link  |
| speech     | `speech.mouth_chart` (`mouth_chart`)   | `face.mouth`                       | 1st        |
| speech     | `speech.pose_only` (`pulse`)           | nothing                            | last link  |
| expression | `expr.full_face` (`full_face`)         | `face.brows`                       | 1st        |
| expression | `expr.without_brows` (`without_brows`) | nothing                            | last link  |

**Locomotion: the gaits of an#224** (classified in
`misc/docs/locomotion_gaits.md`). A walk’s `gait` arg is the author’s
request, the descriptor’s `gait` a declared override (reported as such);
with neither, the chain picks `legs` when the character affords a leg pair
and `glide` when it does not (the rock, the last link before an#224, read as a
metronome on robe figures and is now a gait an author asks for). A requested
gait the rig cannot honour (`hem` on a legless blob, `profile` on a
character with no side view) is a **recorded substitution**: a warning, fatal
under `--strict-assets`, and `why_not` names what would enable it.

**Speech gains a requirement-free last link.** A character whose face is baked
into its art (`face_overlay: false`) used to speak with a frozen mouth; it now
pulses its head on each syllable ([`cutan.motion.speech_pulse()`](cutan.motion.html.md#cutan.motion.speech_pulse), parametrised:
`strength`, `part`, `attack`, `release`; `strength: 0` is a mime).

**Expression names what reads when the brows cannot** (an#252). A hat the
factory could not seat above the brows (recorded in `occluded`), or brow
slots without art, leave `face.brows` unafforded: the face then acts with
the lids, the gaze and the mouth form (`expr.without_brows`), recorded. Both
methods compile to the same face channels — the solver drives whatever the
rig binds — so the aspect is not consulted by the compiler; `an validate`
reports the fall ([`check_brow_acting()`](#cutan.characters.methods.check_brow_acting)) and `an character
capabilities` shows it with the remedy.

The asset profile the compiler resolves against is the character analyser’s
(`an.capabilities.affordances`), fed what the compiler actually has: the
descriptor and the art its store holds, or — for a rig drawn from `parts` or
the placeholder — the parts the builder built. Characters only: other entity
kinds have no analyser yet, and keep the preset’s own rig lookup.

Importing this module registers nothing: `cutan.genre.CUTOUT` lists
[`CUTOUT_METHODS`](#cutan.characters.methods.CUTOUT_METHODS) and [`CUTOUT_ASPECTS`](#cutan.characters.methods.CUTOUT_ASPECTS).

### Module Attributes

| [`LOCOMOTION`](#cutan.characters.methods.LOCOMOTION)         | The aspect names (persisted in substitution records).                                                                                                                                                                                         |
|---------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`SIDE_VIEW_IN_FORCE`](#cutan.characters.methods.SIDE_VIEW_IN_FORCE) | The requirement a `profile` walk has beyond the registry's `swap.view:side`: the side view must be the one SHOWING when the walk starts, or the legs swing in the front view and scissor (cutan#17).                                          |
| [`UNKNOWN_VIEW`](#cutan.characters.methods.UNKNOWN_VIEW)       | "The view in force is not known" — a caller that cannot read the timeline (the extent resolver, which never needs it: see [`walk_preset_context()`](#cutan.characters.methods.walk_preset_context)); the compiler and `an validate` always can. |
| [`CUTOUT_METHODS`](#cutan.characters.methods.CUTOUT_METHODS)     | The genre's methods, as vocabulary entries (kind `method`).                                                                                                                                                                                   |
| [`CUTOUT_ASPECTS`](#cutan.characters.methods.CUTOUT_ASPECTS)     | each chain ends in a method that requires nothing.                                                                                                                                                                                            |

### Functions

| [`brow_loss`](#cutan.characters.methods.brow_loss)(desc, profile, \*, entity)               | The expression aspect's fall to `expr.without_brows` for one character, as a `Resolution` carrying the `missing` substitution, or `None` when its brows can act.                                                                                                                                                                                                                                                                                   |
|-----------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`brow_moving_entities`](#cutan.characters.methods.brow_moving_entities)(shot)                         | `{entity: [IR paths]}`: the shot's expressions (an `expression` leaf, or a dialogue line's `[emotion]`) that move a character's brows, where each is written (`actions/<k>`, `dialogue/<j>/emotion`).                                                                                                                                                                                                                                              |
| [`check_brow_acting`](#cutan.characters.methods.check_brow_acting)(ctx)                             | The cut-out genre's semantic check: an expression that moves the brows of a character whose brows cannot act is reported (a warning) — the expression aspect's recorded fall to `expr.without_brows` (an#252), by the rule the compiler records it with ([`brow_loss()`](#cutan.characters.methods.brow_loss), an#283), the store's art probe included.                                                                                    |
| [`check_declared_speech`](#cutan.characters.methods.check_declared_speech)(ctx)                         | The cut-out genre's semantic check: each character's declared `speech` resolves.                                                                                                                                                                                                                                                                                                                                                                   |
| [`check_walk_gaits`](#cutan.characters.methods.check_walk_gaits)(ctx)                              | The cut-out genre's semantic check: a `walk` whose requested gait the entity cannot honour is reported (a warning, before any render), with the gait it will walk instead and what would make the asked one apply (an#224, ADR 0002 decision 6): a missing capability, the side view not in force for a `profile` (cutan#17), a legged gait asked of a prop with no legs (cutan#22) — and a gait parameter the walk's gait never reads (cutan#21). |
| [`gait_problem`](#cutan.characters.methods.gait_problem)(doc, \*, entity, args[, ...])         | Why a walk on `entity` will not use the gait it asks for (its `gait` arg, else the descriptor's), with what would enable it — or `None`.                                                                                                                                                                                                                                                                                                           |
| [`locomotion_args`](#cutan.characters.methods.locomotion_args)(entity, args, \*, descriptor, ...) | `(args with its gait resolved, resolution)` of a walk on `entity`: the locomotion method the registry resolves (an#248) — the author's `gait` (a spelling, a method id or a pinned choice, spelled out first, its args joining the walk's), else the descriptor's, else the chain.                                                                                                                                                                 |
| [`off_registry_substitution`](#cutan.characters.methods.off_registry_substitution)(entity, args[, parts])   | The record for a legged gait asked of an entity that does not resolve on the capability registry (a prop: no analyser) and whose built `parts` hold no leg pair ([`cutan.motion.WALK_LEG_NAMES`](cutan.motion.html.md#cutan.motion.WALK_LEG_NAMES)): it walks the legless default, and says so (cutan#22).                                                                                                                  |
| [`substitution_problem`](#cutan.characters.methods.substitution_problem)(sub)                          | The sentence `an validate` reports for a `missing` substitution: what happened, plus each missing capability's remedy (the substitution's own where it carries one, else the registry's).                                                                                                                                                                                                                                                          |
| [`walk_arg_problems`](#cutan.characters.methods.walk_arg_problems)(gait, args)                      | The gait parameters in `args` that `gait` never reads (cutan#21): each is a silent no-op otherwise.                                                                                                                                                                                                                                                                                                                                                |
| [`walk_problems`](#cutan.characters.methods.walk_problems)(doc, \*, entity, args[, ...])        | Everything `an validate` says about one `walk` on a character, each a warning: the gait it asks for will not be used ([`gait_problem()`](#cutan.characters.methods.gait_problem)), and a gait parameter the gait it WILL use never reads (cutan#21) — when the gait is the descriptor's or the chain's; an explicit gait's (a spelling, a method id or a pinned choice) unread parameter is `play_problems`' error.                           |
| [`walk_own_args`](#cutan.characters.methods.walk_own_args)()                                    | The walk's own arguments — where to, how many steps, the limbs, the view — read off its signature: everything it accepts that is not a gait parameter (`cutan.motion.WALK_PARAM_DEFAULTS`), which only the gaits that declare it read (cutan#21).                                                                                                                                                                                                  |
| [`compile_profile`](#cutan.characters.methods.compile_profile)(descriptor, \*[, ...])             | The character's profile, from what the compiler has: the analyser, fed honestly.                                                                                                                                                                                                                                                                                                                                                                   |
| [`speech_problems`](#cutan.characters.methods.speech_problems)(declared)                          | Why a character's declared `speech` cannot be honoured (empty: it can).                                                                                                                                                                                                                                                                                                                                                                            |
| [`normalise_gait_args`](#cutan.characters.methods.normalise_gait_args)(args)                          | A walk's args with `gait` as the walk spells it (one of [`cutan.motion.GAITS`](cutan.motion.html.md#cutan.motion.GAITS)).                                                                                                                                                                                                                                                                                                   |
| [`resolve_walk_gait`](#cutan.characters.methods.resolve_walk_gait)(entity, \*, args, ...[, ...])    | `(gait, resolution)` of a walk on `entity`: the locomotion method's spelling.                                                                                                                                                                                                                                                                                                                                                                      |
| [`speech_plan`](#cutan.characters.methods.speech_plan)(shot, \*, is_character, profile_of)    | Resolve the speech aspect ONCE per speaking character, and say what it adds.                                                                                                                                                                                                                                                                                                                                                                       |
| [`substitution_record`](#cutan.characters.methods.substitution_record)(sub, \*[, entity_ref])         | A `Substitution` as an `asset_resolution` entry.                                                                                                                                                                                                                                                                                                                                                                                                   |
| [`syllable_beats`](#cutan.characters.methods.syllable_beats)(line, \*[, min_gap_s])              | Syllable onsets of a dialogue line, in seconds from its start.                                                                                                                                                                                                                                                                                                                                                                                     |
| [`walk_preset_context`](#cutan.characters.methods.walk_preset_context)(entity, args, \*, ...[, ...])  | What the compiler adds to a `walk` play's args before expanding it, as far as the walk's LENGTH depends on it: the resolved `gait` (when the entity resolves on the registry: `profile` given), the figure's drawn `scale` (its stage scale, cutan#13), and — off the registry, where the walk picks its own gait from the limbs it finds — the built `parts`.                                                                                     |

### Classes

| [`SpeechPlan`](#cutan.characters.methods.SpeechPlan)([actions, no_lip_sync])   | What the speech aspect decided for a shot: the actions it adds, and the speakers whose lip-sync it switched off (the viseme pass skips them).   |
|---------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------|

### cutan.characters.methods.CUTOUT_ASPECTS *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[Aspect, ...]* *= (Aspect(name='locomotion', chain=('loco.legged_cycle', 'loco.glide'), applies_to=frozenset(), description='how a character travels when it walks.', declared_by='gait', records_fallback=False), Aspect(name='speech', chain=('speech.mouth_chart', 'speech.pose_only'), applies_to=frozenset(), description='how a character shows that it is speaking.', declared_by='speech', records_fallback=True), Aspect(name='expression', chain=('expr.full_face', 'expr.without_brows'), applies_to=frozenset({'character'}), description="how a character's face shows an emotion.", declared_by='', records_fallback=True))*

each chain ends in a method that requires nothing.

* **Type:**
  The genre’s aspects

### cutan.characters.methods.CUTOUT_METHODS *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[Method, ...]* *= (Method(id='loco.legged_cycle', kind='method', version='2', name='legs', title='legged walk cycle', description='a legged walk cycle: in profile the legs swing about the hip in opposition, facing the camera the stepping leg lifts; the arms swing against the legs', usage='', params={'type': 'object', 'properties': {'step_s': {'type': 'number', 'default': 0.4}, 'step_length': {'type': 'number', 'default': 80.0, 'description': 'scene px at drawn scale 1; scales with the figure'}, 'stride': {'type': 'number', 'default': 0.35}, 'lift': {'type': 'number', 'default': 10.0}, 'arm_swing': {'type': 'number', 'default': 0.3}, 'bob': {'type': 'number', 'default': 6.0, 'description': 'scene px at drawn scale 1; scales with the figure'}}}, examples=({'kind': 'play', 'target': 'ned', 'animation': 'walk', 'args': {'gait': 'legs'}},), requires=(Requirement(capability='limbs.legs', key=None, at_least=None, any_of=()),), levels=frozenset({'b-name', 'a'}), aspects=(), aspect='locomotion', remedies={'limbs.legs': 'split the legs into two slots named leg_l/leg_r, each with its art, pivoted at the hip (an-art-package skill; \`an character new\` builds them)'}), Method(id='loco.profile_cycle', kind='method', version='2', name='profile', title='profile walk cycle', description="the four poses of a walk seen in profile (contact, down, passing, up): with a side or three-quarter view showing the legs swing about the hip in opposition and the body sinks after each contact and rises before the next; asked while another view shows, it walks as legs (Reiniger's silhouettes, any figure drawn side-on)", usage='', params={'type': 'object', 'properties': {'step_s': {'type': 'number', 'default': 0.4}, 'step_length': {'type': 'number', 'default': 80.0, 'description': 'scene px at drawn scale 1; scales with the figure'}, 'stride': {'type': 'number', 'default': 0.45}, 'bob': {'type': 'number', 'default': 6.0, 'description': 'scene px at drawn scale 1; scales with the figure'}, 'arm_swing': {'type': 'number', 'default': 0.35}}}, examples=({'kind': 'play', 'target': 'ned', 'animation': 'walk', 'args': {'gait': 'profile'}},), requires=(Requirement(capability='limbs.legs', key=None, at_least=None, any_of=()), Requirement(capability='swap.view', key='side', at_least=None, any_of=())), levels=frozenset({'b-name', 'a'}), aspects=(), aspect='locomotion', remedies={'limbs.legs': 'split the legs into two slots named leg_l/leg_r, each with its art, pivoted at the hip (an-art-package skill; \`an character new\` builds them)', 'swap.view:side': 'give the character a side view: \`an character add-views <name>\` (a factory character), or carve its art in profile and declare \`rest_view: side\` in character.json'}), Method(id='loco.shuffle', kind='method', version='2', name='shuffle', title='shuffle', description='the feet barely leave the ground: short, quick steps with little bob and arms close to the body (the old, the tired, the cautious)', usage='', params={'type': 'object', 'properties': {'step_s': {'type': 'number', 'default': 0.3}, 'step_length': {'type': 'number', 'default': 40.0, 'description': 'scene px at drawn scale 1; scales with the figure'}, 'stride': {'type': 'number', 'default': 0.12}, 'lift': {'type': 'number', 'default': 3.0}, 'arm_swing': {'type': 'number', 'default': 0.1}, 'bob': {'type': 'number', 'default': 1.0, 'description': 'scene px at drawn scale 1; scales with the figure'}}}, examples=({'kind': 'play', 'target': 'ned', 'animation': 'walk', 'args': {'gait': 'shuffle'}},), requires=(Requirement(capability='limbs.legs', key=None, at_least=None, any_of=()),), levels=frozenset({'b-name', 'a'}), aspects=(), aspect='locomotion', remedies={'limbs.legs': 'split the legs into two slots named leg_l/leg_r, each with its art, pivoted at the hip (an-art-package skill; \`an character new\` builds them)'}), Method(id='loco.hem_sway', kind='method', version='2', name='hem', title='hem sway', description="a robe figure's walk: the leg slots are the two halves of the hem, which tilt about the hip as mirror images (the hem opens and closes) while the body sways and bobs facing the camera; in profile they swing like legs", usage='', params={'type': 'object', 'properties': {'step_s': {'type': 'number', 'default': 0.4}, 'step_length': {'type': 'number', 'default': 80.0, 'description': 'scene px at drawn scale 1; scales with the figure'}, 'hem_tilt': {'type': 'number', 'default': 0.24}, 'rock': {'type': 'number', 'default': 0.06}, 'bob': {'type': 'number', 'default': 6.0, 'description': 'scene px at drawn scale 1; scales with the figure'}, 'stride': {'type': 'number', 'default': 0.35}, 'arm_swing': {'type': 'number', 'default': 0.3}}}, examples=({'kind': 'play', 'target': 'ned', 'animation': 'walk', 'args': {'gait': 'hem'}},), requires=(Requirement(capability='limbs.legs', key=None, at_least=None, any_of=()),), levels=frozenset({'b-name', 'a'}), aspects=(), aspect='locomotion', remedies={'limbs.legs': "carve the robe's hem into two halves on slots leg_l/leg_r, pivoted at the hip, and declare \`gait: hem\` in character.json"}), Method(id='loco.waddle', kind='method', version='2', name='waddle', title='waddle', description='the body rocks from foot to foot and bobs on each step; legs, if any, lift in turn (a penguin, a toddler, a squat figure)', usage='', params={'type': 'object', 'properties': {'step_s': {'type': 'number', 'default': 0.4}, 'step_length': {'type': 'number', 'default': 80.0, 'description': 'scene px at drawn scale 1; scales with the figure'}, 'rock': {'type': 'number', 'default': 0.12}, 'lift': {'type': 'number', 'default': 5.0}, 'bob': {'type': 'number', 'default': 4.0, 'description': 'scene px at drawn scale 1; scales with the figure'}, 'arm_swing': {'type': 'number', 'default': 0.15}}}, examples=({'kind': 'play', 'target': 'ned', 'animation': 'walk', 'args': {'gait': 'waddle'}},), requires=(), levels=frozenset({'b-name', 'a'}), aspects=(), aspect='locomotion', remedies={}), Method(id='loco.hop', kind='method', version='2', name='hop', title='hop', description='the whole figure jumps on every step while it travels (a bird, a kangaroo, a gleeful character, anything drawable)', usage='', params={'type': 'object', 'properties': {'step_s': {'type': 'number', 'default': 0.4}, 'step_length': {'type': 'number', 'default': 80.0, 'description': 'scene px at drawn scale 1; scales with the figure'}, 'hop_height': {'type': 'number', 'default': 18.0, 'description': 'scene px at drawn scale 1; scales with the figure'}, 'arm_swing': {'type': 'number', 'default': 0.0}}}, examples=({'kind': 'play', 'target': 'ned', 'animation': 'walk', 'args': {'gait': 'hop'}},), requires=(), levels=frozenset({'b-name', 'a'}), aspects=(), aspect='locomotion', remedies={}), Method(id='loco.bounce', kind='method', version='2', name='bounce', title='bounce', description='the body bobs on every step while it slides; legs, if any, only flick (the South Park walk)', usage='', params={'type': 'object', 'properties': {'step_s': {'type': 'number', 'default': 0.4}, 'step_length': {'type': 'number', 'default': 80.0, 'description': 'scene px at drawn scale 1; scales with the figure'}, 'bob': {'type': 'number', 'default': 8.0, 'description': 'scene px at drawn scale 1; scales with the figure'}, 'lift': {'type': 'number', 'default': 4.0}, 'stride': {'type': 'number', 'default': 0.1}, 'arm_swing': {'type': 'number', 'default': 0.15}}}, examples=({'kind': 'play', 'target': 'ned', 'animation': 'walk', 'args': {'gait': 'bounce'}},), requires=(), levels=frozenset({'b-name', 'a'}), aspects=(), aspect='locomotion', remedies={}), Method(id='loco.rock', kind='method', version='2', name='rock', title='rock and bob', description='no leg moves: the body rocks side to side and bobs once per step while it travels (a blob, a sack, anything drawable)', usage='', params={'type': 'object', 'properties': {'step_s': {'type': 'number', 'default': 0.4}, 'step_length': {'type': 'number', 'default': 80.0, 'description': 'scene px at drawn scale 1; scales with the figure'}, 'rock': {'type': 'number', 'default': 0.06}, 'bob': {'type': 'number', 'default': 6.0, 'description': 'scene px at drawn scale 1; scales with the figure'}, 'arm_swing': {'type': 'number', 'default': 0.3}}}, examples=({'kind': 'play', 'target': 'ned', 'animation': 'walk', 'args': {'gait': 'rock'}},), requires=(), levels=frozenset({'b-name', 'a'}), aspects=(), aspect='locomotion', remedies={}), Method(id='loco.glide', kind='method', version='2', name='glide', title='glide', description='the figure slides, leaning into the move with a gentle bob; no limb moves (a robe figure, a ghost, a sack — the default for any figure without legs)', usage='', params={'type': 'object', 'properties': {'step_s': {'type': 'number', 'default': 0.4}, 'step_length': {'type': 'number', 'default': 80.0, 'description': 'scene px at drawn scale 1; scales with the figure'}, 'bob': {'type': 'number', 'default': 1.5, 'description': 'scene px at drawn scale 1; scales with the figure'}, 'lean': {'type': 'number', 'default': 0.04}, 'arm_swing': {'type': 'number', 'default': 0.0}}}, examples=({'kind': 'play', 'target': 'ned', 'animation': 'walk', 'args': {'gait': 'glide'}},), requires=(), levels=frozenset({'b-name', 'a'}), aspects=(), aspect='locomotion', remedies={}), Method(id='speech.mouth_chart', kind='method', version='1', name='mouth_chart', title='mouth chart lip-sync', description="lip-sync on the character's mouth chart: the line's visemes swap the mouth drawings (the nine Rhubarb shapes, or the character's own set)", usage='', params={}, examples=(), requires=(Requirement(capability='face.mouth', key=None, at_least=None, any_of=()),), levels=frozenset({'b-name', 'a'}), aspects=(), aspect='speech', remedies={'face.mouth': "give the character an overlay mouth: a \`mouth\` slot with the viseme set's drawings (\`an character mouths <dir>\`) and face_overlay: true"}), Method(id='speech.pose_only', kind='method', version='1', name='pulse', title='speech pulse', description='no lip-sync: the head (or the body) pulses on each syllable, so a baked face or a mime still reads as speaking', usage='', params={'type': 'object', 'properties': {'strength': {'type': 'number', 'default': 0.06}, 'part': {'type': 'string', 'default': 'head'}, 'attack': {'type': 'number', 'default': 0.06}, 'release': {'type': 'number', 'default': 0.1}}}, examples=('a character with face_overlay: false speaks',), requires=(), levels=frozenset({'b-name', 'a'}), aspects=(), aspect='speech', remedies={}), Method(id='expr.full_face', kind='method', version='1', name='full_face', title='full-face expression', description="the expression acts with the whole face: the brows rise, knit and tilt, the lids open and close, the pupils move and the mouth takes the preset's form", usage='', params={}, examples=({'kind': 'expression', 'target': 'ned', 'preset': 'surprised'},), requires=(Requirement(capability='face.brows', key=None, at_least=None, any_of=()),), levels=frozenset({'b-name', 'a'}), aspects=(), aspect='expression', remedies={'face.brows': "keep the brows clear: \`an character new\` seats a hat above them at most head scales — at this one it could not, so use a larger --head-scale, another --hat or --hat none; for drawn art, redraw what covers the brows and remove the descriptor's \`occluded\` entry, or give the face brow slots (left_brow/right_brow) with art"}), Method(id='expr.without_brows', kind='method', version='1', name='without_brows', title='expression without brows', description='the brows cannot be seen acting (covered, or not drawn): the lids, the gaze and the mouth form carry the expression', usage='', params={}, examples=('a character whose hat covers its brows takes [surprised]',), requires=(), levels=frozenset({'b-name', 'a'}), aspects=(), aspect='expression', remedies={}))*

The genre’s methods, as vocabulary entries (kind `method`).

### cutan.characters.methods.LOCOMOTION *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'locomotion'*

The aspect names (persisted in substitution records).

### cutan.characters.methods.SIDE_VIEW_IN_FORCE *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'swap.view:side in force'*

The requirement a `profile` walk has beyond the registry’s
`swap.view:side`: the side view must be the one SHOWING when the walk
starts, or the legs swing in the front view and scissor (cutan#17).

### *class* cutan.characters.methods.SpeechPlan(actions=(), no_lip_sync=frozenset({}))

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

What the speech aspect decided for a shot: the actions it adds, and the
speakers whose lip-sync it switched off (the viseme pass skips them).

### cutan.characters.methods.UNKNOWN_VIEW *: [Any](https://docs.python.org/3/library/typing.html#typing.Any)* *= <object object>*

“The view in force is not known” — a caller that cannot read the timeline
(the extent resolver, which never needs it: see [`walk_preset_context()`](#cutan.characters.methods.walk_preset_context));
the compiler and `an validate` always can. A private object, so no view an
author could type (`view: "?"`) stands for it.

### cutan.characters.methods.brow_loss(desc, profile, , entity)

The expression aspect’s fall to `expr.without_brows` for one character,
as a `Resolution` carrying the `missing`
substitution, or `None` when its brows can act.

THE rule for who records it (an#283), shared by the compiler (the record
`--strict-assets` refuses), `an validate` and `brow_acting_problem()`:
only a character that HAS brows to lose — an overlay face whose binding
moves brow slots — and cannot act with them (covered, or their art
missing). A baked face (`face_overlay: false`, a DiceBear head), a
descriptor with no brow slots, or a procedural rig (no descriptor) has
nothing to lose and records nothing. `profile` is the analyser’s answer
for what compiled ([`compile_profile()`](#cutan.characters.methods.compile_profile), with the store’s art probe).

### cutan.characters.methods.brow_moving_entities(shot)

`{entity: [IR paths]}`: the shot’s expressions (an `expression` leaf,
or a dialogue line’s `[emotion]`) that move a character’s brows, where
each is written (`actions/<k>`, `dialogue/<j>/emotion`).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]]

### cutan.characters.methods.check_brow_acting(ctx)

The cut-out genre’s semantic check: an expression that moves the brows of
a character whose brows cannot act is reported (a warning) — the expression
aspect’s recorded fall to `expr.without_brows` (an#252), by the rule the
compiler records it with ([`brow_loss()`](#cutan.characters.methods.brow_loss), an#283), the store’s art probe
included.

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### cutan.characters.methods.check_declared_speech(ctx)

The cut-out genre’s semantic check: each character’s declared `speech` resolves.

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### cutan.characters.methods.check_walk_gaits(ctx)

The cut-out genre’s semantic check: a `walk` whose requested gait the
entity cannot honour is reported (a warning, before any render), with the
gait it will walk instead and what would make the asked one apply (an#224,
ADR 0002 decision 6): a missing capability, the side view not in force
for a `profile` (cutan#17), a legged gait asked of a prop with no legs
(cutan#22) — and a gait parameter the walk’s gait never reads (cutan#21).
The view in force is read off the timeline the way the compiler reads it
(`cutan.characters.checks._turns_of()`), a prop’s limbs off the built
stage (`cutan.characters.checks._stage_poses_of()`).

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### cutan.characters.methods.compile_profile(descriptor, , built_parts=(), art_exists=None)

The character’s profile, from what the compiler has: the analyser, fed honestly.

`descriptor` is the migrated `CharacterDescriptor` (or `None` for a
rig drawn from `parts` / the placeholder); `art_exists(rel_path)` the
store’s probe (`None`: the store cannot say, so every declared drawing
counts — the rig builder’s own rule); `built_parts` the part names the
builder built under the entity (for a non-descriptor rig, they ARE its
parts document).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]]

### cutan.characters.methods.gait_problem(doc, \*, entity, args, art_exists=None, view=<object object>, policy=None)

Why a walk on `entity` will not use the gait it asks for (its `gait`
arg, else the descriptor’s), with what would enable it — or `None`.

`doc` is the character’s stored document; `art_exists` the store’s
probe; `view` the view in force at the play’s start (cutan#17);
`policy` the scene’s, as the compiler resolves under it. The
sentence is the one the compiler records (`asset_resolution`) when it
substitutes the method, plus each missing capability’s remedy.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### cutan.characters.methods.locomotion_args(entity, args, \*, descriptor, profile, policy=None, view=<object object>, on_skip=None)

`(args with its gait resolved, resolution)` of a walk on `entity`:
the locomotion method the registry resolves (an#248) — the author’s
`gait` (a spelling, a method id or a pinned choice, spelled out first,
its args joining the walk’s), else the descriptor’s, else the chain.

ONE function for the compiler’s expansion and for the walk’s EXTENT (what a
`sequence` waits for, [`walk_preset_context()`](#cutan.characters.methods.walk_preset_context)), so the two cannot
disagree about which gait runs (cutan#12).

`policy` is the scene’s (cutan#9: the shot’s over the style’s, which the
compiler’s policy pass leaves in its products, an#348); it orders the
methods when nothing is requested (its entries that do not apply go to
`on_skip`), and the chosen entry’s OWN args join the walk’s under them
(never the method’s defaults, which the gait scales to the figure).

* **Return type:**
  [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)], [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

```pycon
>>> args, r = locomotion_args("blob", {"gait": "hem", "distance": 80}, descriptor=None, profile={})
>>> args["gait"], r.substitution.reason
('glide', 'missing')
```

### cutan.characters.methods.normalise_gait_args(args)

A walk’s args with `gait` as the walk spells it (one of [`cutan.motion.GAITS`](cutan.motion.html.md#cutan.motion.GAITS)).

`gait` may name a locomotion method by id (`loco.rock`) or be a choice
`{method, args, version}` — the level-(a) form, and how a scene pins a
method’s version (ADR 0003 decision 2). The choice’s `args` join the
walk’s (an explicit arg wins); a pin that no longer holds, or a method of
another aspect, raises `VocabularyError`.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

```pycon
>>> normalise_gait_args({"gait": {"method": "loco.legged_cycle", "args": {"stride": 0.5}, "version": "2"}})
{'stride': 0.5, 'gait': 'legs'}
>>> normalise_gait_args({"gait": "hem", "distance": 80})
{'gait': 'hem', 'distance': 80}
```

### cutan.characters.methods.off_registry_substitution(entity, args, parts=None)

The record for a legged gait asked of an entity that does not resolve
on the capability registry (a prop: no analyser) and whose built
`parts` hold no leg pair ([`cutan.motion.WALK_LEG_NAMES`](cutan.motion.html.md#cutan.motion.WALK_LEG_NAMES)): it walks
the legless default, and says so (cutan#22). `None` otherwise — a prop
rigged with legs walks on them.

```pycon
>>> off_registry_substitution("lamp", {"gait": "hem"}, ["base", "shade"]).sentence()
"lamp: locomotion 'loco.hem_sway' does not apply (missing limbs.legs); used 'loco.glide'"
>>> off_registry_substitution("lamp", {"gait": "hop"}, []) is None
True
>>> off_registry_substitution("bot", {"gait": "legs"}, ["leg_l", "leg_r"]) is None
True
```

### cutan.characters.methods.resolve_walk_gait(entity, \*, args, descriptor, profile, policy=None, view=<object object>, on_skip=None)

`(gait, resolution)` of a walk on `entity`: the locomotion method’s spelling.

`policy` (the shot’s over the style’s) orders the methods when nothing
is requested; its entries that do not apply are reported to `on_skip`.

The request is the walk’s `gait` arg, else the descriptor’s declared
`gait` (an override of the derivation, and reported as one). An explicit
`legs` arg names the limbs itself: a non-empty pair affords legs whatever
the derivation says, `()` affords none. `view` is the view the
TIMELINE has in force at the play’s start (`None`: the rig’s default
drawing; never the walk’s own `view` arg, which poses the legs without
swapping the art): a `profile` while a view its legs do not swing in is
showing would scissor them in front, so the side view is taken off the
profile for this resolution — the registry then substitutes as it would
for a missing capability (the chain, or a policy’s next choice), and the
record names [`SIDE_VIEW_IN_FORCE`](#cutan.characters.methods.SIDE_VIEW_IN_FORCE) with its remedy (cutan#17).
[`UNKNOWN_VIEW`](#cutan.characters.methods.UNKNOWN_VIEW) skips that (a caller with no timeline).

```pycon
>>> gait, r = resolve_walk_gait("blob", args={"gait": "hem"}, descriptor=None, profile={})
>>> gait, r.substitution.reason, r.substitution.missing
('glide', 'missing', ('limbs.legs',))
>>> legged = {"limbs.legs": {"slots": ["leg_l", "leg_r"]},
...           "swap.view": {"keys": ["front", "side"], "rest": "front"}}
>>> gait, r = resolve_walk_gait("ned", args={"gait": "profile"}, descriptor=None, profile=legged, view=None)
>>> gait, r.substitution.missing
('legs', ('swap.view:side in force',))
>>> resolve_walk_gait("ned", args={"gait": "profile"}, descriptor=None, profile=legged, view="side")[0]
'profile'
```

### cutan.characters.methods.speech_plan(shot, \*, is_character, profile_of, descriptor_of=<function <lambda>>, has_part, record=None, policy=None, record_skip=None)

Resolve the speech aspect ONCE per speaking character, and say what it adds.

The request is the character’s declared `speech` (a method spelling or a
`{method, args, version}` choice); `policy` is the shot/style policy.
The one resolution decides both halves: a speaker resolved to anything but
`speech.mouth_chart` gets no viseme channel (`SpeechPlan.no_lip_sync`),
and one resolved to `speech.pose_only` gets a `speech_pulse` play at each
syllable onset of each timed line — one play per syllable, each built at the
head’s pose at that instant, so it rides an authored head-scale tween rather
than overwriting it; a syllable that starts while the speaker’s previous pulse
is still running is skipped, so the head always settles back. `strength: 0`
is a mime: no pulse at all. An authored `play: speech_pulse` on the speaker
replaces the automatic pulses (nothing is added beside it), but it is not a
declaration: the fall from the mouth chart is still recorded, and only a
declared `speech` makes it the request. Substitutions (a declared method
the rig cannot honour; the fall from the mouth chart to the pulse) go to
`record`, once per speaker. A declared `speech` naming no method of the
aspect, or pinned to a stale version, raises
`VocabularyError` naming the aspect’s methods
([`speech_problems()`](#cutan.characters.methods.speech_problems) is `an validate`’s side of it).

* **Return type:**
  [`SpeechPlan`](#cutan.characters.methods.SpeechPlan)

### cutan.characters.methods.speech_problems(declared)

Why a character’s declared `speech` cannot be honoured (empty: it can).

An unknown method, a method of another aspect, or a pin to a version the
registry no longer has; the message names the speech methods.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

```pycon
>>> speech_problems("pulse"), speech_problems(None)
([], [])
>>> speech_problems("flap")[0].startswith("speech 'flap'")
True
```

### cutan.characters.methods.substitution_problem(sub)

The sentence `an validate` reports for a `missing` substitution: what
happened, plus each missing capability’s remedy (the substitution’s own
where it carries one, else the registry’s). `None` for no substitution
or a non-fatal one.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### cutan.characters.methods.substitution_record(sub, , entity_ref=None)

A `Substitution` as an `asset_resolution` entry.

The compiled document’s record generalised (ADR 0002 decision 6):
`kind: method`, `store` the aspect, `ref` what was asked for,
`resolved` what was used, `fallback` whether `--strict-assets` makes
it fatal.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### cutan.characters.methods.syllable_beats(line, , min_gap_s=0.18)

Syllable onsets of a dialogue line, in seconds from its start.

The line’s word timings, when its provider has them, are the authority:
they are measured on the audio, so a beat never falls in a leading breath
or a pause (an#272: a pulse dipped 0.35 s before “Hi” was heard). Each
word starts a beat, and the viseme track’s syllables (where the mouth
opens out of a closed shape) add beats INSIDE a word’s window, never
outside every word. With no word timings: the viseme track’s syllables,
else one beat at the line’s start. Beats closer than `min_gap_s` merge.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`float`](https://docs.python.org/3/builtins/functions.html#float)]

```pycon
>>> from types import SimpleNamespace as NS
>>> track = NS(keyframes=[NS(time=0.0, viseme="B"), NS(time=0.4, viseme="X"),
...                       NS(time=0.7, viseme="C")])
>>> syllable_beats(NS(viseme_track=track, word_timings=None, duration=1.2))
[0.0, 0.7]
>>> words = [NS(start=0.35, end=1.0)]  # a breath before the word
>>> syllable_beats(NS(viseme_track=track, word_timings=words, duration=1.2))
[0.35, 0.7]
```

### cutan.characters.methods.walk_arg_problems(gait, args)

The gait parameters in `args` that `gait` never reads (cutan#21):
each is a silent no-op otherwise. `gait` is a spelling (one of
[`cutan.motion.GAITS`](cutan.motion.html.md#cutan.motion.GAITS)); the walk’s own arguments
([`walk_own_args()`](#cutan.characters.methods.walk_own_args)) are never a problem. An unknown spelling is the
walk’s own to refuse.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

```pycon
>>> walk_arg_problems("hop", {"bob": 20, "distance": 80, "arm_swing": 0.2})
["gait 'hop' does not read 'bob' (it reads: arm_swing, hop_height, step_length, step_s)"]
>>> walk_arg_problems("glide", {"bob": 2}), walk_arg_problems("noop", {"bob": 2})
([], [])
```

### cutan.characters.methods.walk_own_args()

The walk’s own arguments — where to, how many steps, the limbs, the view
— read off its signature: everything it accepts that is not a gait
parameter (`cutan.motion.WALK_PARAM_DEFAULTS`), which only the gaits
that declare it read (cutan#21).

* **Return type:**
  [`frozenset`](https://docs.python.org/3/builtins/stdtypes.html#frozenset)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

```pycon
>>> sorted(walk_own_args())
['arms', 'direction', 'distance', 'gait', 'legs', 'steps', 'to_x', 'view']
```

### cutan.characters.methods.walk_preset_context(entity, args, , descriptor, profile, scale, parts=None, policy=None)

What the compiler adds to a `walk` play’s args before expanding it, as
far as the walk’s LENGTH depends on it: the resolved `gait` (when the
entity resolves on the registry: `profile` given), the figure’s drawn
`scale` (its stage scale, cutan#13), and — off the registry, where the
walk picks its own gait from the limbs it finds — the built `parts`. The
extent resolver reads this so a `sequence` waits exactly as long as the
walk runs (cutan#12); the expansion itself resolves the same way (and
records the substitution). The one thing the extent does not see is the
view in force (cutan#17): a `profile` it resolves may walk as `legs`,
which is why those two share `step_s` and `step_length`
(`tests/test_gaits.py` pins that).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

```pycon
>>> walk_preset_context("b", {"gait": "shuffle"}, descriptor=None, profile={}, scale=2.0)
{'scale': 2.0, 'gait': 'glide'}
>>> walk_preset_context("b", {"gait": "shuffle"}, descriptor=None, profile=None, scale=1.0)
{'scale': 1.0}
>>> walk_preset_context("b", {}, descriptor=None, profile=None, scale=1.0, parts=["head"])
{'scale': 1.0, 'parts': {'head': {}}}
```

### cutan.characters.methods.walk_problems(doc, \*, entity, args, art_exists=None, view=<object object>, policy=None)

Everything `an validate` says about one `walk` on a character, each a
warning: the gait it asks for will not be used ([`gait_problem()`](#cutan.characters.methods.gait_problem)), and
a gait parameter the gait it WILL use never reads (cutan#21) — when the
gait is the descriptor’s or the chain’s; an explicit gait’s (a spelling,
a method id or a pinned choice) unread parameter is `play_problems`’ error.
`doc` is the character’s stored document: a `CharacterDescriptor`, or
a `parts` rig (resolved on its parts, as the compiler does); anything
else is `cutout.play`’s to report.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]
