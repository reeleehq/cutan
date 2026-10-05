# Locomotion gaits: a classification for cut-out walks

The research step of an#224 (P10 of the an#231 plan), kept lean. It classifies how 2D and cut-out animation moves a character from place to place, says what each gait **requires** of a rig (ADR 0002: capability-based applicability, with defaults), and fixes the parameters, their defaults and the default chain that `cutan.motion.walk` and the locomotion methods in `cutan.characters.methods` implement.

Scope and honesty: this pass reads the production literature and the styles' own conventions; it did **not** measure footage frame by frame. The timing defaults keep the values the pre-an#224 walk already rendered with (a step every 0.4 s, close to Williams' "on 12s" at 30 fps), so no existing render moves. Measuring South Park, OverSimplified, Reiniger and Norstein footage to tune each gait is left open (see *Open*).

## 1. The legged walk and its four poses

The walk cycle of drawn animation is built from four key poses per step [1, 2, 3]:

- **Contact**: both feet on the ground, legs at their widest; the body at middle height.
- **Down**: just after contact, the front leg takes the weight and bends; the body is at its **lowest**.
- **Passing**: the back leg passes the standing one; the body rises.
- **Up**: the standing leg pushes off; the body is at its **highest**, just before the next contact.

The body therefore bobs **once per step**, low after contact and high before the next. The arms swing against the legs (left arm forward with the right leg). Timing sets character: a step on 8 frames is brisk, 12 a natural walk, 16 a stroll, 20 or more old or tired [1, 3].

A cut-out rig realises this with legs as separate parts pivoted at the hip, and, in better rigs, a knee pivot and replacement feet (drawing substitution) for the heel strike and the push-off [4, 5]. `cutan`'s rig contract has the hip pivots (`leg_l`/`leg_r`, the `limbs.legs` capability) and neither knees nor foot swaps, so every legged gait here swings or lifts a straight leg.

## 2. The gaits

| Gait (spelling) | Method | What it is | Requires | Typical use |
|---|---|---|---|---|
| `legs` | `loco.legged_cycle` | Seen from the side, the legs swing about the hip in opposition; facing the camera the stepping leg lifts. Body bobs once per step; arms counter-swing. | `limbs.legs` | any legged figure; the chain's first link |
| `profile` | `loco.profile_cycle` | The four-pose cycle in profile: legs swing whatever the view in force, the body **sinks after each contact and rises before the next** (down/up, phased to the contacts; the first step rises only, the last sinks only), a longer stride. | `limbs.legs`, `swap.view:side` | Reiniger's silhouettes, any figure drawn side-on |
| `shuffle` | `loco.shuffle` | Feet barely leave the ground: short quick steps, almost no bob, arms close. | `limbs.legs` | the old, the tired, the cautious; Norstein-like small steps |
| `hem` | `loco.hem_sway` | A robe whose two hem halves are the leg slots: facing the camera they tilt in turn; the body sways and bobs. | `limbs.legs` (the hem halves) | OverSimplified robe figures carved with a split hem |
| `waddle` | `loco.waddle` | The body rocks from foot to foot (weight shift, no knees) and bobs; legs, if any, lift in turn. | nothing | penguins, toddlers, squat figures |
| `hop` | `loco.hop` | The whole figure jumps on every step. | nothing | birds, gleeful characters, a cartoon "boing" |
| `bounce` | `loco.bounce` | The body bobs on every step while it slides; legs, if any, only flick. | nothing | South Park's walk [6] |
| `glide` | `loco.glide` | The figure slides, leaning slightly into the move with a gentle bob; no limb moves. | nothing | robe figures, ghosts, sacks; Kurzgesagt-style floating; **the default without legs** |
| `rock` | `loco.rock` | No leg moves: the body rocks side to side about its root and bobs. | nothing | the pre-an#224 legless walk, kept as a choice |

What each needs, in the capability grammar of `an.capabilities`: `limbs.legs` is two leg slots with art, pivoted at the hip; `swap.view:side` is a side view, either the art's rest view (`rest_view: side`) or a turnaround key (`an character add-views`). A requirement-free gait uses what it finds: `waddle` and `bounce` move a leg pair when there is one, and every gait swings the arms (`limbs.arms`) when its `arm_swing` is not 0.

How gaits compose with **turns and views**: a walk never turns the character. `legs`, `shuffle` and `bounce` read the view in force (a `side`/`three_quarter` view swings the legs, any other lifts them); `profile` always swings; the requirement-free gaits move the body only, so they read the same in every view. The classic walk-off stays `turn` then `walk`.

## 3. Parameters and defaults

Every gait reads the parameters its method declares (`an character capabilities` lists them), each with a shared default (`cutan.motion.WALK_PARAM_DEFAULTS`) that a gait may override (`GAIT_DEFAULTS`); an author's value wins over both.

