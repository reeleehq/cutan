"""A vision critic for body-depicting props: narrow yes/no questions over probe frames (cutan#95).

The deterministic body-continuity check (:mod:`cutan.verify.body`) trusts the
sockets a prop declares: it cannot see whether a drawing's sleeves really end
where its sockets say, or whether hands were drawn from the camera's side. A
production shipped exactly that: a steering wheel with the driver's hands drawn
from the driver's seat, laid over a driver seen through the windscreen.

This critic looks. For each shot holding a prop that declares a
``metadata.body_attachment``, it probes frames of the shot (:func:`an.probe.frames`,
the path a render draws), asks a vision model a short checklist of yes/no
questions answerable from appearance, chosen by the prop's declared ``view``
(:data:`CHECKLISTS`: a first-person prop's arms DO come from the bottom edge),
and reports each answer that differs from the one a correct drawing gives as a
**warning**: never the gate. Free-form "does this look right?" is not asked:
vision models answer camera-perspective questions at about 34-47%
(ViewSpatial-Bench, arXiv 2505.21500); narrow questions about what is visible
fare better.

It is optional and costs money, so nothing runs it by default (the issue's
``critic=None`` keyword on the check's function would not do: that check runs
inside ``an validate``, which never renders). :func:`critique_body_props` takes
the judge (default: ``an``'s paid seam, :func:`an.verify.vision.judge_envelope`)
and the frame source as keywords. A configured judge that fails is a failure (an
``error`` finding), never a silent pass. Every call is recorded in the report
(shot, prop, frames, model): what it cost.

>>> parse_answers('{"answers": [{"n": "1", "answer": "No."}]} Note: {x}', CHECKLISTS["front"])[0]
{'n': 1, 'answer': 'no', 'why': ''}
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Union

from cutan.body_attachment import FIRST_PERSON, body_attachment_of, bound_character
from cutan.verify.body import Finding, declaring_props

__all__ = [
    "CHECKLISTS",
    "Question",
    "CritiqueReport",
    "critique_body_props",
    "checklist_for",
    "checklist_prompt",
    "parse_answers",
]


@dataclass(frozen=True)
class Question:
    """A yes/no question, and the answer a correct drawing gives."""

    text: str
    expected: str  # "yes" or "no"


_SLEEVES = Question(
    "Does every sleeve or forearm touching the {prop} continue towards a "
    "shoulder of {character}, the person visible in the picture?",
    "yes",
)
_NOT_FROM_BELOW = Question(
    "Do any forearms enter the picture from its bottom edge, as if they were "
    "the camera's own arms?",
    "no",
)
#: Narrow questions about a prop that depicts a character's limbs, answerable
#: from appearance, by the prop's declared ``view`` (``"*"``: any view not
#: listed). ``{prop}`` and ``{character}`` are filled in per shot.
CHECKLISTS: dict[str, tuple[Question, ...]] = {
    "front": (
        _SLEEVES,
        _NOT_FROM_BELOW,
        Question(
            "Are the hands on the {prop} seen from the same side as {character}'s "
            "face (both from the front)?",
            "yes",
        ),
    ),
    # the camera IS the character: its arms come from below, and no face shows
    FIRST_PERSON: (
        Question(
            "Do the forearms holding the {prop} enter the picture from its bottom "
            "edge, as if they were the camera's own arms?",
            "yes",
        ),
        Question("Is the face of the person holding the {prop} visible in the picture?", "no"),
    ),
    "*": (_SLEEVES, _NOT_FROM_BELOW),
}

#: The probe instants, as fractions of each shot's length.
DFLT_AT: tuple[float, ...] = (0.5,)

_PROMPT = """You are checking frames from a cut-out animated cartoon for one drawing
mistake: a prop that shows a character's hands or sleeves (here: {prop}, held by
{character}) drawn from the wrong point of view, so the arms do not belong to
the body on screen. Answer each question from what is visible, "yes", "no" or
"unsure", with a few words why. Reply with JSON only:
{{"answers": [{{"n": 1, "answer": "yes", "why": "..."}}, ...]}}

