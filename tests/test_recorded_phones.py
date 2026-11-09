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
    phone_alphabet,
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
    provider = OfflineLipSync(phone_to_viseme=lambda phone, alphabet: "E")
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
            assert phone_viseme((phone + stress).lower()) == ARPABET_TO_VISEME[phone]
    # MFA's english_mfa phone set, diacritics and length marks included
    mfa_ipa = (
        "a aj aw b bʲ c cʰ d dʒ dʲ e ej f fʲ h i iː j k kʰ l m mʲ m̩ n n̩ o ow p pʰ "
        "pʲ s t tʃ tʰ tʲ u uː v vʲ w z æ ç ð ŋ ɐ ɑ ɑː ɒ ɒː ɔ ɔj ə əw ɚ ɛ ɛː ɜ ɜː ɝ "
        "ɟ ɡ ɪ ɫ ɫ̩ ɱ ɲ ɹ ɾ ʃ ʉ ʉː ʊ ʎ ʒ ʔ θ"
    ).split()
    assert phone_alphabet(mfa_ipa) == "ipa"
    for phone in mfa_ipa:
        assert phone_viseme(phone, alphabet="ipa") in set(IPA_TO_VISEME.values()), phone
    assert [phone_viseme(p, alphabet="ipa") for p in ("tʃ", "ow", "əw", "ɱ", "ɜː")] == [
        "B", "F", "F", "G", "E"
    ]  # fmt: skip


def test_the_alphabet_is_the_clips_not_each_phones():
    # SAMPA "love": V is the vowel there, not ARPAbet's teeth-on-lip V
    assert phone_alphabet(["l", "V", "v"]) == "ipa"
    sampa = [("l", 0.0, 0.1), ("V", 0.1, 0.2), ("v", 0.2, 0.3)]
    assert phones_to_visemes(sampa, total_duration=0.5) is None  # spread by words
    # lowercase ARPAbet is ARPAbet: "ae" is AE (C), not IPA a (D)
    got = phones_to_visemes([("ae1", 0.0, 0.1), ("er0", 0.1, 0.2)], total_duration=0.2)
    assert [v.code for v in got] == ["X", "C", "E", "X"]


def test_a_word_with_no_phones_under_it_is_spoken_by_its_letters():
    """MFA writes ``spn`` under a word it cannot phonetise (a name); ``an``
    drops it, so the word has no phones. Its span is not a pause."""
    words = [("hi", 0.0, 0.3), ("gwendolyn", 0.3, 0.9)]
    clip = _clip(phones=[("HH", 0.0, 0.1), ("AY1", 0.1, 0.3)], words=words, duration=1.2)
    track = OfflineLipSync().align(clip, "hi gwendolyn")
    in_name = [v for v in track.visemes if 0.3 <= v.time < 0.9]
    assert len(in_name) >= 3 and all(v.code != "X" for v in in_name)
    # HH takes the shape of the AY after it (D), so the breath does not flash a C
    assert [(round(v.time, 6), v.code) for v in track.visemes][:2] == [
        (0.0, "X"), (0.0, "D")
    ]  # fmt: skip


def test_whisper_runs_its_model_for_phones_without_words(monkeypatch):
    """Whisper promises word timings: phones alone do not give them."""
    called = []
    monkeypatch.setattr(
        WhisperLipSync, "_get_model", lambda self: called.append(1) or _NoSpeech()
    )
    clip = AudioClip(bytes_=b"\0", duration=1.5, phones=ARPA)
    WhisperLipSync().align(clip, "mama")
    assert called


class _NoSpeech:
    def transcribe(self, *_, **__):
        return [], None


def test_unsorted_phones_are_read_in_time_order():
    shuffled = [ARPA[2], ARPA[0], ARPA[3], ARPA[1]]
    track = OfflineLipSync().align(_clip(phones=shuffled), "mama")
    assert _shapes(track) == SHAPES + [(1.5, "X")]


