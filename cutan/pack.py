"""Check a cut-out production pack with cutan's own validators (cutan#87).

A production pack (the ``cutan-production-pack`` skill, cutan#86) is a folder
shaped like an ``an`` project: ``scene.md``, ``cast.sh`` (one ``an character
...`` command per line), ``assets/`` (environments, props, voices, styles,
optional redrawn character parts) and ``PRODUCTION.md``. :func:`check_pack`
builds a throwaway project from it and runs the real checks:

1. lint every SVG drawing in the pack (root tag, size, forbidden elements,
   outside links) and the keys of every voice document;
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
a report with one failed ``pack`` check, never an exception.

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

__all__ = [
    "PackCheck",
    "PackError",
    "PackReport",
    "cast_commands",
    "check_pack",
    "lint_svg",
    "main",
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
SVG_FORBIDDEN = frozenset({"image", "script", "foreignObject"})
#: Seconds one step (one `an` command) may run before it counts as failed.
DFLT_STEP_TIMEOUT = 300.0
#: How `an` is run by default: the interpreter running this code, so the check
#: needs no `an` on PATH (a service's venv rarely puts its scripts there).
DFLT_AN_COMMAND: tuple[str, ...] = (sys.executable, "-m", "an")


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
        found = [_strip_marker(ln, ERROR_MARKER) for ln in _lines_with(self.output, (ERROR_MARKER,))]
        if not self.ok and not found:
            found = [self.output.strip() or "failed with no output"]
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
            "checks": checks,
        }

    def format(self) -> str:
        """The full report as text: each step's verdict and output, then the summary."""
        parts = [
            f"=== {c.label} {'OK' if c.ok else 'FAILED'}" + (f"\n{c.output}" if c.output else "")
            for c in self.checks
        ]
        return "\n\n".join([*parts, self.summary()])


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
    if tags & SVG_FORBIDDEN:
        problems.append(f"forbidden element(s): {', '.join(sorted(tags & SVG_FORBIDDEN))}")
    if not tags & SVG_SHAPES:
        problems.append("draws nothing (no shape element)")
    if _outside_links(root):
        problems.append(
            "links to an outside file, address or embedded data (only `#id` links are allowed)"
        )
    return problems


def _outside_links(root: ET.Element) -> bool:
    for el in root.iter():
        for name, value in el.attrib.items():
            if name.endswith("href") and not value.startswith("#"):
                return True
            if re.search(r"url\(\s*['\"]?(?!#)", value) or value.strip().startswith(
                ("data:", "//", "http:", "https:", "file:")
            ):
                return True
        if el.tag.replace(SVG_NS, "") == "style" and re.search(
            r"@import|url\(\s*['\"]?(?!#)", el.text or ""
        ):
            return True
    return False


def _lint_svgs(pack: Path, report: PackReport) -> None:
    chars = pack / "assets" / "characters"
    for svg in sorted(pack.rglob("*.svg")):
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
            report.add(label, False, f"  {ERROR_MARKER} a voice document is a JSON object")
            continue
        problems = [
            f"  {ERROR_MARKER} unknown key {k!r} (allowed: {', '.join(sorted(VOICE_KEYS))})"
            for k in sorted(set(doc) - VOICE_KEYS)
        ]
        problems += [
            f"  {ERROR_MARKER} {k!r} must be a string of {lo} to {hi} characters"
            for k, (lo, hi) in TEXT_KEY_LENGTHS.items()
            if k in doc and not (isinstance(doc[k], str) and lo <= len(doc[k].strip()) <= hi)
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


def _subdirs(path: Path) -> list[Path]:
    return sorted(p for p in path.iterdir() if p.is_dir()) if path.is_dir() else []


class _Runner:
    """Runs one ``an`` step and records it in the report."""

    def __init__(self, report: PackReport, *, timeout: float) -> None:
        self.report, self.timeout = report, timeout

    def __call__(
        self, cmd: list[str], *, cwd: Path, label: str, expect: str | None = None
    ) -> bool:
        try:
            proc = subprocess.run(
                cmd, cwd=cwd, capture_output=True, text=True, timeout=self.timeout
            )
        except subprocess.TimeoutExpired:
            return self.report.add(
                label, False, f"  {ERROR_MARKER} took longer than {self.timeout:g} s"
            )
        out = (proc.stdout + proc.stderr).strip()
        ok = (
            proc.returncode == 0
            and not any(m in out for m in FAILURE_MARKERS)
            and (expect is None or expect in out)
        )
        return self.report.add(label, ok, out)


def _build_and_check(
    pack: Path, project: Path, report: PackReport, *, an: list[str], python: str, timeout: float
) -> None:
    cast = cast_commands(pack)  # refuse a bad cast.sh before running anything
    _lint_svgs(pack, report)
    _lint_voices(pack, report)
    run = _Runner(report, timeout=timeout)
    workdir = project.parent
    if not run(an + ["init", str(project)], cwd=workdir, label="an init", expect="initialized"):
        return
    pack_chars = pack / "assets" / "characters"
    redrawn = [d for d in _subdirs(pack_chars) if not (d / "character.json").exists()]
    for src in pack.rglob("*"):
        rel = src.relative_to(pack)
        if (
            src.is_dir()
            or src.is_symlink()
            or rel.as_posix() in PACK_ONLY_FILES
            or any(d in src.parents for d in redrawn)
        ):
            continue
        _copy(src, project / rel)
    # `an` syncs scene.md and ir/scene.json by age: make the pack's scene the newer.
    later = (project / "ir" / "scene.json").stat().st_mtime + 2
    os.utime(project / "scene.md", (later, later))

    for argv in cast:
        run(an + argv[1:], cwd=project, label=" ".join(argv[:4]), expect=CAST_SUCCESS[argv[2]])
    chars = project / "assets" / "characters"
    for d in redrawn:  # redrawn parts go over the factory's own, on the factory's canvas
        for src in sorted(d.rglob("*")):
            if src.is_file() and not src.is_symlink():
                rel = src.relative_to(d)
                problem = _redrawn_problem(src, chars / d.name / rel)
                if problem:
                    report.add(
                        f"redrawn {d.name}/{rel.as_posix()}", False, f"  {ERROR_MARKER} {problem}"
                    )
                else:
                    _copy(src, chars / d.name / rel)
    if (project / "assets" / "voices").is_dir():
        run(
            [python, "-c", VOICE_CHECK, str(project / "assets" / "voices")],
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
) -> PackReport:
    """Check the production pack at ``pack_dir``; return a :class:`PackReport`.

    pack_dir: the pack folder (``scene.md``, ``cast.sh``, ``assets/``, ``PRODUCTION.md``)
    workdir: where the scratch project is built (default: a temporary folder,
        deleted afterwards; given, it is kept, and the project is ``<workdir>/project``)
    an_command: how to run ``an`` (default: ``python -m an`` with this interpreter)
    python: the interpreter for the engine's voice checks (default: the one in
        ``an_command`` when it starts with one, else this one)
    timeout: seconds one step may run before it counts as failed

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
            raise PackError(f"{pack.name or pack} has no scene.md: is it a production pack?")
        _build_and_check(pack, work / "project", report, an=an, python=python, timeout=timeout)
    except PackError as e:
        report.add("pack", False, f"{ERROR_MARKER} {e}")
    except Exception as e:  # noqa: BLE001 - a malformed pack ends in a failed check, not a traceback
        report.add(
            "pack", False, f"{ERROR_MARKER} the pack could not be checked: {type(e).__name__}: {e}"
        )
    finally:
        if owned:
            shutil.rmtree(work, ignore_errors=True)
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
