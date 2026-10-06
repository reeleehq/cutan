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
- **the shot**: its `policy` field (`Shot.policy`, declared by `an`
  since thorwhalen/an#348), written in its `yaml shot` block, in
  `ir/scene.json` or in Python.

Where a character’s DECLARED `gait`/`speech` sits is the core matcher’s one
rule (`an.semantic.matcher.DECLARED_OUTRANKS_POLICY`, cutan#36): today it is
the request. The compiler hands the policy to the `play` lowering through its
products ([`cutan.compile.passes.POLICY_PRODUCT`](cutan.compile.passes.md#cutan.compile.passes.POLICY_PRODUCT)); `an validate` layers
the same two documents ([`policy_in_force()`](#cutan.styles.policy.policy_in_force), the pack read from the
`styles` store), so the two resolve every walk alike.

A policy choice is information, not a warning: a character that could walk on
legs but bounces under South Park records a `policy` resolution beside its
stand-ins, so the choice is visible and never silent.

### Module Attributes

| [`POLICY_KEY`](#cutan.styles.policy.POLICY_KEY)      | in a style spec, on a StylePack, on a shot.                                                                                                                                                                     |
|------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`APPLIED_ASPECTS`](#cutan.styles.policy.APPLIED_ASPECTS) | The aspects whose method the cut-out compiler resolves, so a policy on them takes effect (`expression` is resolved only for warnings today: a policy there would be accepted and do nothing, so it is refused). |

### Functions

| [`check_policy`](#cutan.styles.policy.check_policy)(policy, \*[, where])       | `policy` parsed into an `an.semantic.Policy`, or [`PolicyError`](#cutan.styles.policy.PolicyError) naming `where`.                                                                                                                                                        |
|------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`layered_policy`](#cutan.styles.policy.layered_policy)(\*[, shot, style_pack])  | The policy in force: `shot` over `style_pack` (each checked).                                                                                                                                                                                                                        |
| [`policy_in_force`](#cutan.styles.policy.policy_in_force)(ctx, \*[, shot, index]) | The policy the compiler will resolve a shot's aspects under: its `policy` over the scene's style pack's ([`layered_policy()`](#cutan.styles.policy.layered_policy)), once per shot; `None` when neither has one or either is malformed (`check_shot_policy()` reports that). |
| [`policy_of`](#cutan.styles.policy.policy_of)(obj)                          | The policy block an object carries: a `policy` field (declared or extra) or key; else `None`.                                                                                                                                                                                        |
| [`policy_problems`](#cutan.styles.policy.policy_problems)(policy)                 | What is wrong with a `policy` block, one sentence each (empty when it is sound).                                                                                                                                                                                                     |
| [`style_pack`](#cutan.styles.policy.style_pack)(spec)                        | The StylePack a project saves for a style: its `live.style_pack` (a bare pack named after the style when the spec has none), its `policy`, and the spec it was copied from (name and digest) in `metadata`.                                                                          |

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

### cutan.styles.policy.policy_in_force(ctx, , shot=None, index=None)

The policy the compiler will resolve a shot’s aspects under: its
`policy` over the scene’s style pack’s ([`layered_policy()`](#cutan.styles.policy.layered_policy)), once per
shot; `None` when neither has one or either is malformed
(`check_shot_policy()` reports that). The shot is the check’s current
one unless `shot` and `index` name another (a scene-stage check).

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
