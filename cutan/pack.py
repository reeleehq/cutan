"""Check a cut-out production pack with cutan's own validators (cutan#87).

A production pack (the ``cutan-production-pack`` skill, cutan#86) is a folder
shaped like an ``an`` project: ``scene.md``, ``cast.sh`` (one ``an character
...`` command per line), ``assets/`` (environments, props, voices, styles,
optional redrawn character parts) and ``PRODUCTION.md``. :func:`check_pack`
builds a throwaway project from it and runs the real checks:

1. lint every SVG drawing in the pack (root tag, size, forbidden elements,
   outside links), check that every picture (PNG, JPEG, WebP: plates, prop
   parts, reference sheets) is one, and the keys of every voice document;
2. ``an init`` a scratch project and copy the pack over it, except redrawn
   character parts (a character folder with no ``character.json``);
3. run each ``cast.sh`` line, refusing anything but the factory commands and
   options the skill documents (no shell: the line is split and run directly);
4. copy the redrawn parts over the factory's (same file names, same root tag),
   check the voice documents with the engine's own checks, then ``an character
   validate`` every character and ``an props validate`` every drawn prop;
5. ``an validate --strict-assets`` the scene.

A step fails on an error in its output, not only on its exit status (the
``an`` commands exit 0 on some failures). The result is a :class:`PackReport`:
one :class:`PackCheck` per step, each with its errors and warnings, so a caller
(the skill's ``validate_pack.py``, the reelee connector's ``check this pack``
tool) can print it or return it as data (:meth:`PackReport.to_dict`). A pack
that cannot be checked at all (no ``scene.md``, a refused ``cast.sh`` line) is
a report with one failed ``pack`` check, never an exception. Its ``notes`` say
what is neither an error nor a warning: a pack whose drawings are all
hand-written SVG gets one, since such art looks computer-made
(:mod:`cutan.art_brief` says what to ask for instead).

Nothing is rendered: no browser, no network (``an character new`` must say
``--offline``), no paid call.

>>> report = check_pack("/no/such/pack")
>>> report.ok, report.summary()
(False, 'FAIL: 0/1 checks passed, 0 warning(s)')
>>> report.errors
['pack: pack has no scene.md: is it a production pack?']
"""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path

from an.ir.validate import _asset_references
from an.stage.raster import is_svg_content, svg_problems
from an.stores._common import inside_folder

__all__ = [
    "PackCheck",
    "PackError",
    "PackReport",
    "cast_commands",
    "check_pack",
    "lint_svg",
    "main",
    "pack_art_guidance",
    "svg_only_art",
]

