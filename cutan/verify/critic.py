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
from pathlib import Path
from typing import Any, Union

from cutan.body_attachment import FIRST_PERSON, body_attachment_of, bound_character
from cutan.verify.body import Finding, declaring_props

__all__ = [
    "CHECKLISTS",
    "Question",
    "CritiqueReport",
    "critique_body_props",
    "critique_far_plates",
    "FAR_PLATE_CHECKLIST",
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
        Question(
            "Is the face of the person holding the {prop} visible in the picture?", "no"
        ),
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


_LEADING_ANSWER = re.compile(r"^\W*(yes|no)\b(?!\s*/)", re.I)


def parse_answers(
    reply: str, checklist: Sequence[Question]
) -> list[dict[str, Any]] | None:
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
    for position, item in enumerate(raw, 1):
        if not isinstance(item, dict):
            continue
        n = item.get("n", position)  # an unnumbered answer is read by its place
        n = int(n) if isinstance(n, str) and n.strip().isdigit() else n
        if not isinstance(n, int) or isinstance(n, bool):
            continue
        if not 1 <= n <= len(checklist):
            return None  # numbered from 0, or past the end: the answers would shift
        m = _LEADING_ANSWER.match(str(item.get("answer", "")))
        by_n[n] = {
            "n": n,
            "answer": m.group(1).lower() if m else "unsure",
            "why": str(item.get("why", "")),
        }
    if not by_n:
        return None
    return [
        by_n.get(n, {"n": n, "answer": "unsure", "why": ""})
        for n in range(1, len(checklist) + 1)
    ]


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
        return judge_envelope(
            frames, prompt=prompt, **({"model": model} if model else {})
        )

    return judge


class _Fill(dict):
    """``str.format_map`` filling: an unknown ``{name}`` stays as written."""

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def _checked_default_judge(model: str | None, report: CritiqueReport, label: str):
    """The default judge, or ``None`` with an error finding when its SDK is missing."""
    try:
        import anthropic  # noqa: F401 - the default judge's SDK, checked before paying
    except ImportError:
        report.findings.append(
            (
                "error",
                "",
                f"the {label}'s default judge needs the anthropic SDK: pip install an[vision]",
            )
        )
        return None
    return _envelope_judge(model)


def _ask(
    report: CritiqueReport,
    *,
    judge: Callable[..., Union[str, Mapping[str, Any]]],
    images: Callable[[], Sequence[bytes]],
    prompt: str,
    checklist: Sequence[Question],
    fill: Mapping[str, str],
    where: str,
    call: Mapping[str, Any],
    model: str | None,
    label: str,
    subject: str,
    context: str,
    advice: str,
) -> None:
    """Show ``images()`` to ``judge`` with ``prompt``; record the call and add a
    finding per answer that differs from ``checklist``'s (a configured judge
    that fails, or a reply with no answers, is an ``error``)."""
    try:
        shown = images()
        if not shown:
            raise ValueError("there is no image to show")
        answer = judge(shown, prompt=prompt)
    except Exception as e:  # noqa: BLE001 - configured and broken is a failure, said aloud
        report.findings.append(
            (
                "error",
                where,
                f"the {label} could not judge {subject}: {type(e).__name__}: {e}",
            )
        )
        return
    reply = str((answer.get("reply") if isinstance(answer, Mapping) else answer) or "")
    used = answer.get("model") if isinstance(answer, Mapping) else model
    report.calls.append({**call, "frames": len(shown), "model": used})
    answers = parse_answers(reply, checklist)
    if answers is None:
        report.findings.append(
            (
                "error",
                where,
                f"the {label}'s reply about {subject} held no answers: {reply[:200]!r}",
            )
        )
        return
    for q, a in zip(checklist, answers):
        text = q.text.format_map(_Fill(fill))
        if a["answer"] == "unsure":
            report.findings.append(("info", where, f"{label}, unsure: {text}"))
        elif a["answer"] != q.expected:
            report.findings.append(
                (
                    "warning",
                    where,
                    f"{label} ({context}, a vision model, not a measurement): "
                    f"{text} {a['answer']}, expected {q.expected}"
                    + (f" ({a['why']})" if a["why"] else "")
                    + f". {advice}",
                )
            )


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
        raise ValueError(
            f"`at` holds fractions of a shot's length in [0, 1], not {list(at)}"
        )
    report = CritiqueReport()
    custom = judge is not None
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
            if (char_entity is None) != (ba.view == FIRST_PERSON):
                # nobody on screen for the arms to belong to, or a first-person
                # prop with its own body in view: the body check reports both
                continue
            checklist = checklist_for(ba.view, checklists)
            if not checklist:
                continue
            prop = entity.ref or entity.id  # "wheel", not the entity's id
            prompt = checklist_prompt(
                checklist, prop=prop, character=character or "the character"
            )
            if judge is None:
                judge = _checked_default_judge(model, report, "body critic")
                if judge is None:
                    return report

            def probe(shot=shot):
                nonlocal shown
                if shown is None:
                    shown = frames(project, shot.id, [f * shot.duration for f in at])
                if not shown:
                    raise ValueError(f"the probe of shot {shot.id!r} gave no frames")
                return shown

            _ask(
                report,
                judge=judge,
                images=probe,
                prompt=prompt,
                checklist=checklist,
                fill={"prop": prop, "character": character or "the character"},
                where=where,
                call={"shot": shot.id, "prop": entity.id},
                model=None if custom else model,
                label="body critic",
                subject=f"prop {entity.id!r}",
                context=f"shot {shot.id!r}",
                advice="Check the drawing: the hands may be drawn from another point of view.",
            )
    return report


#: What a ``far`` plate of a travelling shot must not hold (ADR 0007 of ``an``):
#: anything nearer than the far range stands still while the streams move.
FAR_PLATE_CHECKLIST: tuple[Question, ...] = (
    Question("Does the picture show the ground or a road close to the viewer?", "no"),
    Question(
        "Are there trees, poles, fences, signs or buildings near the viewer: large, "
        "or cut off by the picture's edges?",
        "no",
    ),
    Question(
        "Is everything shown far away: sky, horizon, distant hills or mountains?", "yes"
    ),
)

_PLATE_PROMPT = """You are checking a background picture for a cut-out animated film. It
is shown through a moving vehicle's window as the far distance, so it must hold
only what is very far away; anything near would stand still while the nearby
scenery streams past. Answer each question from what is visible, "yes", "no"
or "unsure", with a few words why. Reply with JSON only:
{{"answers": [{{"n": 1, "answer": "yes", "why": "..."}}, ...]}}

{questions}
"""
#: A plate is shown at most this many pixels on its longer side (the judge needs
#: no more, and an image costs by its pixels).
PLATE_MAX_SIDE: int = 1024


#: What a plate's transparent parts are shown on: a neutral mid grey, since how
#: a vision model reads transparency is undefined.
PLATE_MATTE: tuple[int, int, int] = (128, 128, 128)


def _plate_png(path: Any, *, max_side: int = PLATE_MAX_SIDE) -> bytes:
    """A raster plate as RGB PNG bytes, at most ``max_side`` pixels long, its
    transparency flattened onto :data:`PLATE_MATTE`."""
    import io

    from PIL import Image

    with Image.open(path) as im:
        rgba = im.convert("RGBA")
        rgba.thumbnail((max_side, max_side))
        flat = Image.new("RGB", rgba.size, PLATE_MATTE)
        flat.paste(rgba, mask=rgba.getchannel("A"))
        buf = io.BytesIO()
        flat.save(buf, format="PNG")
    return buf.getvalue()


def _far_plates(project: Any) -> list[tuple[str, str, Any, str]]:
    """``(where, "member/plane", plate path or None, why not)`` of each plane a
    travel lists ``far``; the path is ``None`` (and ``why not`` says why) when
    the plane has no image (a fill, a gradient), its member is not an
    environment, or its file cannot be read inside its environment's folder."""
    from an.ir.migrate import migrate
    from an.stage.environments import ENVIRONMENT_DOCUMENT_KIND, EnvironmentDescriptor
    from an.stores._common import inside_folder

    world = getattr(project.scene, "world", None)
    travel = getattr(world, "travel", None) if world is not None else None
    if travel is None:
        return []
    env_store = project.mall.get("environments")
    root = getattr(env_store, "_root", None)
    members = {m.id: m for m in world.members}
    out = []
    for k, name in enumerate(travel.plates.get("far", ())):
        member_id, _, plane_name = name.partition("/")
        member = members.get(member_id)
        where = f"world/travel/plates/far/{k}"
        path, why = None, "its file cannot be read in its environment's folder"
        if member is None or member.kind != "environment" or root is None:
            why = (
                "it is not a plane of an environment in the world"
                if root is not None
                else "the environments store has no folder"
            )
            out.append((where, name, None, why))
            continue
        try:
            raw = env_store[member.ref]
            env = EnvironmentDescriptor.model_validate(
                migrate(dict(raw), kind=ENVIRONMENT_DOCUMENT_KIND.name)
            )
            plane = next(p for p in env.planes if p.name == plane_name)
            if plane.art.kind != "image" or not plane.art.src:
                why = f"it is a {plane.art.kind}, not a picture"
            else:
                path = inside_folder(Path(root) / str(member.ref), plane.art.src)
        except StopIteration:
            why = "its environment has no such plane"
        except Exception:  # noqa: BLE001 - a malformed environment is another check's to report
            path = None
        out.append((where, name, path, why))
    return out


def critique_far_plates(
    project: Any,
    *,
    judge: Callable[..., Union[str, Mapping[str, Any]]] | None = None,
    checklist: Sequence[Question] = FAR_PLATE_CHECKLIST,
    model: str | None = None,
    max_side: int = PLATE_MAX_SIDE,
) -> CritiqueReport:
    """Ask whether each ``far`` plate of ``project``'s travel holds anything near
    (cutan#166): a tree baked into a plate stands still while the streams move.

    The plate's own image is judged, not a render: no probe, one call per plate
    (at most ``max_side`` px long; a plane's ``fit`` never crops, so the image
    holds everything a pan could show). An SVG plate (drawn by hand, its content
    known to its author) and a plane with no picture are not judged, each said
    as an ``info``. Only the plates a travel LISTS ``far`` are judged; a plane at
    infinity because its frame is coupled ``far`` is not yet (cutan#177).
    Findings and calls as :func:`critique_body_props`.
    """
    from an.project import load

    project = load(project) if not hasattr(project, "scene") else project
    report = CritiqueReport()
    custom = judge is not None
    for where, name, path, why in _far_plates(project):
        if path is None or Path(path).suffix.lower() == ".svg":
            reason = "it is an SVG, drawn by hand" if path is not None else why
            report.findings.append(
                ("info", where, f"far plate {name!r} not judged: {reason}")
            )
            continue
        if judge is None:
            judge = _checked_default_judge(model, report, "far-plate critic")
            if judge is None:
                return report
        questions = "\n".join(f"{n}. {q.text}" for n, q in enumerate(checklist, 1))
        _ask(
            report,
            judge=judge,
            images=lambda path=path: [_plate_png(path, max_side=max_side)],
            prompt=_PLATE_PROMPT.format(questions=questions),
            checklist=checklist,
            fill={},
            where=where,
            call={"plate": name},
            model=None if custom else model,
            label="far-plate critic",
            subject=f"plate {name!r}",
            context=f"plate {name!r}",
            advice=(
                "A plate the travel lists `far` must hold only what is at infinity: "
                "move what is near to a stream, or onto a `vehicle` plate."
            ),
        )
    return report
