"""A vision critic for body-depicting props: narrow yes/no questions over probe frames (cutan#95).

The deterministic body-continuity check (:mod:`cutan.verify.body`) trusts the
sockets a prop declares: it cannot see whether a drawing's sleeves really end
where its sockets say, or whether hands were drawn from the camera's side. A
production shipped exactly that: a steering wheel with the driver's hands drawn
from the driver's seat, laid over a driver seen through the windscreen.

This critic looks. For each shot holding a prop that declares a
``metadata.body_attachment``, it probes frames of the shot (:func:`an.probe.frames`,
the path a render draws), asks a vision model a short checklist of yes/no
questions answerable from appearance (:data:`BODY_CHECKLIST`), and reports each
answer that differs from the one a correct drawing gives as a **warning**:
never the gate. Free-form "does this look right?" is not asked: vision models
answer camera-perspective questions at about 34-47% (ViewSpatial-Bench,
arXiv 2505.21500); narrow questions about what is visible fare better.

It is optional and costs money, so nothing runs it by default:
:func:`critique_body_props` takes the judge (default: ``an``'s paid seam,
:func:`an.verify.vision.judge_frames`, with its cassettes) and the frame source
as keywords. A configured judge that fails is a failure (an ``error`` finding),
never a silent pass. Every call is recorded in the report (shot, frames, model),
which is what it cost.

>>> def judge(frames, *, prompt):
...     return '{"answers": [{"n": 1, "answer": "no", "why": "the arms come from below"}]}'
>>> parse_answers(judge([], prompt=""), BODY_CHECKLIST)[0]["answer"]
'no'
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from cutan.verify.body import Finding, _declaring_props

__all__ = [
    "BODY_CHECKLIST",
    "Question",
    "CritiqueReport",
    "critique_body_props",
    "checklist_prompt",
    "parse_answers",
]


@dataclass(frozen=True)
class Question:
    """A yes/no question, and the answer a correct drawing gives."""

    text: str
    expected: str  # "yes" or "no"


#: Narrow questions about a prop that depicts a character's limbs, answerable
#: from appearance. ``{prop}`` and ``{character}`` are filled in per shot.
BODY_CHECKLIST: tuple[Question, ...] = (
    Question(
        "Does every sleeve or forearm touching the {prop} continue towards a "
        "shoulder of {character}, the person visible in the picture?",
        "yes",
    ),
    Question(
        "Do any forearms enter the picture from its bottom edge, as if they "
        "were the camera's own arms?",
        "no",
    ),
    Question(
        "Are the hands on the {prop} seen from the same side as {character}'s "
        "face (both from the front, or both from behind)?",
        "yes",
    ),
)

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


def checklist_prompt(
    checklist: Sequence[Question], *, prop: str, character: str
) -> str:
    """The prompt asking ``checklist`` about ``prop`` held by ``character``.

    >>> "1. Does every sleeve" in checklist_prompt(BODY_CHECKLIST, prop="wheel", character="ned")
    True
    """
    questions = "\n".join(
        f"{n}. {q.text.format(prop=prop, character=character)}"
        for n, q in enumerate(checklist, 1)
    )
    return _PROMPT.format(prop=prop, character=character, questions=questions)


def parse_answers(reply: str, checklist: Sequence[Question]) -> list[dict[str, Any]] | None:
    """The answers in a judge's reply, one per question (``answer`` is ``yes``,
    ``no`` or ``unsure``); ``None`` when the reply holds no usable JSON.

    >>> parse_answers('{"answers": [{"n": 2, "answer": "No"}]}', BODY_CHECKLIST)[1]
    {'n': 2, 'answer': 'no', 'why': ''}
    >>> parse_answers("I cannot tell", BODY_CHECKLIST) is None
    True
    """
    m = re.search(r"\{.*\}", reply, re.S)
    try:
        data = json.loads(m.group(0)) if m else None
    except ValueError:
        return None
    raw = data.get("answers") if isinstance(data, dict) else None
    if not isinstance(raw, list):
        return None
    by_n = {}
    for item in raw:
        if isinstance(item, dict) and isinstance(item.get("n"), int):
            answer = str(item.get("answer", "")).strip().lower()
            by_n[item["n"]] = {
                "n": item["n"],
                "answer": answer if answer in ("yes", "no") else "unsure",
                "why": str(item.get("why", "")),
            }
    return [by_n.get(n, {"n": n, "answer": "unsure", "why": ""}) for n in range(1, len(checklist) + 1)]


@dataclass
class CritiqueReport:
    """The critic's findings, and every judge call it made (what it cost)."""

    findings: list[Finding] = field(default_factory=list)
    calls: list[dict[str, Any]] = field(default_factory=list)


def _default_judge(frames: Sequence[bytes], *, prompt: str) -> str:
    from an.verify.vision import judge_frames

    return judge_frames(frames, prompt=prompt)


def _default_frames(project: Any, shot: str, times: Sequence[float]) -> list[bytes]:
    from an.probe import frames

    return frames(project, shot, times)


def critique_body_props(
    project: Any,
    *,
    judge: Callable[..., str] | None = None,
    checklist: Sequence[Question] = BODY_CHECKLIST,
    at: Sequence[float] = DFLT_AT,
    frames: Callable[[Any, str, Sequence[float]], list[bytes]] | None = None,
    model: str | None = None,
) -> CritiqueReport:
    """Ask ``checklist`` about every body-depicting prop of ``project``'s shots.

    project: a loaded :class:`an.project.Project` or its folder
    judge: ``judge(frames, *, prompt) -> reply text`` (default: ``an``'s
        :func:`~an.verify.vision.judge_frames`, a paid call)
    at: the probe instants, as fractions of each shot's length
    frames: ``frames(project, shot_id, times) -> [png bytes]`` (default:
        :func:`an.probe.frames`, which needs the renderer's headless browser)
    model: recorded with each call (the default judge's model when ``None``)

    A finding is ``(severity, ir path, message)``: a ``warning`` per answer that
    differs from a correct drawing's, an ``info`` per ``unsure``, an ``error``
    when the judge or the probe fails or the reply holds no answers.
    """
    from an.project import load

    project = load(project) if not hasattr(project, "scene") else project
    judge = judge or _default_judge
    frames = frames or _default_frames
    if model is None:
        from an.verify.vision import _DEFAULT_MODEL

        model = _DEFAULT_MODEL if judge is _default_judge else None
    report = CritiqueReport()
    props = project.mall.get("props")
    if props is None:
        return report
    for i, shot in enumerate(project.scene.timeline):
        for j, entity, raw in _declaring_props(shot, props):
            where = f"timeline/{i}/entities/{j}"
            character = str((raw.get("metadata") or {}).get("body_attachment", {}).get("character", "the character"))
            prompt = checklist_prompt(checklist, prop=entity.id, character=character)
            times = [f * shot.duration for f in at]
            try:
                shown = frames(project, shot.id, times)
                reply = judge(shown, prompt=prompt)
            except Exception as e:  # noqa: BLE001 - configured and broken is a failure, said aloud
                report.findings.append(
                    ("error", where, f"the body critic could not judge prop {entity.id!r}: {type(e).__name__}: {e}")
                )
                continue
            report.calls.append({"shot": shot.id, "prop": entity.id, "frames": len(shown), "model": model})
            answers = parse_answers(reply, checklist)
            if answers is None:
                report.findings.append(
                    ("error", where, f"the body critic's reply about prop {entity.id!r} held no answers: {reply[:200]!r}")
                )
                continue
            for q, a in zip(checklist, answers):
                text = q.text.format(prop=entity.id, character=character)
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