CAST_FILE = "cast.sh"
PACK_ONLY_FILES = (CAST_FILE,)
NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,40}$")
#: Per `an character` subcommand: the options a pack may pass (value-taking
#: ones map to True, flags to False). Anything else is refused: `--out-dir`,
#: `--overwrite` and a network fetch (no `--offline`) never reach the factory.
CAST_OPTIONS = {
    "new": {
        "--offline": False,
        "--build": True,
        "--head-scale": True,
        "--hat": True,
        "--hair-style": True,
        "--hair-length": True,
        "--sash": False,
        "--palette": True,
        "--mouth-variants": True,
        "--no-views": False,
        "--voice-ref": True,
    },
    "mouths": {"--variants": True},
    "add-half-lid": {"--fraction": True},
    "add-views": {},
    "add-gaze": {},
}
#: What each cast subcommand prints when it worked (the `an` commands exit 0 on failure).
CAST_SUCCESS = {
    "new": "created character",
    "mouths": "wrote ",
    "add-half-lid": "added a HALF eyelid",
    "add-views": "added the views",
    "add-gaze": "added the eye stack",
}
ERROR_MARKER = "[error]"
WARNING_MARKER = "[warning]"
FAILURE_MARKERS = (ERROR_MARKER, "FAILED", "Traceback (most recent call last)")
#: Factory notes that carry no `[warning]` marker but are one.
NOTE_MARKERS = ("covers the brows",)
#: The keys a pack's voice document may carry. ``notes`` (the voice in words: age,
#: accent, pitch, pace, attitude) and ``sample_text`` (what a designed voice's
#: samples say) are what ``an voices design`` designs options from; the engine
#: ignores both when it speaks.
VOICE_KEYS = frozenset(
    {
        "provider",
        "voice_id",
        "model_id",
        "voice_settings",
        "seed",
        "effects",
        "takes",
        "loudness_offset_db",
        "notes",
        "sample_text",
    }
)
#: The voice-design text keys and their lengths (ElevenLabs Voice Design's bounds,
#: as ``an.audio.voice_design`` checks them).
TEXT_KEY_LENGTHS = {"notes": (20, 1000), "sample_text": (100, 1000)}
VOICE_MODELS = frozenset(
    {
        "eleven_v3",
        "eleven_v4",
        "eleven_v4_turbo",
        "eleven_v3_conversational",
        "eleven_multilingual_v2",
        "eleven_turbo_v2_5",
    }
)
#: Run by the interpreter that runs `an`: the engine's own voice checks, one
#: `[error]` line per problem.
VOICE_CHECK = """
import json, sys
from pathlib import Path
from an.audio.effects import voice_effects
from an.audio.elevenlabs_tts import ElevenLabsTTS
from an.audio.loudness import _offset
voices = {p.stem: json.loads(p.read_text()) for p in sorted(Path(sys.argv[1]).glob('*.json'))}
mall = {'voices': voices}
for key, doc in voices.items():
    checks = [lambda: voice_effects(mall, key), lambda: _offset(mall, key)]
    if doc.get('provider') == 'elevenlabs':
        checks.append(lambda: ElevenLabsTTS(api_key='never-called').synthesis_options(doc, emotion=None, direction=None))
    for check in checks:
        try:
            check()
        except Exception as e:
            print(f'  [error] voices/{key}.json: {e}')
"""
SVG_NS = "{http://www.w3.org/2000/svg}"
SVG_SHAPES = frozenset(
    {"path", "rect", "circle", "ellipse", "polygon", "polyline", "line", "text", "use"}
)
#: Seconds one step (one `an` command) may run before it counts as failed.
DFLT_STEP_TIMEOUT = 300.0
#: Seconds the whole check may run; past it, the remaining steps are not run.
DFLT_DEADLINE = 900.0
#: The text files a pack may hold (exact, lower-case suffixes).
TEXT_SUFFIXES = frozenset({".md", ".sh", ".json", ".svg", ".txt", ".yaml", ".yml"})
#: The pictures a pack may hold: plates, prop parts, reference sheets (an#211). Each
#: must start with its format's signature; nothing else is copied: no code, no audio.
IMAGE_SIGNATURES = {
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".webp": (b"RIFF",),
}
PACK_SUFFIXES = TEXT_SUFFIXES | frozenset(IMAGE_SIGNATURES)
#: The largest picture a pack may hold, in bytes, and in pixels (from its header).
MAX_IMAGE_BYTES = 40 * 1024 * 1024
MAX_IMAGE_PIXELS = 50_000_000
#: Where a pack's drawings live (the art an all-SVG note counts).
ART_GLOBS = (
    "assets/environments/*/plates/**/*",
    "assets/props/*/parts/**/*",
    "assets/characters/*/parts/**/*",
)
#: Caps on the work one pack can ask for (each line or folder is one `an` process).
MAX_CAST_LINES = 100
MAX_ASSET_FOLDERS = 60
#: ``-P``: the child does not put its working directory (the scratch project,
#: which holds the pack's files) first on ``sys.path`` (Python 3.11+; on 3.10
#: only :data:`PACK_SUFFIXES` keeps code out).
_NO_CWD_PATH: tuple[str, ...] = ("-P",) if sys.version_info >= (3, 11) else ()
#: How `an` is run by default: the interpreter running this code, so the check
#: needs no `an` on PATH (a service's venv rarely puts its scripts there).
DFLT_AN_COMMAND: tuple[str, ...] = (sys.executable, *_NO_CWD_PATH, "-m", "an")
#: Environment variables a check's children never see (a server's keys).
_SECRET_ENV = re.compile(r"KEY|SECRET|TOKEN|PASSW|CREDENTIAL|^AWS_|PRIVATE", re.I)
_ABS_PATH = re.compile(r"(?<![\w.])/(?:[\w.@+-]+/)+[\w.@+-]*")


class PackError(Exception):
    """A pack that cannot be checked at all (a missing file, a refused line)."""


