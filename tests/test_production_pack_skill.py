"""The `cutan-production-pack` skill stays true to the code it describes.

That skill (``skills/cutan-production-pack/``) is uploaded to Claude.ai by
writers who never run cutan: whatever it says is all their Claude knows. So
its example pack is validated with cutan's own checks, the factory commands
its references show are run, and its generated blocks (vocabulary, preset
parameters, styles) are regenerated here and compared. On drift, regenerate:

    python -m tests.test_production_pack_skill --write
"""

from __future__ import annotations

import inspect
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "cutan-production-pack"
REFS = SKILL / "references"
EXAMPLES = SKILL / "examples"
GENRE = "cutout_animation"

#: (file, block name) of every generated block; the generator is `_BLOCKS[name]`.
GENERATED = (
    (REFS / "characters.md", "presets"),
    (REFS / "characters.md", "rig-paths"),
    (REFS / "styles.md", "styles"),
    (REFS / "art.md", "art"),
)


def _block_re(name: str) -> re.Pattern:
    return re.compile(rf"(<!-- {name}:begin[^>]*-->\n)(.*?)(<!-- {name}:end -->)", re.S)


def _presets_block() -> str:
    """The motion presets a `play` may name, with their parameters and defaults."""
    from an.genres import load
    from cutan.motion import PRESETS

    load()
    rows = ["| preset | parameters (`args`) and defaults |", "|---|---|"]
    for name, fn in PRESETS.items():
        params = [
            f"`{p.name}`" + ("" if p.default is None else f" = `{p.default!r}`")
            for p in inspect.signature(fn).parameters.values()
            if p.kind is p.KEYWORD_ONLY and p.name not in ("rest", "parts")
        ]
        rows.append(f"| `{name}` | {', '.join(params) or '(none)'} |")
    return "\n".join(rows) + "\n"


def _styles_block() -> str:
    """One section per shipped style spec: its cost, its `live` settings, its pack file."""
    import json

    import cutan
    from cutan.styles import style_pack, style_specs

    internal = re.compile(r"\s*\((?:see )?(?:an|cutan)[-#][^)]*\)")  # dev pointers the reader cannot follow

    def flat(value) -> str:
        if isinstance(value, dict):
            return "; ".join(f"{k}: {flat(v)}" for k, v in value.items())
        if isinstance(value, (list, tuple)):
            return ", ".join(flat(v) for v in value)
        text = internal.sub("", str(value).strip())
        return re.sub(r",?\s*(?:an|cutan)#\d+", "", text)

    out = []
    for name in style_specs():
        spec = cutan.style_spec(name)
        live = spec["live"]
        out += [f"### `{name}`: {spec['title']}", ""]
        out.append(f"- **Cost:** `{spec['cost_class']}`, {spec['cost_note']}.")
        for key in ("meta", "camera", "shots", "transitions", "characters", "environment",
                    "easing", "motion_presets", "tween_duration_s"):
            if key in live:
                out.append(f"- **{key}:** {flat(live[key])}")
        for key, value in spec.get("guidance", {}).items():
            if key not in ("voice_acting", "image_prompt"):  # image_prompt: art.md
                out.append(f"- *{key}:* {flat(value)}")
        pack = style_pack(name).model_dump(mode="json", exclude_none=True)
        out += ["", f"`assets/styles/{name}.json`:", "", "```json", json.dumps(pack, indent=2), "```", ""]
    return "\n".join(out)


def _rig_paths_block() -> str:
    """The node paths each rig builds: the same table as the `cutan` skill's."""
    import tempfile

    from tests.test_skill_rig_paths import _rigs_mall, rig_paths_block

    with tempfile.TemporaryDirectory() as tmp:
        return rig_paths_block(_rigs_mall(Path(tmp) / "p"))


def _art_block() -> str:
    """What each kind of art must show, the looks in words, the generators' tips:
    `cutan.art_brief`, the same source the pack checker and the connector use."""
    from cutan.art_brief import ART_KINDS, GENERATOR_TIPS, PAPER_DRAWINGS, style_look
    from cutan.styles import style_specs

    out = ["### What each picture must show", ""]
    for k in ART_KINDS.values():
        out += [f"#### {k.title} (`{k.key}`)", ""]
        out += [f"- **Goes to:** {k.goes_to}", f"- **Canvas:** {k.canvas}", f"- **Background:** {k.background}"]
        out += [f"- {c[0].upper()}{c[1:]}." for c in k.content]
        if k.status != "ready":
            out.append(f"- **Then:** {k.status}.")
        out += [f"- **Prompt words** (after the subject): {k.framing}. (Midjourney: `--ar {k.aspect}`)", ""]
    out += ["### Each named style's look, in words", "", "| style | look (paste after `Look:`) |", "|---|---|"]
    out += [f"| `{name}` | {style_look(name)} |" for name in style_specs()]
    out += ["", "### Generators", ""]
    out += [f"- **{tool}:** {tip}." for tool, tip in GENERATOR_TIPS.items()]
    out += ["", "### Drawings made on paper", ""]
    out += [f"- {line}" for line in PAPER_DRAWINGS]
    return "\n".join(out) + "\n"


_BLOCKS = {
    "presets": _presets_block,
    "rig-paths": _rig_paths_block,
    "styles": _styles_block,
    "art": _art_block,
}


def _render(path: Path, name: str) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8")
    m = _block_re(name).search(text)
    assert m, f"{path.name} has no `<!-- {name}:begin -->` block"
    fresh = _BLOCKS[name]()
    return text, text[: m.start(2)] + fresh + text[m.end(2) :]