def test_a_silence_label_does_not_cover_a_word_and_a_zero_length_word_adds_nothing():
    words = [("gwendolyn", 0.0, 0.6), ("zero", 0.7, 0.7)]
    phones = [("spn", 0.0, 0.6), ("M", 0.6, 0.8)]
    got = phones_to_visemes(phones, total_duration=1.0, words=words, rest_viseme="R")
    codes = [v.code for v in got if v.time < 0.6][1:]  # after the leading rest
    assert codes and set(codes) - {"R", "X"}  # the name is spoken
    assert not [v for v in got if v.time == 0.7]
    assert {v.code for v in got} <= {"R", "A", "B", "C", "D", "E", "F", "G", "H"}


def test_cutan_holds_ans_arpabet_inventory_not_its_own():
    from an.audio.transcripts import ARPABET_PHONES

    assert set(ARPABET_TO_VISEME) == set(ARPABET_PHONES)


def test_a_takes_recorded_alphabet_beats_the_guess():
    # Labels that read as IPA by the clip's own rule ("l", "V" in one case mix)...
    phones = [("l", 0.0, 0.1), ("V", 0.1, 0.2)]
    assert phone_alphabet(p for p, _, _ in phones) == "ipa"
    # ...are mapped as ARPAbet when the take's record says so: L is H, V is G.
    got = phones_to_visemes(phones, total_duration=0.2, alphabet="arpabet")
    assert [v.code for v in got] == ["X", "H", "G", "X"]


@pytest.mark.skipif(
    "phone_alphabet" not in getattr(AudioClip, "__dataclass_fields__", {}),
    reason="this an has no AudioClip.phone_alphabet",
)
def test_phones_track_reads_the_clips_recorded_alphabet():
    from cutan.audio.phones import phones_track

    clip = AudioClip(
        duration=0.2, phones=[("l", 0.0, 0.1), ("V", 0.1, 0.2)], phone_alphabet="arpabet"
    )
    assert [v.code for v in phones_track(clip).visemes] == ["X", "H", "G", "X"]


@pytest.mark.parametrize("recorded", [None, "", "garbage"])
def test_an_absent_or_unknown_recorded_alphabet_is_guessed(recorded):
    got = phones_to_visemes(
        [("ae1", 0.0, 0.1), ("er0", 0.1, 0.2)], total_duration=0.2, alphabet=recorded
    )
    assert [v.code for v in got] == ["X", "C", "E", "X"]


def test_the_recorded_alphabet_is_read_case_insensitively():
    got = phones_to_visemes([("l", 0.0, 0.1)], total_duration=0.1, alphabet="ARPABET")
    assert [v.code for v in got] == ["X", "H", "X"]


def test_hh_takes_the_shape_of_the_phone_after_it():
    got = phones_to_visemes(
        [("HH", 0.0, 0.1), ("AA1", 0.1, 0.3)], total_duration=0.3, alphabet="arpabet"
    )
    assert [(v.time, v.code) for v in got] == [(0.0, "X"), (0.0, "D"), (0.3, "X")]
    # ...and kept as its own at the end, where nothing follows it
    got = phones_to_visemes([("HH", 0.0, 0.1)], total_duration=0.1, alphabet="arpabet")
    assert [v.code for v in got] == ["X", "C", "X"]


def test_a_tongue_only_consonant_can_be_weighed_low_by_the_phone_not_the_letter():
    from cutan.audio.phones import TONGUE_ONLY_INTENSITY

    phones = [("IY1", 0.0, 0.1), ("T", 0.1, 0.2)]  # both are Rhubarb B
    flat = phones_to_visemes(phones, total_duration=0.2, alphabet="arpabet")
    assert {v.intensity for v in flat} == {1.0}  # the default: unchanged
    weighed = phones_to_visemes(
        phones + [("AA1", 0.2, 0.3)],
        total_duration=0.3,
        alphabet="arpabet",
        intensity_of=TONGUE_ONLY_INTENSITY,
    )
    assert {v.code: v.intensity for v in weighed}["B"] == 1.0  # the EE vowel
    t_only = phones_to_visemes(
        [("T", 0.0, 0.1)], total_duration=0.1, alphabet="arpabet",
        intensity_of=TONGUE_ONLY_INTENSITY,
    )
    assert [v.intensity for v in t_only if v.code == "B"] == [0.4]
