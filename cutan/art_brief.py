"""What art a cut-out film needs, and how to ask an image generator for it.

Claude can draw for a production pack, but only by writing SVG: simple
geometric shapes in flat colours, which read as obviously computer-made. A
film looks far better with real art: pictures from a specialised image
generator (Midjourney, GPT-image, Flux, Ideogram, Recraft...) or photographs
and scans of drawings made on paper. This module is the one place that says
what each piece of art must contain to be usable, so the writer-facing skill
(``cutan-production-pack``, its ``references/art.md``), the pack checker
(:func:`cutan.pack.check_pack`, its note on an all-SVG pack) and the reelee
connector (its ``check this pack`` result) all say the same thing.

- :data:`ART_KINDS`: each kind of art (sky, far, mid and near plates, the view
  behind a car, a prop, a vehicle, a character reference sheet, character
  parts, a costume), with where it goes in a pack, its canvas, its background
  and what it must and must not show.
- :func:`style_look`: a named style's look in words, for a prompt (the
  ``guidance.image_prompt`` of its spec in ``cutan/styles/``; never a show's
  name).
- :func:`image_prompt`: a ready-to-paste prompt for one kind, subject and look.
- :func:`art_guidance`: all of it as JSON-ready data.

>>> sorted(ART_KINDS)[:3]
['character_parts', 'character_sheet', 'costume']
>>> print(image_prompt("prop", "a red umbrella, closed", style="south_park"))  # doctest: +NORMALIZE_WHITESPACE
a red umbrella, closed. A single object, whole and centred, filling a square frame,
seen from the angle it is used at, nothing else in the picture, isolated on a plain
flat white background, no cast shadow, no text. Look: construction-paper cut-out
look, simple round and geometric shapes, flat solid colours, thin near-black
outlines, faint paper grain, no shading, no gradients, no perspective.
>>> image_prompt("sky", "a summer evening", tool="midjourney").endswith("--ar 16:9 --no text, letters, watermark, people")
True
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass

__all__ = [
    "ART_KINDS",
    "ArtKind",
    "CLAUDE_SVG_NOTE",
    "GENERATOR_TIPS",
    "PAPER_DRAWINGS",
    "RASTER_SUFFIXES",
    "SVG_ONLY_NOTE",
    "art_guidance",
    "image_prompt",
    "style_look",
]

#: The picture formats a plate, a prop part or a character part may be (an#211).
RASTER_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp")

#: What Claude tells the writer before it draws anything itself.
CLAUDE_SVG_NOTE = (
    "I can draw the art for you, but only as SVG: shapes I write as code. The "
    "result is simple geometry in flat colours (circles, rectangles, smooth "
    "curves), clean but very obviously computer-generated: no texture, no "
    "brush or pencil line, little detail, stiff faces. It is fine for a "
    "placeholder, a map, a title card or a deliberately flat look. For a film "
    "that looks drawn, use a specialised image generator (Midjourney, "
    "ChatGPT's image tool, Flux, Ideogram, Recraft) or photograph or scan "
    "drawings made on paper, and give me the pictures: I will say what each "
    "one must show, and write the prompts."
)

#: The checker's note on a pack whose drawings are all hand-written SVG.
SVG_ONLY_NOTE = (
    "every drawing in this pack is hand-written SVG ({n} file(s)): it will look "
    "computer-generated (simple shapes, flat colours). Tell the writer, and "
    "offer real art instead: pictures from an image generator or photos and "
    "scans of paper drawings, as PNG (transparent background for props and "
    "parts) or JPEG (opaque plates). What each picture must show, and prompts "
    "to paste into a generator: the skill's references/art.md "
    "(cutan.art_brief.art_guidance())."
)

#: How to photograph or scan drawings made on paper so they can be cut out.
PAPER_DRAWINGS = (
    "Draw each piece on its own sheet, or spread pieces out with a hand's width "
    "of empty paper between them.",
    "Use plain white or pale paper, and a background colour that appears nowhere "
    "in the drawing; strong, closed outlines cut out cleanest.",
    "Scan at 300 dpi, or photograph straight down in even daylight: no shadow of "
    "the phone or the hand, no glare, no perspective, the sheet filling the frame.",
    "Cut-paper pieces (actual scissors and card) are welcome: photograph them "
    "flat on a contrasting background.",
    "Send the original files (PNG or JPEG), not screenshots; the pipeline owner "
    "cuts the pieces out (cutan.carve) and keeps who drew them and on what terms.",
)

#: Per image generator: how to get usable art out of it.
GENERATOR_TIPS = {
    "midjourney": "append the aspect (--ar 16:9 for a plate, --ar 1:1 for a prop) and "
    "--no text, letters, watermark; it cannot make a transparent background, so ask "
    "for a plain flat white one; keep a character consistent with a reference image "
    "(--oref <image URL> in V7, --cref in V6)",
    "gpt-image": "ChatGPT's image tool (gpt-image): write the prompt as plain sentences; "
    "it can make a transparent PNG when asked ('transparent background, PNG'); ask "
    "for edits of the same image to keep a character consistent",
    "flux": "no negative prompt, and naming a thing tends to add it: use the "
    "positive-only prompt (image_prompt(..., tool='flux') drops the 'no ...' words); "
    "give the size as an aspect (16:9, 1:1); a flat plain background, cut out afterwards",
    "ideogram": "good at following a long description; switch magic prompt off so "
    "your words stay yours; ask for no text in the image",
    "recraft": "can draw in a vector style and export SVG, which suits the flat looks "
    "(South Park-like, OverSimplified-like, Kurzgesagt-like); an SVG it exports must "
    "still follow the pack's SVG rules (no embedded images)",
}

#: The negative words every prompt ends with (Midjourney's --no).
_NO = "text, letters, watermark"


@dataclass(frozen=True)
class ArtKind:
    """One kind of art a production pack can carry."""

    key: str
    title: str
    #: Where the file goes in the pack.
    goes_to: str
    #: Size and aspect, at the default 1280x720 frame.
    canvas: str
    #: ``"opaque"`` or ``"transparent"`` (or a plain flat colour cut out afterwards).
    background: str
    #: What the picture must show, and must not.
    content: tuple[str, ...]
    #: The words a generator prompt adds after the subject.
    framing: str
    #: Midjourney's ``--ar`` for it.
    aspect: str
    #: Who turns the picture into film: ``"ready"`` (the pack uses it as it is) or
    #: what the pipeline owner still has to do with it.
    status: str = "ready"
    #: Whether the subject is a person or creature (no ``people`` in --no).
    has_figures: bool = False


_PLATE_FILES = "assets/environments/<set>/plates/<layer>.png (or .jpg; an image plane in meta.json)"

ART_KINDS: dict[str, ArtKind] = {
    k.key: k
    for k in (
        ArtKind(
            key="sky",
            title="Sky (the farthest plate)",
            goes_to=_PLATE_FILES,
            canvas="16:9, at least 1920x1080; the camera barely moves it (depth 0 to 0.2)",
            background="opaque",
            content=(
                "sky only: its colours, clouds, sun or moon, stars",
                "no ground, buildings or horizon objects: those are the next layers",
            ),
            framing="An empty sky filling the whole frame, no ground, no horizon, "
            "no buildings, no people, no text",
            aspect="16:9",
        ),
        ArtKind(
            key="far",
            title="Far layer (distant hills, skyline, sea)",
            goes_to=_PLATE_FILES,
            canvas="wide: about 2560x1080 (21:9), wider still when the camera pans; "
            "parallax depth about 0.4",
            background="transparent above its top edge, so the sky shows through "
            "(or a plain flat colour there, cut out afterwards)",
            content=(
                "only what is far away, as one band across the whole width",
                "the horizon at the same height from left to right",
        ),
            framing="A wide horizontal band of distant scenery across the whole "
            "width, horizon level and at the same height throughout, nothing in the "
            "foreground, no people, empty plain flat white sky above it, no text",
            aspect="21:9",
            status="ready if its background is transparent; a flat background is "
            "cut out by the pipeline owner first (cutan.carve)",
        ),
        ArtKind(
            key="mid",
            title="Mid layer (the set the characters stand in)",
            goes_to=_PLATE_FILES,
            canvas="wide: about 2560x1080 (21:9), enough to cover the frame and the "
            "camera's pan; depth 1 (moves with the characters)",
            background="transparent where the far layer and sky should show",
            content=(
                "the street, room or landscape the characters stand in, at their scale",
                "the floor line about three-quarters of the way down",
                "the middle third left quiet: the characters stand and talk there",
                "no characters in it",
        ),
            framing="A stage-like set seen straight on at eye level, the floor line "
            "three-quarters of the way down, the centre left open and uncluttered for "
            "characters, no people, no animals, no text",
            aspect="21:9",
            status="ready if its background is transparent; a flat background is "
            "cut out by the pipeline owner first (cutan.carve)",
        ),
        ArtKind(
            key="near",
            title="Near layer (foreground in front of the characters)",
            goes_to=_PLATE_FILES + "; listed after the environment's characters_after plane",
            canvas="the frame's width or wider (16:9 or 21:9)",
            background="transparent everywhere except the foreground object",
            content=(
                "what is in front of the characters: a railing, a bush, a counter, "
                "a car's dashboard and window frames",
                "kept to the edges and bottom of the frame so it does not hide faces",
        ),
            framing="A foreground element along the bottom edge of the frame, the "
            "rest of the picture plain flat white and empty, seen straight on, no "
            "people, no text",
            aspect="16:9",
            status="ready if its background is transparent; a flat background is "
            "cut out by the pipeline owner first (cutan.carve)",
        ),
        ArtKind(
            key="window_view",
            title="The view behind a car (or a train, a moving window)",
            goes_to=_PLATE_FILES + "; its own plate, behind the vehicle's interior plate",
            canvas="a long strip, 3 to 4 frames wide (about 5000x1080), so it can "
            "scroll past the windows for the whole shot",
            background="opaque",
            content=(
                "only the landscape or road seen through the windows: no car parts, "
                "no window frame, no reflections",
                "the horizon at one height along the whole strip; ideally the left "
                "and right ends join so it can loop",
                "the car's interior (seats, dashboard, window frames with the glass "
                "left empty) is a separate near-layer picture",
            ),
            framing="A very wide panoramic strip of roadside landscape seen side-on "
            "from a moving car, horizon level at one height throughout, no car parts, "
            "no window frame, no people, no text",
            aspect="4:1",
        ),
        ArtKind(
            key="prop",
            title="A prop (any object a scene shows)",
            goes_to="assets/props/<prop>/parts/<prop>.png (in prop.json's skin)",
            canvas="square, 1024x1024; the object fills the square",
            background="transparent (or a plain flat white, cut out afterwards)",
            content=(
                "one object per picture, whole, not cropped",
                "seen from the angle the scene shows it",
                "no cast shadow on a floor, no hands holding it",
                "moving pieces (a lid, a door) as separate pictures",
        ),
            framing="A single object, whole and centred, filling a square frame, seen "
            "from the angle it is used at, nothing else in the picture, isolated on a "
            "plain flat white background, no cast shadow, no text",
            aspect="1:1",
            status="ready if its background is transparent; a flat background is "
            "cut out by the pipeline owner first (cutan.carve)",
        ),
        ArtKind(
            key="vehicle",
            title="A vehicle seen from outside (a car in three-quarter view)",
            goes_to="assets/props/<car>/parts/<car>.png",
            canvas="square, 1024x1024, like any prop; the car fills the width, the space above it empty",
            background="transparent (or a plain flat white, cut out afterwards)",
            content=(
                "the whole vehicle in three-quarter front view, wheels on one level line",
                "nobody inside: windows dark or empty, so characters can be placed",
                "wheels that must turn as separate pictures, seen at the same angle",
        ),
            framing="A whole car in three-quarter front view, filling the width of a "
            "square frame, wheels level, nobody inside, isolated on a plain flat white "
            "background, no road, no cast shadow, no text",
            aspect="1:1",
            status="ready if its background is transparent; a flat background is "
            "cut out by the pipeline owner first (cutan.carve)",
        ),
        ArtKind(
            key="character_sheet",
            title="A character reference sheet",
            goes_to="reference/<name>-sheet.png (a folder the scene does not use; PRODUCTION.md lists it)",
            canvas="landscape, about 3000x1500, the views side by side",
            background="plain flat white",
            content=(
                "the same character in front, three-quarter, side and back views, "
                "full body, at the same scale and in the same light",
                "standing straight, arms hanging a little away from the body, legs a "
                "little apart, so each limb can be cut out",
                "a face sheet on its own: eyes open and closed, and the mouth shapes "
                "(closed, slightly open, wide open, O, E, F/V, M/B/P, L, rest)",
                "no text labels, no props in the hands",
            ),
            framing="A character turnaround sheet: front, three-quarter, side and back "
            "views side by side, full body, same scale and lighting in every view, "
            "standing straight with arms slightly away from the body and legs slightly "
            "apart, plain flat white background, no text, no labels",
            aspect="2:1",
            status="the pipeline owner cuts it into parts (cutan.carve) and rigs it by "
            "hand: allow for that work (cutan#92)",
            has_figures=True,
        ),
        ArtKind(
            key="character_parts",
            title="Character parts (a puppet in pieces)",
            goes_to="reference/<name>-parts/<part>.png; the pipeline owner builds the "
            "art package from them (`an character contract`)",
            canvas="each part on its own canvas, all at the same scale",
            background="transparent",
            content=(
                "head (no eyes or mouth drawn on it), torso, each arm, each leg; eyes "
                "open and closed; nine mouth shapes",
                "each limb with a little extra at the joint so the pieces overlap",
                "a redrawn part of a factory character must be SVG for now (cutan#92)",
            ),
            framing="A single body part of a cut-out puppet, isolated on a plain flat "
            "white background, flat even lighting, no text",
            aspect="1:1",
            status="the pipeline owner assembles the art package (character.json)",
            has_figures=True,
        ),
        ArtKind(
            key="costume",
            title="A costume",
            goes_to="reference/<name>-costume.png, or on the reference sheet; colours in PRODUCTION.md",
            canvas="as the reference sheet, or close-ups at 1024x1024",
            background="plain flat white",
            content=(
                "for a factory character: the colours by name or hex for the "
                "clothing, accessory and legs (the cast line's --palette)",
                "for a drawn character: the costume on the reference sheet, with "
                "close-ups of a hat, a pattern or a badge",
                "a costume change is a second reference sheet",
            ),
            framing="A costume design sheet: the outfit laid out flat from the front, "
            "with close-ups of its details, plain flat white background, no text",
            aspect="1:1",
            status="the pipeline owner applies it",
        ),
    )
}


def style_look(style: str | Mapping | None) -> str:
    """A style's look in words, for a prompt (``guidance.image_prompt`` of its spec).

    ``style`` is a style's name, a spec mapping, or ``None`` (the writer's own look).

    >>> style_look("reiniger").startswith("black paper silhouette")
    True
    >>> style_look(None)
    '<your look in words: medium, colours, line, texture>'
    """
    if style is None:
        return "<your look in words: medium, colours, line, texture>"
    from cutan.styles import resolve_style_spec

    spec = resolve_style_spec(style)
    look = (spec.get("guidance") or {}).get("image_prompt")
    if not look:
        raise KeyError(f"style {spec.get('style')!r} has no guidance.image_prompt")
    return str(look)


def image_prompt(
    kind: str,
    subject: str,
    *,
    style: str | Mapping | None = None,
    tool: str | None = None,
) -> str:
    """A prompt to paste into an image generator for one piece of art.

    kind: a key of :data:`ART_KINDS`
    subject: what the picture is of, in the writer's words
    style: a style name or spec (its look in words), or ``None`` for a placeholder
    tool: ``"midjourney"`` appends its ``--ar`` and ``--no`` flags; ``"flux"``
        drops the ``no ...`` words; any other tool takes the plain prompt (see
        :data:`GENERATOR_TIPS`)
    """
    if kind not in ART_KINDS:
        raise KeyError(f"no art kind {kind!r}; the kinds are: {', '.join(ART_KINDS)}")
    k = ART_KINDS[kind]
    framing, look = k.framing, style_look(style)
    if tool == "flux":  # naming what is unwanted tends to add it
        framing, look = _positive(framing), _positive(look)
    text = f"{subject.strip().rstrip('.')}. {framing}. Look: {look}."
    if tool == "midjourney":
        no = _NO if k.has_figures else f"{_NO}, people"
        text += f" --ar {k.aspect} --no {no}"
    return text


def _positive(words: str) -> str:
    """``words`` without its ``no ...`` clauses.

    >>> _positive("a sky, no ground, no text, soft light")
    'a sky, soft light'
    """
    return ", ".join(c for c in words.split(", ") if not c.lower().startswith(("no ", "nothing ")))


def art_guidance(*, style: str | Mapping | None = None) -> dict:
    """Everything a writer's Claude needs to ask for real art, as JSON-ready data.

    A prompt is ``prompt_recipe``: the subject, the kind's ``framing``, the ``look``.

    >>> g = art_guidance(style="norstein")
    >>> sorted(g)
    ['claude_svg', 'formats', 'generators', 'kinds', 'look', 'paper_drawings', 'prompt_recipe']
    >>> g["kinds"][0]["key"], g["look"].startswith("painted multiplane")
    ('sky', True)
    """
    look = style_look(style)
    kinds = []
    for k in ART_KINDS.values():
        row = asdict(k)
        row["content"] = list(k.content)
        kinds.append(row)
    return {
        "claude_svg": CLAUDE_SVG_NOTE,
        "look": look,
        "prompt_recipe": "<subject in the writer's words>. <the kind's framing>. Look: "
        "<look>. Never a show's, studio's or artist's name. Midjourney: add --ar "
        "<the kind's aspect> --no text, letters, watermark.",
        "formats": "PNG (transparent background where a kind says so), JPEG or WebP "
        "for an opaque plate; SVG from a vector tool if it follows the pack's SVG "
        "rules. Not PSD, HEIC, PDF or AI. Original files, not screenshots.",
        "kinds": kinds,
        "paper_drawings": list(PAPER_DRAWINGS),
        "generators": dict(GENERATOR_TIPS),
    }