@dataclass(frozen=True)
class PackCheck:
    """One step of a pack check: its label, its verdict and what it printed."""

    label: str
    ok: bool
    output: str = ""

    @property
    def errors(self) -> list[str]:
        """The step's error lines (its whole output when it failed silently).

        >>> PackCheck("x", False, "  [error] bad\\nfine").errors
        ['bad']
        >>> PackCheck("x", False, "exit 2").errors
        ['exit 2']
        """
        found = [
            _strip_marker(ln, ERROR_MARKER)
            for ln in _lines_with(self.output, (ERROR_MARKER,))
        ]
        if not self.ok and not found:
            last = [ln.strip() for ln in self.output.splitlines() if ln.strip()]
            found = [last[-1][:300] if last else "failed with no output"]
        return found

    @property
    def warnings(self) -> list[str]:
        """The step's warning lines (a factory note counts as one)."""
        return [
            _strip_marker(ln, WARNING_MARKER)
            for ln in _lines_with(self.output, (WARNING_MARKER, *NOTE_MARKERS))
        ]


@dataclass
class PackReport:
    """Every step of a pack check, in order."""

    checks: list[PackCheck] = field(default_factory=list)
    #: Information for the writer that is neither an error nor a warning (it
    #: never fails a check): e.g. that every drawing is hand-written SVG.
    notes: list[str] = field(default_factory=list)

    def add(self, label: str, ok: bool, output: str = "") -> bool:
        self.checks.append(PackCheck(label, ok, output.strip()))
        return ok

    @property
    def ok(self) -> bool:
        return bool(self.checks) and all(c.ok for c in self.checks)

    @property
    def errors(self) -> list[str]:
        """``"<check>: <error>"`` for every error of every check."""
        return [f"{c.label}: {e}" for c in self.checks for e in c.errors]

    @property
    def warnings(self) -> list[str]:
        """``"<check>: <warning>"`` for every warning of every check."""
        return [f"{c.label}: {w}" for c in self.checks for w in c.warnings]

    def summary(self) -> str:
        """The one line a writer quotes in ``PRODUCTION.md``."""
        passed = sum(c.ok for c in self.checks)
        verdict = "PASS" if self.ok else "FAIL"
        return (
            f"{verdict}: {passed}/{len(self.checks)} checks passed, "
            f"{len(self.warnings)} warning(s)"
        )

    def to_dict(self, *, with_output: bool = False) -> dict:
        """The report as JSON-ready data (the output of each step on request)."""
        checks = [
            {
                "label": c.label,
                "ok": c.ok,
                "errors": c.errors,
                "warnings": c.warnings,
                **({"output": c.output} if with_output else {}),
            }
            for c in self.checks
        ]
        return {
            "ok": self.ok,
            "summary": self.summary(),
            "errors": self.errors,
            "warnings": self.warnings,
            "notes": list(self.notes),
            "checks": checks,
        }

    def format(self) -> str:
        """The full report as text: each step's verdict and output, then the summary."""
        parts = [
            f"=== {c.label} {'OK' if c.ok else 'FAILED'}"
            + (f"\n{c.output}" if c.output else "")
            for c in self.checks
        ]
        notes = [f"note: {n}" for n in self.notes]
        return "\n\n".join([*parts, *notes, self.summary()])


def _lines_with(text: str, markers: Sequence[str]) -> list[str]:
    return [ln.strip() for ln in text.splitlines() if any(m in ln for m in markers)]


def _strip_marker(line: str, marker: str) -> str:
    return line.replace(marker, "", 1).strip() if line.startswith(marker) else line


def cast_commands(pack: Path) -> list[list[str]]:
    """The ``an character`` commands of ``cast.sh``; raise :class:`PackError` on any other line.

    Blank lines and ``#`` comments are skipped; a trailing backslash continues
    a line.
    """
    path = Path(pack) / CAST_FILE
    if not path.exists():
        return []
    try:
        text = path.read_text(encoding="utf-8").replace("\\\n", " ")
    except (OSError, UnicodeDecodeError) as e:
        raise PackError(f"{CAST_FILE} cannot be read: {e}") from None
    commands = []
    for n, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            argv = shlex.split(line, comments=True)
        except ValueError as e:
            raise PackError(f"{CAST_FILE} line {n}: {e}: {line}") from None
        commands.append(_checked_cast_line(argv, n, line))
    return commands