| Parameter | Shared default | Unit | Scales with the figure | Overridden by |
|---|---|---|---|---|
| `step_s` | 0.4 | s per step | no | `shuffle` 0.3 |
| `step_length` | 80 | scene px per step | **yes** | `shuffle` 40 |
| `stride` | 0.35 | rad a leg swings | no | `profile` 0.45, `shuffle` 0.12, `bounce` 0.1 |
| `lift` | 10 | px a stepping leg rises (in the figure's frame) | already does | `shuffle` 3, `waddle` 5, `bounce` 4 |
| `bob` | 6 | px the body travels per step (`profile`: between two contacts it sinks a third after one and rises two thirds before the next; the first step rises only, the last sinks only) | **yes** | `shuffle` 1, `waddle` 4, `bounce` 8, `glide` 1.5 |
| `arm_swing` | 0.3 | rad | no | `profile` 0.35, `shuffle` 0.1, `waddle`/`bounce` 0.15, `hop`/`glide` 0 |
| `rock` | 0.06 | rad the body rocks, onto the standing foot (follows the figure's facing) | no | `waddle` 0.12 |
| `hem_tilt` | 0.24 | rad a hem half tilts | no | |
| `hop_height` | 18 | px the body jumps | **yes** | |
| `lean` | 0.04 | rad a glide leans into the move | no | |

**Relative to the drawn size** (an#224's comment). A descriptor rig is drawn so its view box is 345 scene px tall at scale 1 (`SCENE_PX_PER_VIEW_BOX`), so a character's drawn size is that times its stage scale. The lengths above are stated for scale 1 and multiplied by the figure's scale (its `stage.scale`, the rig as built — never the pose at the play's start, which a `pop_in` under the walk holds at 0, cutan#13): a character staged at `scale: 2` steps 160 px and bobs 12 px, where it used to shuffle 80 px steps. A leg's `lift` is in the figure's own frame and already scales with it; angles never scale. An explicit value is scene px as given.

A parameter set to **0 writes no channel** (an authored move on that property runs under the walk untouched), and every channel, the body's included, lands with a 1 ms constant tween rather than a settling `set`, so an authored move that outlasts the walk carries on. A one-step walk (any `distance` under 1.5 × `step_length`) still swings its limbs: their one extreme is mid-step.

## 4. The default chain, and choosing

`legs` (if the rig affords `limbs.legs`) → `glide` (requires nothing).

- A chain ends at its first requirement-free method, so it has exactly one requirement-free link. The plan's "legged → hop → glide" cannot be a chain (hop and glide both require nothing). `glide` is the last link because it moves a figure **without pretending a structure it does not have**: the pre-an#224 `rock` tilted the whole figure about its feet like a metronome, which is what read as strange on OverSimplified's robe figures, and a hop is a characterisation, not a neutral default.
- An author picks a gait explicitly: `args: {gait: hop}` on the `walk` play, or `"gait": "bounce"` in `character.json` for every walk of that character, or a version-pinned choice `{method: loco.bounce, args: {bob: 10}, version: "1"}`.
- When the asked gait does not apply, the walk uses the chain's choice and the substitution is **recorded** (`asset_resolution`, a warning, fatal under `--strict-assets`); `an validate` says it before any render (`cutout.walk_gait`), naming the missing capability and its remedy; `an character capabilities <name>` lists every gait that applies and why each other one does not.
- A style that always walks one way (South Park bounces even when its characters have legs) is ADR 0002's **policy**; the matcher takes one (`resolve(..., policy=)`), but no style document is read by the compiler yet, so today a style is applied through each character's declared `gait`.

## 5. Per style, as the Alice & Bob comparison renders them

| Style | Characters | Gait |
|---|---|---|
| South Park | carved legs | `bounce` (the show's slide-and-bob) |
| OverSimplified | robe figures | `glide` (the default without legs; `hem` once the hem is carved in two) |
| Reiniger | jointed silhouettes in profile | `profile` |

## Open

- Measure footage of each style (step period, bob height in figure heights, stride angle) and tune `GAIT_DEFAULTS` from it.
- Knees and foot swaps: a `limbs.knees` capability and replacement feet would let `legs`/`profile` bend at the knee and roll the foot, as Harmony and Moho rigs do [4, 5].
- The style `policy:` block read by the compiler (ADR 0002 decision 4).
- Runs, sneaks and struts [1, 2]: further gaits with the same shape.

## References

1. Williams R. *The Animator's Survival Kit*. London: Faber and Faber; 2001. Chapters "Walks" and "Run, Jumps and Skips".
2. Blair P. *Cartoon Animation*. Laguna Hills (CA): Walter Foster; 1994. "The walk", "Character walks".
3. Whitaker H, Halas J. *Timing for Animation*. London: Focal Press; 1981 (2nd ed. Sito T, 2009). "Walks", "Timing of a walk".
4. Toon Boom Animation. [Harmony documentation: cut-out character rigging and animation](https://docs.toonboom.com/help/harmony-22/premium/cut-out-animation/about-cut-out-animation.html).
5. Lost Marble. [Moho user manual: bones and smart bones](https://moho.lostmarble.com/pages/manual).
6. Parker T, Stone M. *South Park* (Comedy Central, 1997–), whose computer animation imitates the original construction-paper cut-outs, with characters that bob as they slide.
