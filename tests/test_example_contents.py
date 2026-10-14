"""Content of the committed examples, pinned where the examples live.

Moved from `an`'s `tests/test_dialogue_parse_errors.py` (an#433): which line a
cut-out example speaks is `cutan` content, so a change to the example is a change
to this test, not to `an`'s suite.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_promote_demo_has_its_line_again():
    """Its IR carries the line. Whether visemes are stamped depends on whether
    someone ran the example (`auto_audio=True` persists them) — the bench does
    not care, because `_prepare_promote_demo` regenerates the staged IR from
    the md, so the fixture's picture and contract hash are a property of the
    tree, not of developer state."""
    ir = json.loads(
        (REPO / "examples" / "promote_demo" / "ir" / "scene.json").read_text(encoding="utf-8")
    )
    (line,) = ir["timeline"][0]["dialogue"]
    assert line["speaker"] == "maya" and line["text"].startswith("I started life")