def _checked_cast_line(argv: list[str], n: int, line: str) -> list[str]:
    def refuse(why: str) -> PackError:
        return PackError(f"{CAST_FILE} line {n}: {why}: {line}")

    if argv[:2] != ["an", "character"] or len(argv) < 4 or argv[2] not in CAST_OPTIONS:
        raise refuse(
            f"only `an character {{{'|'.join(CAST_OPTIONS)}}} <name> ...` is allowed"
        )
    sub, name, rest = argv[2], argv[3], argv[4:]
    if not NAME_RE.match(name):
        raise refuse(f"{name!r} is not a character name (lowercase letters, digits, _)")
    allowed = CAST_OPTIONS[sub]
    i = 0
    while i < len(rest):
        opt = rest[i]
        if opt not in allowed:
            raise refuse(
                f"option {opt!r} is not allowed here (allowed: {', '.join(allowed) or 'none'})"
            )
        i += 2 if allowed[opt] else 1
    if i != len(rest):
        raise refuse(f"option {rest[-1]!r} needs a value")
    if sub == "new" and "--offline" not in rest:
        raise refuse("`an character new` needs `--offline`")
    return argv


def lint_svg(path: Path, *, exact_size: bool) -> list[str]:
    """What is wrong with one SVG drawing (empty when nothing is)."""
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as e:
        return [f"not valid XML: {e}"]
    problems = []
    if root.tag not in (f"{SVG_NS}svg", "svg"):
        problems.append("the root element is not <svg>")
    if root.tag != f"{SVG_NS}svg":
        problems.append('missing xmlns="http://www.w3.org/2000/svg" on the root')
    box = (root.get("viewBox") or "").replace(",", " ").split()
    if len(box) != 4:
        problems.append("no viewBox")
    for dim in ("width", "height"):
        if root.get(dim) is None:
            problems.append(f"no {dim}")
    if exact_size and len(box) == 4 and root.get("width") and root.get("height"):
        try:
            if (float(root.get("width")), float(root.get("height"))) != (
                float(box[2]),
                float(box[3]),
            ):
                problems.append("width/height differ from the viewBox size")
        except ValueError:
            problems.append("width/height are not plain numbers")
    tags = {el.tag.replace(SVG_NS, "") for el in root.iter()}
    if not tags & SVG_SHAPES:
        problems.append("draws nothing (no shape element)")
    # Forbidden elements and links out of the file: the core's rule, so the two never drift.
    problems += svg_problems(root)
    return problems


def _child_env() -> dict[str, str]:
    """This process's environment minus anything that looks like a secret."""
    return {k: v for k, v in os.environ.items() if not _SECRET_ENV.search(k)}


def _redact(text: str, *, places: Sequence[tuple[str, str]]) -> str:
    """``text`` with the given places renamed and any other absolute path hidden.

    >>> _redact("at /tmp/x/project/a.svg and /etc/hostname", places=[("/tmp/x/project", "<project>")])
    'at <project>/a.svg and <path>'
    """
    for path, name in places:
        text = text.replace(path, name)
    return _ABS_PATH.sub("<path>", text)


def _lint_files(pack: Path, report: PackReport) -> None:
    """Refuse every file a pack must not hold (by exact suffix) and every symlink."""
    for src in sorted(pack.rglob("*")):
        rel = src.relative_to(pack).as_posix()
        if src.is_symlink():
            report.add(f"file {rel}", False, f"  {ERROR_MARKER} a link, not a file")
        elif src.is_file() and src.suffix not in PACK_SUFFIXES:
            report.add(
                f"file {rel}",
                False,
                f"  {ERROR_MARKER} a pack holds only {', '.join(sorted(PACK_SUFFIXES))} files "
                "(lower-case suffix); this one is not copied",
            )
        elif src.is_file() and src.suffix in IMAGE_SIGNATURES:
            problem = _image_problem(src)
            if problem:
                report.add(f"file {rel}", False, f"  {ERROR_MARKER} {problem}")


