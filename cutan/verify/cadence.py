"""Pre-render cadence lint: the scene's timing against its style spec (catalogue B6, an#519 rank 5).

The styles were measured on timing (``cutan.verify.style`` measures a render); the
spec's ``live`` block already declares what the IR should say: ``tween_duration_s``,
``easing`` and ``meta.step_hz``. ``an validate`` reads those from the style spec the
scene's style pack was copied from (or the pack's own name, when it is a shipped
style) and warns, before any render, on:

- ``duration``: tweens lasting outside ``tween_duration_s`` (a South Park scene that
  glides, an OverSimplified scene of snaps);
- ``easing``: tweens whose resolved easing is not in the spec's ``easing`` list;
- ``step_hz``: a scene whose ``meta.step_hz`` is not the style's (a stepped style on
  ones, or a smooth one stepped).

Silent when the scene names no style, the name is not a shipped spec, or the spec
declares none of these. One finding per shot and kind, with a count and the first
offender. The hold-gap half of catalogue B6 (no changes closer than a minimum hold)
needs a per-style hold declaration the specs do not carry yet: not built.
:func:`cadence_faults` is the pure function under the check.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

__all__ = ["check_cadence", "cadence_faults", "spec_for_pack"]

#: A tween this far outside the range (seconds) is within a frame's rounding.
DURATION_SLACK_S: float = 1e-6
#: The kinds of action whose ``duration`` is a move.
TWEEN_KIND: str = "tween"


def _easing_key(easing: Any) -> Any:
    """An easing in a comparable form (a bezier's list or tuple as a tuple)."""
    return tuple(easing) if isinstance(easing, (list, tuple)) else easing


def cadence_faults(
    tweens: Sequence[tuple[str, float, Any]], live: Mapping[str, Any]
) -> dict[str, list[str]]:
    """``{fault: [what, ...]}`` for ``tweens`` (``(label, duration_s, easing)``) against a spec's ``live`` block.

    >>> live = {"tween_duration_s": [0.12, 0.25], "easing": ["linear", "step"]}
    >>> cadence_faults([("a.x", 0.2, "linear"), ("b.x", 1.0, "ease_in")], live)
    {'duration': ['b.x lasts 1 s'], 'easing': ['b.x eases with ease_in']}
    >>> cadence_faults([("a.x", 0.2, "step")], live)
    {}
    """
    out: dict[str, list[str]] = {}
    span = live.get("tween_duration_s")
    allowed = live.get("easing")
    allowed_keys = {_easing_key(e) for e in allowed} if allowed else None
    for label, duration, easing in tweens:
        if span and not (
            span[0] - DURATION_SLACK_S <= duration <= span[1] + DURATION_SLACK_S
        ):
            out.setdefault("duration", []).append(f"{label} lasts {duration:g} s")
        if allowed_keys is not None and _easing_key(easing) not in allowed_keys:
            out.setdefault("easing", []).append(f"{label} eases with {easing}")
    return out


def spec_for_pack(ctx: Any) -> dict[str, Any] | None:
    """The shipped style spec the scene's style pack comes from, or ``None``.

    The pack's recorded origin (``metadata.style_spec.name``) wins; else the pack
    name when it is itself a shipped style.
    """
    from cutan.styles import style_spec, style_specs
    from cutan.styles.copies import SPEC_ORIGIN_KEY

    name = getattr(ctx.scene.meta, "style_pack", None)
    if not name:
        return None
    pack = None
    styles = (ctx.stores or {}).get("styles")
    if styles is not None and name in styles:
        pack = styles[name]
    origin = ((pack or {}).get("metadata") or {}).get(SPEC_ORIGIN_KEY) or {}
    style = origin.get("name") or name
    return style_spec(style) if style in style_specs() else None


def check_cadence(ctx: Any) -> None:
    """The genre's ``cutout.cadence`` check, once per scene (catalogue B6, pre-render tier)."""
    from an.ir.compose import iter_actions

    spec = spec_for_pack(ctx)
    live = (spec or {}).get("live") or {}
    if not live:
        return
    style = spec["style"]
    default = ctx.scene.meta.default_easing
    wanted_hz = (live.get("meta") or {}).get("step_hz")
    if wanted_hz is not None and ctx.scene.meta.step_hz != wanted_hz:
        ctx.report.add(
            "warning",
            "meta/step_hz",
            f"style {style!r} steps at {wanted_hz} Hz; this scene's `step_hz` is "
            f"{ctx.scene.meta.step_hz}. Set `step_hz: {wanted_hz}` in the meta block.",
        )
    for i, shot in enumerate(ctx.scene.timeline):
        tweens = [
            (f"{a.target}.{a.property}", float(a.duration), a.resolved_easing(default))
            for top in shot.actions
            for a in iter_actions(top)
            if getattr(a, "kind", None) == TWEEN_KIND
        ]
        for fault, found in cadence_faults(tweens, live).items():
            rule = {
                "duration": f"`tween_duration_s` {live.get('tween_duration_s')}",
                "easing": f"`easing` {live.get('easing')}",
            }[fault]
            more = f" (and {len(found) - 1} more)" if len(found) > 1 else ""
            ctx.report.add(
                "warning",
                f"timeline/{i}/actions",
                f"style {style!r} wants {rule}; {found[0]}{more}. Retime the "
                "tween, or pick the style that matches this timing.",
            )
