"""`[angry 0.4]`: a dialogue emotion at an intensity (an#253).

"Slightly annoyed" needed a separate `expression` action at intensity 0.45,
because the line's `[emotion]` had no intensity. The sugar carries one now: a
number from 0 to 1 after the name, kept through `scene.md`, scaling the face.
"""

from __future__ import annotations

import pytest

from an.ir.schema import Dialogue, Shot

from cutan.expression.provider import expression_spans
from cutan.expression.registration import parse_emotion


def test_the_sugar_reads_and_writes_an_intensity():
    from an.ir.sync import _format_dialogue_line, _parse_dialogue_line

    line = _parse_dialogue_line("maya [angry 0.4]: Fine.", where="t")
    assert (line.emotion, line.emotion_intensity) == ("angry", 0.4)
    assert _format_dialogue_line(line) == "maya [angry 0.4]: Fine."
    plain = _parse_dialogue_line("maya [Happy]: Hi.", where="t")
    assert (plain.emotion, plain.emotion_intensity) == ("happy", None)
    assert _format_dialogue_line(plain) == "maya [happy]: Hi."


@pytest.mark.parametrize("bad", ["angry loud", "angry 1.5", "angry -0.1", "angry 0.4 0.2"])
def test_a_bad_intensity_is_refused_with_the_form(bad):
    with pytest.raises(ValueError, match="intensity|emotion name"):
        parse_emotion(bad)


def test_the_face_takes_the_lines_intensity():
    line = Dialogue(speaker="c", text="Fine.", emotion="angry", emotion_intensity=0.4,
                    start=0.0, duration=1.0)
    full = line.model_copy(update={"emotion_intensity": None})
    (span,) = expression_spans(Shot(id="s", duration=2.0, dialogue=[line]), "c")
    (whole,) = expression_spans(Shot(id="s", duration=2.0, dialogue=[full]), "c")
    assert span.intensity == 0.4 and whole.intensity == 1.0
    mid = 0.5  # past the blend: full weight, times the intensity
    assert span.weight_at(mid) == pytest.approx(0.4 * whole.weight_at(mid))
