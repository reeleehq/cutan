"""A style's policy: per-aspect method orders the compiler applies (ADR 0002 decision 4, cutan#9).

A first-applicable chain cannot say "this show bounces even when its
characters have legs" (South Park), "these figures glide" (OverSimplified) or
"silhouettes mime" (Reiniger); a policy can. It is a ``policy:`` block, one
method order per aspect, naming methods by id::

    policy:
      locomotion: [loco.bounce]
      speech: [speech.pose_only]

**Precedence**, as ADR 0002 decision 4 states it: the author's explicit request
(a walk's ``gait``, a character's declared ``gait`` or ``speech``), then the
shot, then the style, then the aspect's default chain. Where each lives:

- **the style**: the spec's ``policy:`` block (:func:`cutan.styles.style_spec`),
  carried into the project by the StylePack :func:`style_pack` builds (its
  ``policy`` field), the document a scene names in ``meta.style_pack``. A
  snapshot, like every copy of a spec: the pack records the spec's digest;
- **the shot**: a ``policy`` field on the shot. ``an``'s ``scene.md`` reader
  keeps only the shot keys it knows, so today it is read from ``ir/scene.json``
  or set in Python, not from a ``yaml shot`` block (thorwhalen/an#348).

A policy choice is information, not a warning: a character that could walk on
legs but bounces under South Park records a ``policy`` resolution beside its
stand-ins, so the choice is visible and never silent.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

__all__ = [
    "APPLIED_ASPECTS",
    "POLICY_KEY",
    "PolicyError",
    "check_policy",
    "layered_policy",
    "policy_of",
    "policy_problems",
    "style_pack",
]

#: The key of a policy block: in a style spec, on a StylePack, on a shot.
POLICY_KEY: str = "policy"

#: The aspects whose method the cut-out compiler resolves, so a policy on them
#: takes effect (``expression`` is resolved only for warnings today: a policy
#: there would be accepted and do nothing, so it is refused).
APPLIED_ASPECTS: tuple[str, ...] = ("locomotion", "speech")

#: The genre whose aspects this module judges (others are theirs to judge).
_GENRE: str = "cutout_animation"


class PolicyError(ValueError):
    """A policy block names an aspect or a method that does not exist, or is malformed."""


def _registry():
    import an.genres

    an.genres.load()
    import an.semantic as semantic

    return semantic


def policy_problems(policy: Any) -> list[str]:
    """What is wrong with a ``policy`` block, one sentence each (empty when it is sound).

    Every aspect must be registered, every choice a method OF that aspect (by
    id: ``loco.bounce``, not ``bounce``), and every choice well formed (an id or
    ``{method, args, version}``).

    >>> policy_problems({"locomotion": ["loco.bounce", "loco.glide"]})
    []
    >>> for p in policy_problems({"locomotion": ["bounce"], "dance": ["x"]}): print(p)
    policy locomotion: 'bounce' is not a locomotion method id; did you mean 'loco.bounce'?
    policy aspect 'dance' is not registered (aspects: expression, locomotion, speech)
    """
    if policy is None:
        return []
    if not isinstance(policy, Mapping):
        return [
            f"a policy is a mapping {{aspect: [method, ...]}}, not {type(policy).__name__}"
        ]
    S = _registry()
    names = sorted(S.aspect_names())
    out: list[str] = []
    for aspect_name, choices in policy.items():
        if aspect_name not in names:
            out.append(
                f"policy aspect {aspect_name!r} is not registered (aspects: {', '.join(names)})"
            )
            continue
        if aspect_name not in APPLIED_ASPECTS:
            # another genre's aspect is that genre's to apply; refuse only the
            # cut-out's own aspects the compiler does not apply yet
            if S.owner_of_aspect(aspect_name) == _GENRE:
                out.append(
                    f"policy aspect {aspect_name!r} is not applied by the cut-out "
                    f"compiler yet (it applies: {', '.join(APPLIED_ASPECTS)})"
                )
            continue
        methods = {m.id: m for m in S.methods_of(aspect_name)}
        by_term = {getattr(m, "term", None): m.id for m in methods.values()}
        items = (
            [choices] if isinstance(choices, (str, Mapping)) else list(choices or ())
        )
        if not items:
            out.append(f"policy {aspect_name}: an empty method order")
        for c in items:
            try:
                choice = S.Choice.of(c)
            except S.VocabularyError as e:
                out.append(f"policy {aspect_name}: {e}")
                continue
            if choice.method not in methods:
                hint = (
                    f"; did you mean {by_term[choice.method]!r}?"
                    if choice.method in by_term
                    else f" (its methods: {', '.join(sorted(methods))})"
                )
                out.append(
                    f"policy {aspect_name}: {choice.method!r} is not a {aspect_name} method id{hint}"
                )
        if aspect_name == "locomotion":
            out.extend(_view_dependent_length_args(items, methods, S))
    return out


#: The walk args that set its LENGTH (what a ``sequence`` waits for).
_LENGTH_ARGS: frozenset[str] = frozenset(
    {"step_s", "step_length", "steps", "distance", "to_x"}
)


def _view_dependent_length_args(items, methods, S) -> list[str]:
    """A locomotion order whose entries need a view (``swap.view:side``) decides
    its winner by the view in force at the walk; a walk's extent is measured
    before the timeline places it, so it cannot know that view. An entry's own
    length args would then make a ``sequence`` wait for the wrong walk: refused.
    """
    choices = []
    for c in items:
        try:
            choices.append(S.Choice.of(c))
        except S.VocabularyError:
            return []
    needs_view = [
        c.method
        for c in choices
        if c.method in methods
        and any(str(r).startswith("swap.view") for r in methods[c.method].requires)
    ]
    if not needs_view:
        return []
    return [
        f"policy locomotion: {c.method!r} sets {', '.join(sorted(set(c.args) & _LENGTH_ARGS))}, "
        f"but which entry wins depends on the view in force ({', '.join(needs_view)} needs "
        "one), which a walk's length is measured without: put length args on the walk"
        for c in choices
        if set(c.args) & _LENGTH_ARGS
    ]


def check_policy(policy: Any, *, where: str = "policy") -> Any:
    """``policy`` parsed into an :class:`an.semantic.Policy`, or :class:`PolicyError` naming ``where``."""
    problems = policy_problems(policy)
    if problems:
        raise PolicyError(f"{where}: " + "; ".join(problems))
    return _registry().Policy.of(policy or {})


def policy_of(obj: Any) -> Any:
    """The policy block an object carries: a ``policy`` field (declared or extra) or key; else ``None``.

    >>> policy_of({"policy": {"locomotion": ["loco.glide"]}})
    {'locomotion': ['loco.glide']}
    >>> policy_of(None) is None
    True
    """
    if obj is None:
        return None
    if isinstance(obj, Mapping):
        return obj.get(POLICY_KEY)
    return getattr(obj, POLICY_KEY, None)


def layered_policy(*, shot: Any = None, style_pack: Any = None) -> Any:
    """The policy in force: ``shot`` over ``style_pack`` (each checked).

    Each argument is anything :func:`policy_of` reads (or ``None``). The
    author's explicit request is not here: the matcher puts it first
    (``resolve(..., requested=)``).
    """
    S = _registry()
    layers = []
    for where, obj in (
        ("the shot's policy", shot),
        ("the style pack's policy", style_pack),
    ):
        block = policy_of(obj)
        if block is not None:
            layers.append(check_policy(block, where=where))
    return S.Policy.layered(*layers)


def style_pack(spec: Any) -> Any:
    """The StylePack a project saves for a style: its ``live.style_pack`` (a bare
    pack named after the style when the spec has none), its ``policy``, and the
    spec it was copied from (name and digest) in ``metadata``.

    ``spec`` is anything :func:`cutan.styles.resolve_style_spec` takes (a
    style's name, a path, a mapping). Save it as the skill's step 3 says:
    ``mall["styles"][pack.name] = pack.model_dump(mode="json")``.

    >>> pack = style_pack("south_park")
    >>> pack.name, pack.policy, pack.metadata["style_spec"]["name"]
    ('south_park', {'locomotion': ['loco.bounce']}, 'south_park')
    """
    from an.styles import StylePack

    from cutan.styles import _is_style_name, resolve_style_spec, style_spec_digest

    data = resolve_style_spec(spec)
    live = data.get("live") or {}
    # a spec with no palette still has a document for its policy: a bare pack
    pack = dict(live.get("style_pack") or {"name": data.get("style")})
    block = data.get(POLICY_KEY)
    if block is not None:
        check_policy(block, where=f"style spec {data.get('style')!r}")
        pack[POLICY_KEY] = block
    origin = {"name": data.get("style")}
    if _is_style_name(spec):
        origin["sha256"] = style_spec_digest(spec)
    elif not isinstance(
        spec, Mapping
    ):  # a file: the same digest rule as the shipped specs
        import hashlib
        from pathlib import Path

        raw = Path(spec).read_bytes().replace(b"\r\n", b"\n")
        origin["sha256"] = hashlib.sha256(raw).hexdigest()
    pack["metadata"] = {**(pack.get("metadata") or {}), "style_spec": origin}
    return StylePack(**pack)


def _is_cutout(shot: Any) -> bool:
    from cutan import RENDERER_NAME

    return getattr(shot, "renderer", RENDERER_NAME) == RENDERER_NAME


def check_shot_policy(ctx) -> None:
    """``an validate``'s side (cutan#9), per cut-out shot: its ``policy`` is well formed."""
    if not _is_cutout(ctx.shot):
        return
    block = policy_of(ctx.shot)
    if block is not None:
        for problem in policy_problems(block):
            ctx.report.add("error", f"{ctx.path}/policy", problem)
