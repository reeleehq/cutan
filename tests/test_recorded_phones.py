"""A clip that knows its phones (a take timed by a forced aligner, an#491) drives
the mouth by them: each phone's own shape, at the phone's own time.

``an``'s ``AudioClip.phones`` carries the aligner's ``(phone, start_s, end_s)``;
the offline and whisper providers map them to Rhubarb shapes before falling
back to words (an#490) or an even spread.
"""

from __future__ import annotations

import pytest

from an.audio.tts import AudioClip
from cutan.audio.offline_lipsync import OfflineLipSync
from cutan.audio.phones import (
    ARPABET_TO_VISEME,
    IPA_TO_VISEME,
    phone_viseme,
    phones_to_visemes,
)
from cutan.audio.whisper_lipsync import WhisperLipSync

pytestmark = pytest.mark.skipif(
    "phones" not in getattr(AudioClip, "__dataclass_fields__", {}),
    reason="this an has no AudioClip.phones",
)

# "mama", as MFA's english_us_arpa model times it, and as its IPA model would.
WORDS = [("mama", 0.2, 0.8)]
ARPA = [("M", 0.2, 0.3), ("AA1", 0.3, 0.5), ("M", 0.5, 0.6), ("AH0", 0.6, 0.8)]
IPA = [("m", 0.2, 0.3), ("ɑː", 0.3, 0.5), ("m", 0.5, 0.6), ("ə", 0.6, 0.8)]
SHAPES = [(0.0, "X"), (0.2, "A"), (0.3, "D"), (0.5, "A"), (0.6, "C"), (0.8, "X")]


def _clip(*, phones=None, words=WORDS, duration=1.5):
    return AudioClip(bytes_=b"", duration=duration, words=words, phones=phones)


def _shapes(track):
    return [(round(v.time, 6), v.code) for v in track.visemes]


@pytest.mark.parametrize("phones", [ARPA, IPA], ids=["arpabet", "ipa"])
def test_offline_lipsync_follows_the_clips_phones(phones):
    track = OfflineLipSync().align(_clip(phones=phones), "mama")
    # each phone's shape at its own start, closed after the last, rest at the end
    assert _shapes(track) == SHAPES + [(1.5, "X")]
    assert track.words == WORDS and track.duration == 1.5
    assert track.convention == "rhubarb"


def test_phones_beat_words_and_an_unknown_phone_falls_back_to_them():
    by_words = OfflineLipSync().align(_clip(), "mama")
    unknown = ARPA[:2] + [("QX", 0.5, 0.6)] + ARPA[3:]
    assert _shapes(OfflineLipSync().align(_clip(phones=unknown), "mama")) == _shapes(
        by_words
    )
    assert _shapes(OfflineLipSync().align(_clip(phones=ARPA), "mama")) != _shapes(
        by_words
    )


def test_a_caller_supplies_its_own_phone_table():
    provider = OfflineLipSync(phone_to_viseme=lambda phone: "E")
    track = provider.align(_clip(phones=ARPA), "mama")
    assert [c for _, c in _shapes(track)] == ["X", "E", "X", "X"]


def test_whisper_lipsync_needs_no_model_for_a_clip_that_knows_its_phones():
    assert WhisperLipSync._model is None
    track = WhisperLipSync().align(_clip(phones=ARPA), "mama")
    assert WhisperLipSync._model is None, "no model was loaded"
    assert _shapes(track) == SHAPES + [(1.5, "X")]


def test_silences_and_long_pauses_close_the_mouth():
    phones = [("M", 0.0, 0.1), ("sil", 0.1, 0.2), ("M", 0.2, 0.3), ("P", 0.7, 0.8)]
    got = [(round(v.time, 6), v.code) for v in phones_to_visemes(phones, total_duration=0.9)]
    assert got == [
        (0.0, "X"),
        (0.0, "A"),
        (0.1, "X"),  # the aligner's silence
        (0.2, "A"),
        (0.3, "X"),  # a 0.4 s pause between phones
        (0.7, "A"),
        (0.8, "X"),
        (0.9, "X"),
    ]


def test_times_are_clamped_to_the_clip():
    got = phones_to_visemes([("AA1", -0.1, 0.4), ("M", 0.4, 2.0)], total_duration=1.0)
    assert [(v.time, v.code) for v in got] == [
        (0.0, "X"),
        (0.0, "D"),
        (0.4, "A"),
        (1.0, "X"),
    ]


def test_every_arpabet_phone_with_stress_and_the_mfa_ipa_set_have_a_shape():
    for phone in ARPABET_TO_VISEME:
        for stress in ("", "0", "1", "2"):
            assert phone_viseme(phone + stress) == ARPABET_TO_VISEME[phone]
    # MFA's english_mfa phone set, diacritics and length marks included
    for phone in "aj aw b bʲ cʰ dʒ dʲ ej iː kʰ m̩ n̩ ow pʰ tʃ tʰ uː ɑː ɒː ɔj əw ɛː ɜː ɫ̩ ʉː".split():
        assert phone_viseme(phone) in set(IPA_TO_VISEME.values()), phone
    assert phone_viseme("tʃ") == "B" and phone_viseme("ow") == "F"