{questions}
"""

Checklist = Union[Sequence[Question], Mapping[str, Sequence[Question]]]


def checklist_for(view: str, checklists: Checklist = CHECKLISTS) -> Sequence[Question]:
    """The questions for a prop declared in ``view``: a mapping's entry for it
    (else its ``"*"``), or ``checklists`` itself when it is one list.

    >>> [q.expected for q in checklist_for("first_person")]
    ['yes', 'no']
    >>> len(checklist_for("side"))
    2
    """
    if isinstance(checklists, Mapping):
        return checklists.get(view) or checklists.get("*") or ()
    return checklists


def checklist_prompt(
    checklist: Sequence[Question], *, prop: str, character: str
) -> str:
    """The prompt asking ``checklist`` about ``prop`` held by ``character``.

    >>> "1. Does every sleeve" in checklist_prompt(CHECKLISTS["front"], prop="wheel", character="ned")
    True
    """
    questions = "\n".join(
        f"{n}. {q.text.format(prop=prop, character=character)}"
        for n, q in enumerate(checklist, 1)
    )
    return _PROMPT.format(prop=prop, character=character, questions=questions)


def _first_json_object(text: str) -> Any:
    """The first JSON object in ``text`` (prose and braces around it ignored)."""
    decoder = json.JSONDecoder()
    for m in re.finditer(r"\{", text):
        try:
            value, _ = decoder.raw_decode(text, m.start())
        except ValueError:
            continue
        if isinstance(value, dict):
            return value
    return None


_LEADING_ANSWER = re.compile(r"^\W*(yes|no)\b", re.I)


def parse_answers(reply: str, checklist: Sequence[Question]) -> list[dict[str, Any]] | None:
    """The answers in a judge's reply, one per question (``answer`` is ``yes``,
    ``no`` or ``unsure``: read from its leading word); ``None`` when the reply
    holds no answers at all.

    >>> parse_answers('{"answers": [{"n": 2, "answer": "yes, clearly"}]}', CHECKLISTS["front"])[1]
    {'n': 2, 'answer': 'yes', 'why': ''}
    >>> parse_answers("I cannot tell", CHECKLISTS["front"]) is None
    True
    """
    data = _first_json_object(reply)
    raw = data.get("answers") if isinstance(data, dict) else None
    if not isinstance(raw, list):
        return None
    by_n = {}
    for item in raw:
        if not isinstance(item, dict):
            continue
        n = item.get("n")
        n = int(n) if isinstance(n, str) and n.strip().isdigit() else n
        if not isinstance(n, int) or isinstance(n, bool):
            continue
        m = _LEADING_ANSWER.match(str(item.get("answer", "")))
        by_n[n] = {"n": n, "answer": m.group(1).lower() if m else "unsure", "why": str(item.get("why", ""))}
    if not by_n:
        return None
    return [by_n.get(n, {"n": n, "answer": "unsure", "why": ""}) for n in range(1, len(checklist) + 1)]


@dataclass
class CritiqueReport:
    """The critic's findings, and every judge call it made (what it cost)."""

    findings: list[Finding] = field(default_factory=list)
    calls: list[dict[str, Any]] = field(default_factory=list)


def _default_frames(project: Any, shot: str, times: Sequence[float]) -> list[bytes]:
    from an.probe import frames

    return frames(project, shot, times)


def _envelope_judge(model: str | None) -> Callable[..., Mapping[str, Any]]:
    from an.verify.vision import judge_envelope

    def judge(frames: Sequence[bytes], *, prompt: str) -> Mapping[str, Any]:
        return judge_envelope(frames, prompt=prompt, **({"model": model} if model else {}))

    return judge