def test_frontmatter_uploads():
    """Claude.ai refuses a skill whose frontmatter is not YAML, whose name is not
    its folder's, or whose description is over 1024 characters."""
    import yaml

    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert text.startswith("---\n")
    meta = yaml.safe_load(text.split("---\n")[1])
    assert set(meta) <= {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}
    assert meta["name"] == SKILL.name and re.fullmatch(r"[a-z0-9-]{1,64}", meta["name"])
    assert 0 < len(meta["description"]) <= 1024 and "<" not in meta["description"]


@pytest.mark.parametrize("path,name", GENERATED, ids=[n for _, n in GENERATED])
def test_generated_blocks_are_current(path, name):
    text, fresh = _render(path, name)
    assert text == fresh, "run: python -m tests.test_production_pack_skill --write"


def test_vocabulary_sections_are_current():
    """The core's names and the genre's, as `an`'s own generator renders them."""
    from an.genres import load
    from an.semantic.docs import CORE_OWNER, current_section, skill_vocabulary_section

    load()
    for owner, file in ((CORE_OWNER, "vocabulary-core.md"), (GENRE, "vocabulary-cutout.md")):
        text = (REFS / file).read_text(encoding="utf-8")
        assert current_section(text) == skill_vocabulary_section(owner=owner), (
            "run: python -m tests.test_production_pack_skill --write"
        )


def _env_with_an() -> dict:
    """The environment with this interpreter's scripts (`an`) first on PATH, and
    this checkout's `cutan` first on the import path (the skill's script runs
    from its own folder, so it would otherwise import whatever cutan is installed)."""
    env = dict(os.environ)
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
    env["PYTHONPATH"] = os.pathsep.join(p for p in (str(ROOT), env.get("PYTHONPATH")) if p)
    return env


@pytest.mark.parametrize("pack", sorted(p for p in EXAMPLES.iterdir() if p.is_dir()), ids=lambda p: p.name)
def test_example_pack_passes_validate_pack(pack):
    proc = subprocess.run(
        [sys.executable, str(SKILL / "scripts" / "validate_pack.py"), str(pack)],
        capture_output=True, text=True, env=_env_with_an(),
    )
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0, out
    assert "[warning]" not in out and "[error]" not in out, out


def _validate_pack():
    """The pack checker the skill's `validate_pack.py` fronts (cutan#87)."""
    import cutan.pack

    return cutan.pack


def test_factory_commands_in_the_skill_are_accepted(tmp_path):
    """Every complete `an character new <name> …` line the skill shows passes the
    pack's allow-list and creates a character."""
    vp = _validate_pack()
    lines = set()
    for md in [SKILL / "SKILL.md", *REFS.glob("*.md")]:
        for line in md.read_text(encoding="utf-8").splitlines():
            m = re.search(r"(an character new [a-z][^`\n]*)", line)
            if m and "<" not in m.group(1) and "..." not in m.group(1):
                lines.add(m.group(1).strip())
    assert lines, "the skill shows no `an character new <name>` command"
    for i, line in enumerate(sorted(lines)):
        argv = vp._checked_cast_line(shlex.split(line), i, line)
        argv[3] = f"c{i}"  # each its own name
        proc = subprocess.run(
            argv[:4] + ["--out-dir", str(tmp_path)] + argv[4:],
            capture_output=True, text=True, env=_env_with_an(),
        )
        out = proc.stdout + proc.stderr
        assert proc.returncode == 0 and "created character" in out, f"{line}\n{out}"


def test_cast_allow_list_refuses_what_could_escape_the_project():
    vp = _validate_pack()
    for line in (
        "an character new x --offline --out-dir /tmp/elsewhere",
        "an character new x --offline --overwrite",
        "an character new ../../x --offline",
        "an character new x",  # no --offline: a network fetch
        "an character new x --offline --build",  # a value missing
        "rm -rf x",
        "an character validate x",
    ):
        with pytest.raises(vp.PackError):
            vp._checked_cast_line(shlex.split(line), 1, line)


def test_the_documented_voice_and_style_documents_validate(tmp_path):
    """The JSON shown in voices-and-looks.md, dropped into the example, passes."""
    import shutil

    blocks = re.findall(r"```json\n(.*?)\n```", (REFS / "voices-and-looks.md").read_text(encoding="utf-8"), re.S)
    voice, style = blocks[:2]
    pack = tmp_path / "pack"
    shutil.copytree(EXAMPLES / "the-umbrella", pack)
    (pack / "assets" / "voices" / "default.json").write_text(voice)
    (pack / "assets" / "styles" / "dusk.json").write_text(style)
    scene = pack / "scene.md"
    scene.write_text(scene.read_text().replace(
        "mara [skeptical] (pause 0.5)", "narrator: Nine minutes.\nmara [skeptical] (pause 0.5)"))
    proc = subprocess.run(
        [sys.executable, str(SKILL / "scripts" / "validate_pack.py"), str(pack)],
        capture_output=True, text=True, env=_env_with_an(),
    )
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0 and "[warning]" not in out, out


def _write() -> None:
    from an.genres import load
    from an.semantic.docs import CORE_OWNER, replace_section, skill_vocabulary_section

    load()
    for owner, file in ((CORE_OWNER, "vocabulary-core.md"), (GENRE, "vocabulary-cutout.md")):
        path = REFS / file
        path.write_text(replace_section(path.read_text(encoding="utf-8"), skill_vocabulary_section(owner=owner)))
    for path, name in GENERATED:
        path.write_text(_render(path, name)[1], encoding="utf-8")


if __name__ == "__main__":
    if sys.argv[1:] == ["--write"]:
        _write()
    else:
        sys.exit("usage: python -m tests.test_production_pack_skill --write")
