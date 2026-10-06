# cutan.styles.policy

A style’s policy: per-aspect method orders the compiler applies (ADR 0002 decision 4, cutan#9).

A first-applicable chain cannot say “this show bounces even when its
characters have legs” (South Park), “these figures glide” (OverSimplified) or
“silhouettes mime” (Reiniger); a policy can. It is a `policy:` block, one
method order per aspect, naming methods by id:

```default
policy:
  locomotion: [loco.bounce]
  speech: [speech.pose_only]
```

**Precedence**, as ADR 0002 decision 4 states it: the author’s explicit request
(a walk’s `gait`, a character’s declared `gait` or `speech`), then the
shot, then the style, then the aspect’s default chain. Where each lives:

- **the style**: the spec’s `policy:` block ([`cutan.styles.style_spec()`](cutan.styles.md#cutan.styles.style_spec)),
  carried into the project by the StylePack [`style_pack()`](#cutan.styles.policy.style_pack) builds (its
  `policy` field), the document a scene names in `meta.style_pack`. A
  snapshot, like every copy of a spec: the pack records the spec’s digest;
- **the shot**: a `policy` field on the shot. `an`’s `scene.md` reader
  keeps only the shot keys it knows, so today it is read from `ir/scene.json`
  or set in Python, not from a `yaml shot` block (thorwhalen/an#348).

A policy choice is information, not a warning: a character that could walk on
legs but bounces under South Park records a `policy` resolution beside its
stand-ins, so the choice is visible and never silent.

### Module Attributes

| [`POLICY_KEY`](#cutan.styles.policy.POLICY_KEY)      | in a style spec, on a StylePack, on a shot.                                                                                                                                                                     |
|------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`APPLIED_ASPECTS`](#cutan.styles.policy.APPLIED_ASPECTS) | The aspects whose method the cut-out compiler resolves, so a policy on them takes effect (`expression` is resolved only for warnings today: a policy there would be accepted and do nothing, so it is refused). |

### Functions

| [`applicable_policy`](#cutan.styles.policy.applicable_policy)(policy, aspect, profile, \*)   | `policy` with `aspect`'s order cut to the methods that apply to `profile`.                                                                                                                                  |
|---------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`check_policy`](#cutan.styles.policy.check_policy)(policy, \*[, where])                | `policy` parsed into an `an.semantic.Policy`, or [`PolicyError`](#cutan.styles.policy.PolicyError) naming `where`.                                                                               |
| [`layered_policy`](#cutan.styles.policy.layered_policy)(\*[, shot, style_pack])           | The policy in force: `shot` over `style_pack` (each checked).                                                                                                                                               |
| [`policy_of`](#cutan.styles.policy.policy_of)(obj)                                   | The policy block an object carries: a `policy` field (declared or extra) or key; else `None`.                                                                                                               |
| [`policy_problems`](#cutan.styles.policy.policy_problems)(policy)                          | What is wrong with a `policy` block, one sentence each (empty when it is sound).                                                                                                                            |
| [`style_pack`](#cutan.styles.policy.style_pack)(spec)                                 | The StylePack a project saves for a style: its `live.style_pack` (a bare pack named after the style when the spec has none), its `policy`, and the spec it was copied from (name and digest) in `metadata`. |

### Exceptions

| [`PolicyError`](#cutan.styles.policy.PolicyError)   | A policy block names an aspect or a method that does not exist, or is malformed.   |
|----------------------------------------------------------------|------------------------------------------------------------------------------------|

### cutan.styles.policy.APPLIED_ASPECTS *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), ...]* *= ('locomotion', 'speech')*

The aspects whose method the cut-out compiler resolves, so a policy on them
takes effect (`expression` is resolved only for warnings today: a policy
there would be accepted and do nothing, so it is refused).

### cutan.styles.policy.POLICY_KEY *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'policy'*

in a style spec, on a StylePack, on a shot.

* **Type:**
  The key of a policy block

### *exception* cutan.styles.policy.PolicyError

Bases: [`ValueError`](https://docs.python.org/3/builtins/exceptions.html#ValueError)

A policy block names an aspect or a method that does not exist, or is malformed.

### cutan.styles.policy.applicable_policy(policy, aspect, profile, , on_skip=None)

`policy` with `aspect`’s order cut to the methods that apply to `profile`.

A policy is an order: its first APPLICABLE entry wins (ADR 0002). The
core matcher today treats the order’s head as a request (an#334), so a
head that does not apply (a profile cycle on a figure with no side view)
would be recorded as a fatal `missing` substitution. Handing it only the
entries that apply gives the order’s own meaning: the first of them is a
non-fatal `policy` choice, and none applying leaves the chain to decide.
Each entry passed over before the first applicable one is reported to
`on_skip(method id, missing terms)`, so a skip is recorded, never silent
(ADR 0002 decision 6). Drop this once
an#334 lands.

* **Return type:**
  [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

### cutan.styles.policy.check_policy(policy, , where='policy')

`policy` parsed into an `an.semantic.Policy`, or [`PolicyError`](#cutan.styles.policy.PolicyError) naming `where`.

* **Return type:**
  [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

### cutan.styles.policy.layered_policy(, shot=None, style_pack=None)

The policy in force: `shot` over `style_pack` (each checked).

Each argument is anything [`policy_of()`](#cutan.styles.policy.policy_of) reads (or `None`). The
author’s explicit request is not here: the matcher puts it first
(`resolve(..., requested=)`).

* **Return type:**
  [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

### cutan.styles.policy.policy_of(obj)

The policy block an object carries: a `policy` field (declared or extra) or key; else `None`.

* **Return type:**
  [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

```pycon
>>> policy_of({"policy": {"locomotion": ["loco.glide"]}})
{'locomotion': ['loco.glide']}
>>> policy_of(None) is None
True
```

### cutan.styles.policy.policy_problems(policy)

What is wrong with a `policy` block, one sentence each (empty when it is sound).

Every aspect must be registered, every choice a method OF that aspect (by
id: `loco.bounce`, not `bounce`), and every choice well formed (an id or
`{method, args, version}`).

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

```pycon
>>> policy_problems({"locomotion": ["loco.bounce", "loco.glide"]})
[]
>>> for p in policy_problems({"locomotion": ["bounce"], "dance": ["x"]}): print(p)
policy locomotion: 'bounce' is not a locomotion method id; did you mean 'loco.bounce'?
policy aspect 'dance' is not registered (aspects: expression, locomotion, speech)
```

### cutan.styles.policy.style_pack(spec)

The StylePack a project saves for a style: its `live.style_pack` (a bare
pack named after the style when the spec has none), its `policy`, and the
spec it was copied from (name and digest) in `metadata`.

`spec` is anything [`cutan.styles.resolve_style_spec()`](cutan.styles.md#cutan.styles.resolve_style_spec) takes (a
style’s name, a path, a mapping). Save it as the skill’s step 3 says:
`mall["styles"][pack.name] = pack.model_dump(mode="json")`.

* **Return type:**
  [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

```pycon
>>> pack = style_pack("south_park")
>>> pack.name, pack.policy, pack.metadata["style_spec"]["name"]
('south_park', {'locomotion': ['loco.bounce']}, 'south_park')
```
