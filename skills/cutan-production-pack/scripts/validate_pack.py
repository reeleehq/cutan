"""Check a cut-out production pack with cutan's own validators.

A production pack is a folder shaped like an `an` project: ``scene.md``,
``cast.sh`` (one ``an character ...`` command per line) and ``assets/``
(environments, props, optional hand-drawn or redrawn characters, optional
style packs). This script builds a throwaway project from it and runs the
real checks:

1. lint every SVG drawing in the pack (root tag, size, forbidden elements,
   outside links) and the keys of every voice document;
2. ``an init`` a scratch project and copy the pack over it, except redrawn
   character parts (a character folder with no ``character.json``);
3. run each ``cast.sh`` line, refusing anything but the factory commands and
   options the skill documents (no shell: the line is split and run directly);
4. copy the redrawn parts over the factory's (same file names, same root
   tag), check the voice documents with the engine's own checks, then
   ``an character validate`` every character and ``an props validate`` every
   drawn prop;
5. ``an validate --strict-assets`` the scene.

A step fails on an error in its output, not only on its exit status (the
``an`` commands exit 0 on some failures). Warnings are counted and printed.

It needs only the standard library and the ``an`` command, which
``pip install cutan`` provides (pure Python, no browser; nothing is rendered).
Exit status: 0 when nothing failed, 1 otherwise.

    python validate_pack.py path/to/pack            # check, then delete the scratch project
    python validate_pack.py path/to/pack --keep     # keep it and print where it is
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

CAST_FILE = "cast.sh"
PACK_ONLY_FILES = (CAST_FILE,)
NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,40}$")
#: Per `an character` subcommand: the options a pack may pass (value-taking
#: ones map to True, flags to False). Anything else is refused: `--out-dir`,
#: `--overwrite` and a network fetch (no `--offline`) never reach the factory.
CAST_OPTIONS = {
    "new": {
        "--offline": False, "--build": True, "--head-scale": True, "--hat": True,
        "--hair-style": True, "--hair-length": True, "--sash": False, "--palette": True,
        "--mouth-variants": True, "--no-views": False, "--voice-ref": True,
    },
    "mouths": {"--variants": True},
    "add-half-lid": {"--fraction": True},
    "add-views": {},
    "add-gaze": {},
}
#: What each cast subcommand prints when it worked (the `an` commands exit 0 on failure).
CAST_SUCCESS = {
    "new": "created character", "mouths": "wrote ", "add-half-lid": "added a HALF eyelid",
    "add-views": "added the views", "add-gaze": "added the eye stack",
}
FAILURE_MARKERS = ("[error]", "FAILED", "Traceback (most recent call last)")
#: Factory notes that carry no `[warning]` marker but are one.
NOTE_MARKERS = ("covers the brows",)
VOICE_KEYS = {"provider", "voice_id", "model_id", "voice_settings", "seed", "effects", "takes", "loudness_offset_db"}
VOICE_MODELS = {"eleven_v3", "eleven_v4", "eleven_v4_turbo", "eleven_v3_conversational",
                "eleven_multilingual_v2", "eleven_turbo_v2_5"}
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
SVG_SHAPES = {"path", "rect", "circle", "ellipse", "polygon", "polyline", "line", "text", "use"}
SVG_FORBIDDEN = {"image", "script", "foreignObject"}


class PackError(Exception):
    """A pack that cannot be checked at all (a missing file, a refused line)."""


def _an() -> list[str]:
    exe = shutil.which("an")
    if exe is None:
        raise PackError(
            "The `an` command is not installed. Run `pip install cutan` "
            "(it brings `an`), then try again."
        )
    return [exe]


def _python_of(exe: str) -> str:
    """The interpreter behind a console script (its shebang), else this one."""
    try:
        first = Path(exe).read_text(encoding="utf-8", errors="replace").splitlines()[0]
    except (OSError, IndexError):
        return sys.executable
    return first[2:].strip() if first.startswith("#!") and "python" in first else sys.executable


class Report:
    """The steps run so far, with their verdicts and warning counts."""

    def __init__(self) -> None:
        self.steps: list[tuple[str, bool]] = []
        self.warnings = 0

    def add(self, label: str, ok: bool, out: str = "") -> bool:
        self.steps.append((label, ok))
        self.warnings += out.count("[warning]") + sum(out.count(m) for m in NOTE_MARKERS)
        print(f"\n=== {label} {'OK' if ok else 'FAILED'}")
        if out:
            print(out)
        return ok

    def run(self, cmd: list[str], *, cwd: Path, label: str, expect: str | None = None) -> bool:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
        out = (proc.stdout + proc.stderr).strip()
        ok = (
            proc.returncode == 0
            and not any(m in out for m in FAILURE_MARKERS)
            and (expect is None or expect in out)
        )
        return self.add(label, ok, out)

    @property
    def ok(self) -> bool:
        return all(ok for _, ok in self.steps)

    def summary(self) -> str:
        passed = sum(ok for _, ok in self.steps)
        verdict = "PASS" if self.ok else "FAIL"
        return f"{verdict}: {passed}/{len(self.steps)} checks passed, {self.warnings} warning(s)"


def cast_commands(pack: Path) -> list[list[str]]:
    """The ``an character`` commands of ``cast.sh``; raise on any other line.

    Blank lines and ``#`` comments are skipped; a trailing backslash continues
    a line.
    """
    path = pack / CAST_FILE
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
        raise refuse(f"only `an character {{{'|'.join(CAST_OPTIONS)}}} <name> ...` is allowed")
    sub, name, rest = argv[2], argv[3], argv[4:]
    if not NAME_RE.match(name):
        raise refuse(f"{name!r} is not a character name (lowercase letters, digits, _)")
    allowed = CAST_OPTIONS[sub]
    i = 0
    while i < len(rest):
        opt = rest[i]
        if opt not in allowed:
            raise refuse(f"option {opt!r} is not allowed here (allowed: {', '.join(allowed) or 'none'})")
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
            if (float(root.get("width")), float(root.get("height"))) != (float(box[2]), float(box[3])):
                problems.append("width/height differ from the viewBox size")
        except ValueError:
            problems.append("width/height are not plain numbers")
    tags = {el.tag.replace(SVG_NS, "") for el in root.iter()}
    if tags & SVG_FORBIDDEN:
        problems.append(f"forbidden element(s): {', '.join(sorted(tags & SVG_FORBIDDEN))}")
    if not tags & SVG_SHAPES:
        problems.append("draws nothing (no shape element)")
    if _outside_links(root):
        problems.append("links to an outside file, address or embedded data (only `#id` links are allowed)")
    return problems


def _outside_links(root: ET.Element) -> bool:
    for el in root.iter():
        for name, value in el.attrib.items():
            if name.endswith("href") and not value.startswith("#"):
                return True
            if re.search(r"url\(\s*['\"]?(?!#)", value) or value.strip().startswith(("data:", "//", "http:", "https:", "file:")):
                return True
        if el.tag.replace(SVG_NS, "") == "style" and re.search(r"@import|url\(\s*['\"]?(?!#)", el.text or ""):
            return True
    return False


def _lint_svgs(pack: Path, report: Report) -> None:
    chars = pack / "assets" / "characters"
    for svg in sorted(pack.rglob("*.svg")):
        rel = svg.relative_to(pack)
        # A character part keeps its factory root tag, whose size may differ from its box.
        problems = lint_svg(svg, exact_size=chars not in svg.parents)
        report.add(f"svg {rel.as_posix()}", not problems, "\n".join(f"  [error] {p}" for p in problems))


def _lint_voices(pack: Path, report: Report) -> None:
    """Each voice document's keys; its values are checked by the engine later."""
    for path in sorted((pack / "assets" / "voices").glob("*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            report.add(f"voice {path.stem}", False, f"  [error] {e}")
            continue
        if not isinstance(doc, dict):
            report.add(f"voice {path.stem}", False, "  [error] a voice document is a JSON object")
            continue
        problems = [f"  [error] unknown key {k!r} (allowed: {', '.join(sorted(VOICE_KEYS))})"
                    for k in sorted(set(doc) - VOICE_KEYS)]
        model = doc.get("model_id")
        notes = [] if model is None or model in VOICE_MODELS else [
            f"  [warning] model_id {model!r} is not one this skill knows ({', '.join(sorted(VOICE_MODELS))})"]
        report.add(f"voice {path.stem}", not problems, "\n".join(problems + notes))


def _copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)


def _redrawn_problem(new: Path, factory: Path) -> str | None:
    """Why a redrawn part cannot replace the factory's (None when it can)."""
    if not factory.exists():
        return f"the factory made no {factory.name} for this character (check the name in cast.sh and the file name)"
    if new.suffix != ".svg":
        return None
    try:
        a, b = ET.parse(new).getroot(), ET.parse(factory).getroot()
    except ET.ParseError as e:
        return f"not valid XML: {e}"
    for attr in ("viewBox", "width", "height"):
        if a.get(attr) != b.get(attr):
            return f"{attr} is {a.get(attr)!r}, the factory's is {b.get(attr)!r}: keep the factory's root tag"
    return None


def _subdirs(path: Path) -> list[Path]:
    return sorted(p for p in path.iterdir() if p.is_dir()) if path.is_dir() else []


def validate_pack(pack: Path, *, workdir: Path) -> Report:
    """Build a project from ``pack`` under ``workdir`` and run every check."""
    an = _an()
    pack = pack.resolve()
    if not (pack / "scene.md").exists():
        raise PackError(f"{pack.name} has no scene.md: is it a production pack?")
    cast = cast_commands(pack)  # refuse a bad cast.sh before running anything
    report = Report()
    _lint_svgs(pack, report)
    _lint_voices(pack, report)

    project = workdir / "project"
    if not report.run(an + ["init", str(project)], cwd=workdir, label="an init", expect="initialized"):
        return report
    pack_chars = pack / "assets" / "characters"
    redrawn = [d for d in _subdirs(pack_chars) if not (d / "character.json").exists()]
    for src in pack.rglob("*"):
        rel = src.relative_to(pack)
        if src.is_dir() or rel.as_posix() in PACK_ONLY_FILES or any(d in src.parents for d in redrawn):
            continue
        _copy(src, project / rel)
    # `an` syncs scene.md and ir/scene.json by age: make the pack's scene the newer.
    later = (project / "ir" / "scene.json").stat().st_mtime + 2
    os.utime(project / "scene.md", (later, later))

    for argv in cast:
        report.run(an + argv[1:], cwd=project, label=" ".join(argv[:4]), expect=CAST_SUCCESS[argv[2]])
    chars = project / "assets" / "characters"
    for d in redrawn:  # redrawn parts go over the factory's own, on the factory's canvas
        for src in sorted(d.rglob("*")):
            if src.is_file():
                rel = src.relative_to(d)
                problem = _redrawn_problem(src, chars / d.name / rel)
                if problem:
                    report.add(f"redrawn {d.name}/{rel.as_posix()}", False, f"  [error] {problem}")
                else:
                    _copy(src, chars / d.name / rel)
    if (project / "assets" / "voices").is_dir():
        report.run([_python_of(an[0]), "-c", VOICE_CHECK, str(project / "assets" / "voices")],
                   cwd=project, label="voices (engine checks)")
    for d in _subdirs(chars):
        report.run(an + ["character", "validate", d.name, "--out-dir", str(chars)],
                   cwd=project, label=f"character {d.name}")
    props = project / "assets" / "props"
    for d in _subdirs(props):
        try:
            doc = json.loads((d / "prop.json").read_text(encoding="utf-8"))
            if not isinstance(doc, dict):
                raise ValueError("prop.json must hold a JSON object")
            kind = doc.get("kind", "PropDescriptor")
        except (OSError, ValueError) as e:
            report.add(f"prop {d.name}", False, f"  [error] prop.json: {e}")
            continue
        if kind == "PropDescriptor":
            report.run(an + ["props", "validate", d.name, "--out-dir", str(props)],
                       cwd=project, label=f"prop {d.name}")
    report.run(an + ["validate", str(project), "--strict-assets"], cwd=project,
               label="scene", expect="validation: passed")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("pack", type=Path, help="the production pack folder")
    parser.add_argument("--keep", action="store_true", help="keep the scratch project")
    args = parser.parse_args(argv)
    workdir = Path(tempfile.mkdtemp(prefix="cutan-pack-"))
    try:
        report = validate_pack(args.pack, workdir=workdir)
    except PackError as e:
        print(f"FAIL: {e}")
        return 1
    except Exception as e:  # noqa: BLE001 - a malformed pack must end in a FAIL line, not a traceback
        print(f"FAIL: the pack could not be checked: {type(e).__name__}: {e}")
        return 1
    finally:
        if args.keep:
            print(f"\nScratch project kept at {workdir / 'project'}")
        else:
            shutil.rmtree(workdir, ignore_errors=True)
    print(f"\n{report.summary()}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
