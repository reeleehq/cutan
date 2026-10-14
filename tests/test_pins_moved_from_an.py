"""Pins on `cutan`-owned content that `an`'s suite used to carry (an#433).

A cutan change that touches only genre content must never fail `an`'s tests, so the
literal colours and the compile-source line they pinned are asserted here instead.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


def test_the_default_leg_and_pupil_colours_are_the_literals_they_replaced():
    """Both moved from inline literals into named constants. A constant whose
    value drifts is a picture change nobody asked for, and only a labelled
    golden run would otherwise catch it."""
    from cutan.compile.passes import DFLT_LEG_COLOUR, DFLT_PUPIL_COLOUR

    assert DFLT_LEG_COLOUR == "#2c3e50"
    assert DFLT_PUPIL_COLOUR == "#1a1a1a"


def test_the_compiler_emits_a_non_default_loop_mode():
    """A compiler path writes a non-default loop_mode (`_resolve_play`), so the
    "nothing emits loop_mode" gap line in an's docs would be true again if this broke."""
    passes = importlib.util.find_spec("cutan.compile.passes")
    assert passes is not None and passes.origin
    compile_src = Path(passes.origin).read_text(encoding="utf-8")
    assert 'loop_mode="loop" if loop else "once"' in compile_src