def _image_problem(path: Path) -> str | None:
    """Why a picture in a pack is refused (None when it is not).

    >>> import tempfile
    >>> p = Path(tempfile.mkdtemp()) / "a.png"
    >>> _ = p.write_bytes(b"GIF89a...")
    >>> _image_problem(p)
    'not a .png picture (its first bytes say otherwise): export it again as PNG'
    """
    size = path.stat().st_size
    if size > MAX_IMAGE_BYTES:
        return f"{size // 2**20} MB; a picture in a pack is at most {MAX_IMAGE_BYTES // 2**20} MB"
    with path.open("rb") as f:
        head = f.read(12)
    ok = any(head.startswith(sig) for sig in IMAGE_SIGNATURES[path.suffix])
    if path.suffix == ".webp":
        ok = ok and head[8:12] == b"WEBP"
    if not ok:
        name = path.suffix.lstrip(".").upper().replace("JPG", "JPEG")
        return f"not a {path.suffix} picture (its first bytes say otherwise): export it again as {name}"
    from an.stage.raster import image_size

    try:
        w, h = image_size(path)
    except (OSError, ValueError) as e:
        return f"not a readable picture: {e}"
    if w * h > MAX_IMAGE_PIXELS:
        return f"{w:.0f}x{h:.0f} is over {MAX_IMAGE_PIXELS:,} pixels: scale it down"
    return None


def svg_only_art(pack_dir: str | os.PathLike) -> int:
    """How many drawings the pack has when every one is SVG (0 when any is a picture,
    or there are none): hand-written SVG looks computer-made.

    >>> svg_only_art("/no/such/pack")
    0
    """
    pack = Path(pack_dir)
    art = {p for g in ART_GLOBS for p in pack.glob(g) if p.is_file()}
    svgs = [p for p in art if p.suffix == ".svg"]
    return 0 if any(p.suffix in IMAGE_SIGNATURES for p in art) else len(svgs)


_STYLE_PACK = re.compile(r"(?m)^\s*style_pack:\s*['\"]?([a-z][a-z0-9_]*)")


def pack_art_guidance(pack_dir: str | os.PathLike) -> dict | None:
    """What art to ask the writer for (:func:`cutan.art_brief.art_guidance`), in the
    look of the pack's named style if it has one, when every drawing is SVG; else None.

    >>> pack_art_guidance("/no/such/pack") is None
    True
    """
    if not svg_only_art(pack_dir):
        return None
    from cutan.art_brief import art_guidance
    from cutan.styles import style_specs

    scene = Path(pack_dir) / "scene.md"
    try:
        m = _STYLE_PACK.search(scene.read_text(encoding="utf-8"))
    except OSError:
        m = None
    style = m.group(1) if m and m.group(1) in style_specs() else None
    return art_guidance(style=style)


def _note_svg_only_art(pack: Path, report: PackReport) -> None:
    """Note a pack whose drawings are all hand-written SVG (it will look computer-made)."""
    from cutan.art_brief import SVG_ONLY_NOTE

    n = svg_only_art(pack)
    if n:
        report.notes.append(SVG_ONLY_NOTE.format(n=n))
    from an.stage.raster import has_alpha

    for part in sorted((pack / "assets" / "props").glob("*/parts/**/*")):
        if part.suffix in IMAGE_SIGNATURES and part.is_file():
            try:
                opaque = has_alpha(part) is False
            except (OSError, ValueError):
                continue
            if opaque:
                report.notes.append(
                    f"{part.relative_to(pack).as_posix()} has no transparent background: "
                    "it shows as a rectangle, background included; cut it out first "
                    "(a PNG with alpha, or cutan.carve)"
                )


#: The documents that name an asset's files, by asset kind folder.
ASSET_DOCUMENTS: tuple[tuple[str, str], ...] = (
    ("characters", "character.json"),
    ("props", "prop.json"),
    ("environments", "meta.json"),
)


def _in_pack(pack: Path, path: Path) -> Path | None:
    """``path`` when it stays inside ``pack`` once links are resolved, else ``None``
    (``_lint_files`` fails the link; nothing behind it is read)."""
    return inside_folder(pack, path.relative_to(pack).as_posix())


