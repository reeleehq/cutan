---
name: cutan-physics
description: >-
  Make things move physically in a cut-out (an + cutan) scene: an item dropped or let go that must fall and land rather than float, an item tossed, a prop or a figurine knocked over (a camera on a tripod, a statue), a character tripping, a chain reaction where one body knocks the next, a point that must end on a target (a sword tip in an eye), gravity and timing that read as weight, a bounce or a settle, and the sound of a landing on its exact frame.
  Use whenever a scene or a review says "falls", "drops", "lets go", "floats", "hovers", "too slow", "no weight", "bounces", "tips over", "topples", "knocks over", "trips", "stumbles", "domino", "chain reaction", "physics", "gravity", or a sound "late" or "out of sync" with a landing or a hand-over.
  Routes to an's machinery (release, topple, solve gravity, joints, support, airborne, event cues) rather than restating it; the cutan-physicist subagent reviews a shot's physical motion or authors it for one beat.
metadata:
  audience: agents authoring or reviewing cut-out scenes
---

# cutan-physics — weight, falls and knocks in a cut-out scene

Physical motion is core (`an`): the same verbs move a musket, a crate or a crane's load. This skill is the cut-out author's map to them, plus what a character adds. Read the core references for the grammar; do not hand-tween what a verb does.

**Read first:** the `an` skill's `references/falls-and-topples.md` (drops, topples, chains, gravity scale, the refusals) and `references/holding-things.md` (grasp, place, release, swap; the ground; sounds on hold events). The `cutan` skill's *Holding things* names a character's hands (`stu@hand_r`).

## The one-line answers

| You want | Write | Not |
|---|---|---|
| gravity that reads as weight | `solve: {ground: <floor y>, gravity: down <9.8 × figure px / 1.7>, mode: pose}` (a 400 px figure: 2200) | the 980 default with big figures (slow motion, an#805); gravity without `mode: pose` (every limb starts to swing) |
| a hand lets go and the thing drops | `{kind: release, item: musket, at: 8.8}` (or `onto: ground@x` to land there), on a frame where the hand is still (the end of its tween), and the empty arm's next move a frame or two after it: a release takes the hand's velocity on its frame, so an arm that starts to drop at the let-go throws the item at the floor | an `arc:` (that is a throw up) or a `rotation:` (it spins in the air to reach it) unless you mean them |
| a character carries a cup, a mug, a box | the item `held_by: stu@hand_r` from the start (`held_rotation: 0.0` for upright) on an arm with an elbow (a carved one-stroke arm: `an character add-forearms`, cutan skill), the forearm bent across the front; keep upper + forearm rotation near the carrying pose's whenever the arm moves, since the item turns with the forearm | a straight hanging arm with the item at its end (it reads as floating in front of the body) |
| a deliberate drop of a long item | lift the arm first, fast and higher than the fall is long, and let go at the top: `{kind: tween, target: stu/arm_l, property: rotation, to: 1.8, duration: 0.2, start: 8.5}`, release at 8.7, lower it at 9.0 | releasing it while it hangs through the floor (`an validate` warns; it falls over its low end in front of the floor line); a slow lift (0.3 s, 1.4 rad) about as tall as the fall: it reads as a bob |
| a throw | swing the arm into it with `easing: ease_in` (the hand still moving at the let-go), then `{kind: release, item: musket, at: 31.6, onto: ground@-640}`; add `arc:` only for a throw *up* | a tween of the item's `y`; an eased-out swing (the hand stops, the item pops up off it); `arc: 60` on a toss down (it rises 60 px first: floating) |
| a prop knocked over | `{kind: topple, id: cam_falls, body: cam, toward: right, push: 1.3, start: 1.0}` | tweening its `rotation` about its middle (it pivots on its foot, accelerating) |
| one body knocks the next | `{kind: topple, body: nap, toward: right, after: cam_falls}` (starts at first contact) | a hand-timed second topple |
| a point ends on a target | add `point: 'sabre@0.03,0.02', until: 'han/head@0.7,0.6'` (or `world@x,y`) to the topple; quote `@u,v` | nudging rotations until it looks close |
| a character trips | a walk that ends at the obstacle, a short `rotation` tween forward and back on the character, and the obstacle's `topple` started at that instant with a `push` | a `topple` of the character (a rig is not rigid; cutan#203) |
| a sound on the landing / the hand-over | `{sound: thud, at: {when: musket, event: land}}`, `{sound: clink, at: {when: sabre, event: place}}`, a topple's `{when: nap, event: pin}`; once per clip `an sounds sync <project> <key>` | hand-typed seconds; a clip whose hit is 0.78 s in, cued by its first sample |
| a thrown thing you animate yourself | tween `y` with `ease_in` and declare `overrides: {airborne: {from, until}}` on it (the `gravity` check holds it to a parabola under a style pack's gravity) | `ease_in_out` on a fall (it decelerates into the floor: floating) |

## Timing that reads as weight (cut-out house rules)

- A fall accelerates all the way to the contact and stops dead: never ease *out* into a landing. The rigid fall gives this; for an authored fall use `ease_in`.
- After the hit: at most a small bounce or rock (`bounce`, 0.15 default; 0 for a heavy thud), then still. OverSimplified-style cut-out does not squash props; a character landing may dip a few px (`tween y` down 6-10 px over 0.06 s and back over 0.12 s), never stretch.
- A trip reads in three beats: the foot stops (one or two frames held), the body pitches (fast, 0.12-0.2 s), the recovery or the fall (slower). The obstacle starts moving on the pitch's first frame.
- Sound on the frame of the contact, never after it: event cues plus a declared sync point land within 10 ms (measured on a render).

## Checks to run

`an validate <dir> [--scene scene.<x>.md]`, then read these lines:

- `floating_item` (a taken item lay above or in the floor; a release with no ground or no gravity stays in the air; a let-go already through the floor line),
- `gravity` (an `airborne` entity hovers, moves straight, or does not fall at a steady rate),
- `support` / `skate` (a declared support floats or sinks; feet slide),
- `hold_conflict`, `unreachable_hold` (the holds do not add up; a hand cannot arrive: move the carrier as told),
- `cue_event` (a cue's event does not happen; else its second as `info`), `causality` (a sound ahead of or late on its named cause), the assembly line "hits N s into its file ... declares no sync point",
- a topple that cannot happen does not compile, and says the fix: the `push` needed, how close the knocker came, how far to move the body so its point meets the target.

Then look: `an probe <dir> --shot <id> --at <t> ...` at the release, the touch, the rest (the hold report's `events` give the seconds: `meta.extensions.solve.holds.events`, `meta.extensions.topple.events` in the compiled shot).

## Not supported yet

- Gravity derived from the scene's scale: an#805.
- A check that a carried item sinks through the floor while carried: an#806.
- Friction and sliding, a body coming to rest on another, several contacts, rolling: an#807.
- A character's trip, stumble and fall as a preset: cutan#203.
- Joints and dynamic follow-through (`solve: {gravity, damping}` with `mode: dynamic`, strings, hinges) exist (an's ADR 0008; the `cutan-style` skill's *marionette*), but a rigid prop falling while jointed to a character is not combined with `topple`.

## The subagent

`cutan-physicist` (shipped in `cutan/data/agents/`, linked into `~/.claude/agents/`): give it a scene file and a beat ("he drops the musket at the camera", "the camera falls on Napoleon"); it returns the actions and overrides to write and the checks to run, or, as a reviewer, ranked findings on a shot's physical motion. It reads and compiles; it does not edit the scene.