def critique_body_props(
    project: Any,
    *,
    judge: Callable[..., Union[str, Mapping[str, Any]]] | None = None,
    checklists: Checklist = CHECKLISTS,
    at: Sequence[float] = DFLT_AT,
    frames: Callable[[Any, str, Sequence[float]], list[bytes]] | None = None,
    model: str | None = None,
) -> CritiqueReport:
    """Ask each body-depicting prop of ``project``'s shots its view's checklist.

    project: a loaded :class:`an.project.Project` or its folder
    judge: ``judge(frames, *, prompt)`` returning the reply text, or an envelope
        with ``reply`` and ``model`` (default: ``an``'s
        :func:`~an.verify.vision.judge_envelope`, a paid call, with ``model``)
    checklists: questions by declared view (:data:`CHECKLISTS`), or one list for all
    at: the probe instants, as fractions of each shot's length, in [0, 1]
    frames: ``frames(project, shot_id, times) -> [png bytes]`` (default:
        :func:`an.probe.frames`, which needs the renderer's headless browser)
    model: the default judge's model; recorded with each call

    A finding is ``(severity, ir path, message)``: a ``warning`` per answer that
    differs from a correct drawing's, an ``info`` per ``unsure``, an ``error``
    when the judge or the probe fails or the reply holds no answers. A prop
    whose character is not in the shot is not asked (a first-person prop's is
    off screen by design, so it is).
    """
    from an.project import load

    if not at or any(not 0.0 <= f <= 1.0 for f in at):
        raise ValueError(f"`at` holds fractions of a shot's length in [0, 1], not {list(at)}")
    report = CritiqueReport()
    if judge is None:
        try:
            import anthropic  # noqa: F401 - the default judge's SDK, checked before any probe
        except ImportError:
            report.findings.append(
                ("error", "", "the body critic's default judge needs the anthropic SDK: pip install an[vision]")
            )
            return report
        judge = _envelope_judge(model)
    project = load(project) if not hasattr(project, "scene") else project
    frames = frames or _default_frames
    props = project.mall.get("props")
    if props is None:
        return report
    for i, shot in enumerate(project.scene.timeline):
        shown: list[bytes] | None = None  # probed once per shot, for all its props
        for j, entity, raw in declaring_props(shot, props):
            where = f"timeline/{i}/entities/{j}"
            try:
                ba = body_attachment_of(raw)
            except Exception:  # noqa: BLE001 - a malformed declaration is the body check's to report
                continue
            if ba is None:
                continue
            char_entity, character = bound_character(shot, entity, ba)
            if char_entity is None and ba.view != FIRST_PERSON:
                continue  # nobody on screen to belong to: the body check says so
            checklist = checklist_for(ba.view, checklists)
            if not checklist:
                continue
            prompt = checklist_prompt(checklist, prop=entity.id, character=character or "the character")
            try:
                if shown is None:
                    shown = frames(project, shot.id, [f * shot.duration for f in at])
                answer = judge(shown, prompt=prompt)
            except Exception as e:  # noqa: BLE001 - configured and broken is a failure, said aloud
                report.findings.append(
                    ("error", where, f"the body critic could not judge prop {entity.id!r}: {type(e).__name__}: {e}")
                )
                continue
            reply = answer.get("reply", "") if isinstance(answer, Mapping) else str(answer)
            used = answer.get("model", model) if isinstance(answer, Mapping) else model
            report.calls.append({"shot": shot.id, "prop": entity.id, "frames": len(shown), "model": used})
            answers = parse_answers(reply, checklist)
            if answers is None:
                report.findings.append(
                    ("error", where, f"the body critic's reply about prop {entity.id!r} held no answers: {reply[:200]!r}")
                )
                continue
            for q, a in zip(checklist, answers):
                text = q.text.format(prop=entity.id, character=character or "the character")
                if a["answer"] == "unsure":
                    report.findings.append(("info", where, f"body critic, unsure: {text}"))
                elif a["answer"] != q.expected:
                    report.findings.append(
                        (
                            "warning",
                            where,
                            f"body critic (shot {shot.id!r}, a vision model, not a measurement): "
                            f"{text} {a['answer']}, expected {q.expected}"
                            + (f" ({a['why']})" if a["why"] else "")
                            + ". Check the drawing: the hands may be drawn from another point of view.",
                        )
                    )
    return report