def _referenced_svgs(pack: Path) -> list[Path]:
    """Every file an asset document in the pack names that IS an SVG by content,
    whatever its suffix (``an`` reads it as one) and that stays inside the asset's
    folder; one that leaves it is ``an validate``'s finding, never read here."""
    out: list[Path] = []
    for kind, doc_name in ASSET_DOCUMENTS:
        for doc_path in sorted((pack / "assets" / kind).glob(f"*/{doc_name}")):
            if _in_pack(pack, doc_path) is None:
                continue
            try:
                doc = json.loads(doc_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if not isinstance(doc, dict):
                continue
            for _what, rel in _asset_references(doc):
                file = inside_folder(doc_path.parent, rel)
                if (
                    file is not None
                    and _in_pack(pack, file) is not None
                    and file.is_file()
                    and is_svg_content(file)
                ):
                    out.append(file)
    return out


def _lint_svgs(pack: Path, report: PackReport) -> None:
    chars = pack / "assets" / "characters"
    svgs = {
        f for f in (*pack.rglob("*.svg"), *_referenced_svgs(pack)) if _in_pack(pack, f)
    }
    for svg in sorted(svgs):
        rel = svg.relative_to(pack)
        # A character part keeps its factory root tag, whose size may differ from its box.
        problems = lint_svg(svg, exact_size=chars not in svg.parents)
        report.add(
            f"svg {rel.as_posix()}",
            not problems,
            "\n".join(f"  {ERROR_MARKER} {p}" for p in problems),
        )


def _lint_voices(pack: Path, report: PackReport) -> None:
    """Each voice document's keys; its values are checked by the engine later."""
    for path in sorted((pack / "assets" / "voices").glob("*.json")):
        label = f"voice {path.stem}"
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            report.add(label, False, f"  {ERROR_MARKER} {e}")
            continue
        if not isinstance(doc, dict):
            report.add(
                label, False, f"  {ERROR_MARKER} a voice document is a JSON object"
            )
            continue
        problems = [
            f"  {ERROR_MARKER} unknown key {k!r} (allowed: {', '.join(sorted(VOICE_KEYS))})"
            for k in sorted(set(doc) - VOICE_KEYS)
        ]
        problems += [
            f"  {ERROR_MARKER} {k!r} must be a string of {lo} to {hi} characters"
            for k, (lo, hi) in TEXT_KEY_LENGTHS.items()
            if k in doc
            and not (isinstance(doc[k], str) and lo <= len(doc[k].strip()) <= hi)
        ]
        model = doc.get("model_id")
        notes = (
            []
            if model is None or model in VOICE_MODELS
            else [
                f"  {WARNING_MARKER} model_id {model!r} is not one this skill knows "
                f"({', '.join(sorted(VOICE_MODELS))})"
            ]
        )
        report.add(label, not problems, "\n".join(problems + notes))


def _copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)


def _redrawn_problem(new: Path, factory: Path) -> str | None:
    """Why a redrawn part cannot replace the factory's (None when it can)."""
    if new.suffix in IMAGE_SIGNATURES:
        if not factory.with_suffix(".svg").exists():
            return (
                f"the factory made no {factory.with_suffix('.svg').name} for this "
                "picture to replace (check the name in cast.sh and the file name)"
            )
        return None
    if not factory.exists():
        return (
            f"the factory made no {factory.name} for this character "
            "(check the name in cast.sh and the file name)"
        )
    if new.suffix != ".svg":
        return None
    try:
        a, b = ET.parse(new).getroot(), ET.parse(factory).getroot()
    except ET.ParseError as e:
        return f"not valid XML: {e}"
    for attr in ("viewBox", "width", "height"):
        if a.get(attr) != b.get(attr):
            return (
                f"{attr} is {a.get(attr)!r}, the factory's is {b.get(attr)!r}: "
                "keep the factory's root tag"
            )
    return None


def _replace_with_picture(
    report: PackReport, name: str, char_dir: Path, rel: Path, picture: Path
) -> None:
    """A redrawn part that is a picture takes the place of the factory's SVG of
    the same name (``an character set-part``, cutan#92)."""
    from cutan.characters.set_part import SetPartError, replace_part_art

    try:
        replace_part_art(char_dir, rel.with_suffix(".svg").as_posix(), picture)
    except (SetPartError, OSError, ValueError) as e:
        report.add(f"redrawn {name}/{rel.as_posix()}", False, f"  {ERROR_MARKER} {e}")


def _subdirs(path: Path) -> list[Path]:
    return sorted(p for p in path.iterdir() if p.is_dir()) if path.is_dir() else []


class _OutOfTime(PackError):
    """The check's overall deadline passed."""


