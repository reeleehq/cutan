# cutan.verify.cadence

Pre-render cadence lint: the scene’s timing against its style spec (catalogue B6, an#519 rank 5).

The styles were measured on timing (`cutan.verify.style` measures a render); the
spec’s `live` block already declares what the IR should say: `tween_duration_s`,
`easing` and `meta.step_hz`. `an validate` reads those from the style spec the
scene’s style pack was copied from (or the pack’s own name, when it is a shipped
style) and warns, before any render, on:

- `duration`: tweens lasting outside `tween_duration_s` (a South Park scene that
  glides, an OverSimplified scene of snaps);
- `easing`: tweens whose resolved easing is not in the spec’s `easing` list;
- `step_hz`: a scene whose `meta.step_hz` is not the style’s (a stepped style on
  ones, or a smooth one stepped).

Silent when the scene names no style, the name is not a shipped spec, or the spec
declares none of these. One finding per shot and kind, with a count and the first
offender. The hold-gap half of catalogue B6 (no changes closer than a minimum hold)
needs a per-style hold declaration the specs do not carry yet: not built.
[`cadence_faults()`](#cutan.verify.cadence.cadence_faults) is the pure function under the check.

### Functions

| [`check_cadence`](#cutan.verify.cadence.check_cadence)(ctx)           | The genre's `cutout.cadence` check, once per scene (catalogue B6, pre-render tier).                |
|-------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------|
| [`cadence_faults`](#cutan.verify.cadence.cadence_faults)(tweens, live) | `{fault: [what, ...]}` for `tweens` (`(label, duration_s, easing)`) against a spec's `live` block. |
| [`spec_for_pack`](#cutan.verify.cadence.spec_for_pack)(ctx)           | The shipped style spec the scene's style pack comes from, or `None`.                               |

### cutan.verify.cadence.cadence_faults(tweens, live)

`{fault: [what, ...]}` for `tweens` (`(label, duration_s, easing)`) against a spec’s `live` block.

```pycon
>>> live = {"tween_duration_s": [0.12, 0.25], "easing": ["linear", "step"]}
>>> cadence_faults([("a.x", 0.2, "linear"), ("b.x", 1.0, "ease_in")], live)
{'duration': ['b.x lasts 1 s'], 'easing': ['b.x eases with ease_in']}
>>> cadence_faults([("a.x", 0.2, "step")], live)
{}
```

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]]

### cutan.verify.cadence.check_cadence(ctx)

The genre’s `cutout.cadence` check, once per scene (catalogue B6, pre-render tier).

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### cutan.verify.cadence.spec_for_pack(ctx)

The shipped style spec the scene’s style pack comes from, or `None`.

The pack’s recorded origin (`metadata.style_spec.name`) wins; else the pack
name when it is itself a shipped style.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)] | [`None`](https://docs.python.org/3/builtins/constants.html#None)
