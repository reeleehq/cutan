"""The cutan skill's vocabulary section is generated from the registry, and current (an#354).

The names this genre contributes (presets, methods, its action and entity kinds)
are listed in ``.claude/skills/cutan/SKILL.md``, rendered by ``an``'s generator
for this owner. They live here, not in ``an``'s skill, so a change to one of them
fails THIS repository's CI and never an unrelated ``an`` pull request.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OWNER = "cutout_animation"


def test_the_skill_vocabulary_section_is_generated_and_current():
    from an.genres import load
    from an.semantic.docs import current_section, skill_vocabulary_section

    load()
    skill = (ROOT / ".claude" / "skills" / "cutan" / "SKILL.md").read_text(encoding="utf-8")
    assert current_section(skill) == skill_vocabulary_section(owner=OWNER), (
        f"run: python -m an.semantic.docs --write .claude/skills/cutan/SKILL.md --owner {OWNER}"
    )