class _Runner:
    """Runs one ``an`` step (secrets scrubbed from its environment, within the
    step timeout and what is left of the deadline) and records it in the report."""

    def __init__(
        self, report: PackReport, *, timeout: float, deadline: float | None
    ) -> None:
        import time

        self.report, self.timeout = report, timeout
        self._clock = time.monotonic
        self._end = None if deadline is None else self._clock() + deadline
        self._env = _child_env()

    def __call__(
        self, cmd: list[str], *, cwd: Path, label: str, expect: str | None = None
    ) -> bool:
        timeout = self.timeout
        if self._end is not None:
            left = self._end - self._clock()
            if left <= 0:
                raise _OutOfTime(
                    "the check ran out of time; the remaining steps were not run"
                )
            timeout = min(timeout, left)
        try:
            proc = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=self._env,
            )
        except subprocess.TimeoutExpired:
            return self.report.add(
                label, False, f"  {ERROR_MARKER} took longer than {timeout:g} s"
            )
        out = (proc.stdout + proc.stderr).strip()
        ok = (
            proc.returncode == 0
            and not any(m in out for m in FAILURE_MARKERS)
            and (expect is None or expect in out)
        )
        return self.report.add(label, ok, out)


def _build_and_check(
    pack: Path,
    project: Path,
    report: PackReport,
    *,
    an: list[str],
    python: str,
    timeout: float,
    deadline: float | None,
) -> None:
    cast = cast_commands(pack)  # refuse a bad cast.sh before running anything
    if len(cast) > MAX_CAST_LINES:
        raise PackError(
            f"{CAST_FILE} has {len(cast)} commands; a pack checked here has at most {MAX_CAST_LINES}"
        )
    for kind in ("characters", "props", "environments"):
        n = len(_subdirs(pack / "assets" / kind))
        if n > MAX_ASSET_FOLDERS:
            raise PackError(
                f"assets/{kind} has {n} folders; at most {MAX_ASSET_FOLDERS}"
            )
    _lint_files(pack, report)
    _note_svg_only_art(pack, report)
    _lint_svgs(pack, report)
    _lint_voices(pack, report)
    run = _Runner(report, timeout=timeout, deadline=deadline)
    workdir = project.parent
    if not run(
        an + ["init", str(project)], cwd=workdir, label="an init", expect="initialized"
    ):
        return
    pack_chars = pack / "assets" / "characters"
    redrawn = [d for d in _subdirs(pack_chars) if not (d / "character.json").exists()]
    for src in pack.rglob("*"):
        rel = src.relative_to(pack)
        if (
            src.is_dir()
            or src.is_symlink()
            or src.suffix not in PACK_SUFFIXES
            or (src.suffix in IMAGE_SIGNATURES and _image_problem(src))
            or rel.as_posix() in PACK_ONLY_FILES
            or any(d in src.parents for d in redrawn)
        ):
            continue
        _copy(src, project / rel)
    # `an` syncs scene.md and ir/scene.json by age: make the pack's scene the newer.
    later = (project / "ir" / "scene.json").stat().st_mtime + 2
    os.utime(project / "scene.md", (later, later))

    for argv in cast:
        run(
            an + argv[1:],
            cwd=project,
            label=" ".join(argv[:4]),
            expect=CAST_SUCCESS[argv[2]],
        )
    chars = project / "assets" / "characters"
    for (
        d
    ) in redrawn:  # redrawn parts go over the factory's own, on the factory's canvas
        for src in sorted(d.rglob("*")):
            if src.is_file() and not src.is_symlink() and src.suffix in PACK_SUFFIXES:
                rel = src.relative_to(d)
                problem = _redrawn_problem(src, chars / d.name / rel)
                if problem:
                    report.add(
                        f"redrawn {d.name}/{rel.as_posix()}",
                        False,
                        f"  {ERROR_MARKER} {problem}",
                    )
                elif src.suffix in IMAGE_SIGNATURES:
                    _replace_with_picture(report, d.name, chars / d.name, rel, src)
                else:
                    _copy(src, chars / d.name / rel)
    if (project / "assets" / "voices").is_dir():
        run(
            [
                python,
                *_NO_CWD_PATH,
                "-c",
                VOICE_CHECK,
                str(project / "assets" / "voices"),
            ],
            cwd=project,
            label="voices (engine checks)",
        )
    for d in _subdirs(chars):
        run(
            an + ["character", "validate", d.name, "--out-dir", str(chars)],
            cwd=project,
            label=f"character {d.name}",
        )
    props = project / "assets" / "props"
    for d in _subdirs(props):
        try:
            doc = json.loads((d / "prop.json").read_text(encoding="utf-8"))
            if not isinstance(doc, dict):
                raise ValueError("prop.json must hold a JSON object")
            kind = doc.get("kind", "PropDescriptor")
        except (OSError, ValueError) as e:
            report.add(f"prop {d.name}", False, f"  {ERROR_MARKER} prop.json: {e}")
            continue
        if kind == "PropDescriptor":
            run(
                an + ["props", "validate", d.name, "--out-dir", str(props)],
                cwd=project,
                label=f"prop {d.name}",
            )
    run(
        an + ["validate", str(project), "--strict-assets"],
        cwd=project,
        label="scene",
        expect="validation: passed",
    )


