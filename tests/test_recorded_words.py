"""A clip that knows its words (a recorded take, an#490) drives the mouth by them.

``an``'s ``AudioClip.words`` carries a take's word timings; the offline and the
whisper providers use them instead of an even spread or a model run.
"""

from __future__ import annotations

import pytest

from an.audio.tts import AudioClip
from cutan.audio.offline_lipsync import OfflineLipSync, clip_words
from cutan.audio.whisper_lipsync import WhisperLipSync

WORDS = [("hi", 0.2, 0.5), ("you", 1.0, 1.4)]

# The field arrives with the `an` release that ships recorded voices; against an
# older `an` these tests have nothing to exercise (the providers' `getattr` path
# is what keeps them working there).
pytestmark = pytest.mark.skipif(
    "words" not in getattr(AudioClip, "__dataclass_fields__", {}),
    reason="this an has no AudioClip.words",
)


def _clip(words):
    return AudioClip(bytes_=b"", duration=2.0, words=words)


def test_clip_words_reads_the_field_and_tolerates_its_absence():
    assert clip_words(_clip(WORDS)) == WORDS
    assert clip_words(AudioClip(duration=1.0)) is None


def test_offline_lipsync_follows_the_clips_words():
    track = OfflineLipSync().align(_clip(WORDS), "hi you")
    assert track.words == WORDS
    spoken = [v for v in track.visemes if v.code != "X"]
    assert spoken, "the words make mouth shapes"
    assert all(0.2 <= v.time <= 0.5 or 1.0 <= v.time <= 1.4 for v in spoken)
    assert track.visemes[0].code == "X" and track.visemes[-1].time == pytest.approx(2.0)


def test_offline_lipsync_without_words_spreads_as_before():
    track = OfflineLipSync().align(_clip(None), "hi you")
    assert track.words is None
    assert len(track.visemes) >= 3


def test_whisper_lipsync_needs_no_model_for_a_clip_that_knows_its_words():
    provider = WhisperLipSync()
    assert WhisperLipSync._model is None
    track = provider.align(_clip(WORDS), "hi you")
    assert WhisperLipSync._model is None, "no model was loaded"
    assert track.words == WORDS
    assert any(0.2 <= v.time <= 0.5 for v in track.visemes if v.code != "X")