def check_pack(
    pack_dir: str | os.PathLike,
    *,
    workdir: str | os.PathLike | None = None,
    an_command: Sequence[str] = DFLT_AN_COMMAND,
    python: str | None = None,
    timeout: float = DFLT_STEP_TIMEOUT,
    deadline: float | None = DFLT_DEADLINE,
) -> PackReport:
    """Check the production pack at ``pack_dir``; return a :class:`PackReport`.

    pack_dir: the pack folder (``scene.md``, ``cast.sh``, ``assets/``, ``PRODUCTION.md``)
    workdir: where the scratch project is built (default: a temporary folder,
        deleted afterwards; given, it is kept, and the project is ``<workdir>/project``)
    an_command: how to run ``an`` (default: ``python -m an`` with this interpreter)
    python: the interpreter for the engine's voice checks (default: the one in
        ``an_command`` when it starts with one, else this one)
    timeout: seconds one step may run before it counts as failed
    deadline: seconds the whole check may run (``None``: no limit)

    The pack is untrusted: only :data:`PACK_SUFFIXES` files are copied, the
    ``an`` children run without the working directory on their import path
    and without any secret-looking environment variable, the work is capped
    (:data:`MAX_CAST_LINES`, :data:`MAX_ASSET_FOLDERS`, ``deadline``), and the
    report names no server path (the scratch project is ``<project>``).

    A pack that cannot be checked at all gives a report with one failed
    ``pack`` check; nothing here raises on a bad pack.
    """
    pack = Path(pack_dir).resolve()
    report = PackReport()
    an = list(an_command)
    python = python or (an[0] if "python" in Path(an[0]).name else sys.executable)
    owned = workdir is None
    work = Path(tempfile.mkdtemp(prefix="cutan-pack-")) if owned else Path(workdir)
    work.mkdir(parents=True, exist_ok=True)
    try:
        if not (pack / "scene.md").is_file():
            raise PackError(
                f"{pack.name or pack} has no scene.md: is it a production pack?"
            )
        _build_and_check(
            pack,
            work / "project",
            report,
            an=an,
            python=python,
            timeout=timeout,
            deadline=deadline,
        )
    except PackError as e:
        report.add("pack", False, f"{ERROR_MARKER} {e}")
    except Exception as e:  # noqa: BLE001 - a malformed pack ends in a failed check, not a traceback
        report.add(
            "pack",
            False,
            f"{ERROR_MARKER} the pack could not be checked: {type(e).__name__}: {e}",
        )
    finally:
        if owned:
            shutil.rmtree(work, ignore_errors=True)
    places = [
        (str(work / "project"), "<project>"),
        (str(work), "<scratch>"),
        (str(pack), "<pack>"),
    ]
    report.checks = [
        PackCheck(c.label, c.ok, _redact(c.output, places=places))
        for c in report.checks
    ]
    return report


def main(argv: Sequence[str] | None = None) -> int:
    """``python -m cutan.pack <pack> [--keep] [--json]``: check a pack; exit 1 on a failure."""
    import argparse

    parser = argparse.ArgumentParser(description="Check a cut-out production pack.")
    parser.add_argument("pack", type=Path, help="the production pack folder")
    parser.add_argument("--keep", action="store_true", help="keep the scratch project")
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    args = parser.parse_args(argv)
    workdir = Path(tempfile.mkdtemp(prefix="cutan-pack-")) if args.keep else None
    report = check_pack(args.pack, workdir=workdir)
    print(json.dumps(report.to_dict(), indent=2) if args.json else report.format())
    if workdir is not None:
        print(f"\nScratch project kept at {workdir / 'project'}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
