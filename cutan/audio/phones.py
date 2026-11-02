"""Phones to mouth shapes: an aligner's phone timings as a Rhubarb viseme track.

A recorded take imported with a forced aligner's output carries its phones,
``AudioClip.phones``: ``(phone, start_s, end_s)`` from the clip's start (an#491),
in ARPAbet (MFA's English models: ``HH``, ``AH0``) or IPA (``mfa:ipa``: ``h``,
``ə``). The take's record knows which, but the clip does not, so the alphabet is
decided once per clip (:func:`phone_alphabet`).

:func:`phones_track` is what a lip-sync provider calls: the clip's track from its
phones, or ``None`` to align some other way. A word the aligner could not
phonetise (MFA writes ``spn`` under a name it does not know, and ``an`` drops it)
has no phones under it; it is spoken by its letters over its own span, as the
word-timing rule does (``an.audio.lipsync.word_timings_to_visemes``).

>>> [(v.time, v.code) for v in phones_to_visemes(
...     [("HH", 0.1, 0.2), ("AH0", 0.2, 0.3), ("L", 0.3, 0.4), ("OW1", 0.4, 0.6)],
...     total_duration=1.0,
... )]
[(0.0, 'X'), (0.1, 'C'), (0.3, 'H'), (0.4, 'F'), (0.6, 'X'), (1.0, 'X')]
"""

from __future__ import annotations

import unicodedata
from typing import Callable, Iterable, Mapping, Optional, Sequence

from an.audio.lipsync import Viseme, VisemeTrack
from an.audio.tts import AudioClip

#: ``(label, start_s, end_s)``, as ``AudioClip.phones`` and ``.words`` hold them.
Timing = tuple[str, float, float]
#: ``phone_to_viseme(phone, alphabet=...)``: a Rhubarb shape, or ``None`` when unknown.
PhoneToViseme = Callable[..., Optional[str]]

REST_VISEME: str = "X"
#: The letter shape a word's unknown letter takes (the word-timing rule's).
DEFAULT_LETTER_VISEME: str = "C"

#: A pause between two phones longer than this closes the mouth (seconds): the
#: word-timing rule's value (``an.audio.lipsync``'s minimum word gap for a rest).
MIN_GAP_FOR_REST_S: float = 0.20

#: Silence and noise labels, should a clip carry them (``an`` drops these when it
#: reads a TextGrid: ``an.audio.transcripts``' silence labels).
SILENCES: frozenset[str] = frozenset({"", "sil", "sp", "spn", "oov"})

# Rhubarb's shapes: A closed (P B M), B clenched teeth (most consonants, EE),
# C open (EH, AE, AH), D wide (AA), E slightly rounded (AO, ER), F puckered (UW,
# OW, W), G teeth on lip (F V), H tongue raised (L).

#: ARPAbet (stress digits removed) to a Rhubarb shape.
ARPABET_TO_VISEME: dict[str, str] = {
    # vowels
    "AA": "D", "AE": "C", "AH": "C", "AO": "E", "AW": "D", "AY": "D",
    "EH": "C", "ER": "E", "EY": "C", "IH": "B", "IY": "B", "OW": "F",
    "OY": "E", "UH": "F", "UW": "F",
    # consonants
    "P": "A", "B": "A", "M": "A",
    "F": "G", "V": "G",
    "L": "H",
    "W": "F",
    "HH": "C",
    "CH": "B", "JH": "B", "SH": "B", "ZH": "B", "TH": "B", "DH": "B",
    "D": "B", "T": "B", "N": "B", "S": "B", "Z": "B", "R": "B",
    "K": "B", "G": "B", "NG": "B", "Y": "B",
}  # fmt: skip

#: IPA (diacritics, length and stress marks removed) to a Rhubarb shape. A
#: phone not in it is read by its first symbol (``aj`` as ``a``, ``tʃ`` as ``t``).
IPA_TO_VISEME: dict[str, str] = {
    # vowels
    "a": "D", "ɑ": "D", "ɒ": "D",
    "æ": "C", "ɛ": "C", "e": "C", "ə": "C", "ʌ": "C", "ɐ": "C",
    "ɜ": "E", "ɝ": "E", "ɚ": "E", "ɔ": "E",
    "o": "F", "u": "F", "ʊ": "F", "ʉ": "F", "y": "F", "əw": "F", "əʊ": "F",
    "i": "B", "ɪ": "B",
    # consonants
    "p": "A", "b": "A", "m": "A",
    "f": "G", "v": "G", "ɱ": "G",
    "l": "H", "ɫ": "H", "ʎ": "H",
    "w": "F",
    "h": "C",
    "θ": "B", "ð": "B", "t": "B", "d": "B", "s": "B", "z": "B", "n": "B",
    "ɾ": "B", "ɹ": "B", "r": "B", "ʃ": "B", "ʒ": "B", "k": "B", "ɡ": "B",
    "g": "B", "ŋ": "B", "j": "B", "c": "B", "ɟ": "B", "ç": "B", "ɲ": "B",
    "ʔ": "B",
}  # fmt: skip

#: Marks an IPA phone may carry that do not change its mouth shape.
_IPA_MODIFIERS: frozenset[str] = frozenset("ːˑˈˌʲʰʷˠˤ")


def _is_silence(phone: str) -> bool:
    return phone.strip().lower() in SILENCES


def _arpabet_base(phone: str) -> str:
    return phone.upper().rstrip("012")


def _ipa_base(phone: str) -> str:
    return "".join(
        ch
        for ch in unicodedata.normalize("NFD", phone)
        if ch not in _IPA_MODIFIERS and not unicodedata.combining(ch)
    )


def phone_alphabet(phones: Iterable[str]) -> str:
    """``"arpabet"`` when every phone is ARPAbet as aligners write it (ASCII, one
    case throughout, each in :data:`ARPABET_TO_VISEME` once its stress digit is
    dropped), else ``"ipa"``. Decided per clip: a SAMPA ``V`` (the vowel of
    *love*) beside a lowercase ``l`` is not ARPAbet ``V``.

    >>> phone_alphabet(["HH", "AH0", "L"]), phone_alphabet(["hh", "ah0"])
    ('arpabet', 'arpabet')
    >>> phone_alphabet(["l", "V", "v"]), phone_alphabet(["h", "ə", "l"])
    ('ipa', 'ipa')
    """
    spoken = [p for p in phones if not _is_silence(p)]
    letters = [p.rstrip("012") for p in spoken]
    arpabet = (
        bool(spoken)
        and all(p.isascii() and _arpabet_base(p) in ARPABET_TO_VISEME for p in spoken)
        and (all(p.isupper() for p in letters) or all(p.islower() for p in letters))
    )
    return "arpabet" if arpabet else "ipa"


def phone_viseme(phone: str, *, alphabet: str = "arpabet") -> Optional[str]:
    """The Rhubarb shape of one phone in ``alphabet``; :data:`REST_VISEME` for a
    silence; ``None`` for a phone the table does not know.

    >>> phone_viseme("AA1"), phone_viseme("M"), phone_viseme("sil"), phone_viseme("Q9")
    ('D', 'A', 'X', None)
    >>> [phone_viseme(p, alphabet="ipa") for p in ("tʃ", "iː", "əw", "ʘ")]
    ['B', 'B', 'F', None]
    """
    if _is_silence(phone):
        return REST_VISEME
    if alphabet == "arpabet":
        return ARPABET_TO_VISEME.get(_arpabet_base(phone))
    base = _ipa_base(phone)
    return IPA_TO_VISEME.get(base) or IPA_TO_VISEME.get(base[:1])


def _letter_segments(word: Timing, char_to_viseme: Mapping[str, str]) -> list[Timing]:
    """A word's letters as ``(shape, start, end)`` spread evenly over its span
    (repeated shapes merged): the word-timing rule, for a word with no phones."""
    text, start, end = word
    codes: list[str] = []
    for ch in text.lower():
        code = char_to_viseme.get(ch, DEFAULT_LETTER_VISEME) if ch.isalpha() else None
        if code and (not codes or codes[-1] != code):
            codes.append(code)
    step = (end - start) / max(len(codes), 1)
    return [(c, start + i * step, start + (i + 1) * step) for i, c in enumerate(codes)]


def _keyframes(
    segments: Iterable[Timing],
    *,
    total_duration: float,
    rest_viseme: str,
    min_gap_for_rest: float,
) -> list[Viseme]:
    """Rest at 0; a keyframe where the shape changes, at a segment's start; rest
    after a pause longer than ``min_gap_for_rest`` and after the last segment;
    rest at ``total_duration``. Times clamped to ``[0, total_duration]``."""
    end = max(0.0, total_duration)

    def clamp(t: float) -> float:
        return max(0.0, min(float(t), end))

    out = [Viseme(time=0.0, code=rest_viseme)]
    previous, prev_end = rest_viseme, 0.0
    for code, start, stop in sorted(segments, key=lambda s: s[1]):
        start, stop = clamp(start), clamp(stop)
        if start - prev_end > min_gap_for_rest and previous != rest_viseme:
            out.append(Viseme(time=prev_end, code=rest_viseme))
            previous = rest_viseme
        if code != previous:
            out.append(Viseme(time=start, code=code))
            previous = code
        prev_end = max(prev_end, stop)
    if previous != rest_viseme and prev_end < end:
        out.append(Viseme(time=prev_end, code=rest_viseme))
    out.append(Viseme(time=end, code=rest_viseme))
    return out


def phones_to_visemes(
    phones: Iterable[Timing],
    *,
    total_duration: float,
    words: Sequence[Timing] = (),
    phone_to_viseme: PhoneToViseme = phone_viseme,
    char_to_viseme: Optional[Mapping[str, str]] = None,
    rest_viseme: str = REST_VISEME,
    min_gap_for_rest: float = MIN_GAP_FOR_REST_S,
) -> Optional[list[Viseme]]:
    """A viseme track from phone timings: each phone's shape at its start (in the
    clip's :func:`phone_alphabet`), the mouth closed at a silence, at a pause
    longer than ``min_gap_for_rest`` and after the last sound. A word of ``words``
    with no phone under it is spoken by its letters (``char_to_viseme``).

    ``None`` when a phone is one ``phone_to_viseme`` does not know: a phone set
    this table was not written for is better spread by its words than guessed.

    >>> phones_to_visemes([("ʘ", 0.0, 0.1)], total_duration=1.0) is None
    True
    >>> [(v.time, v.code) for v in phones_to_visemes(
    ...     [("M", 0.0, 0.1), ("AA1", 0.1, 0.3), ("P", 0.6, 0.7)], total_duration=0.7)]
    [(0.0, 'X'), (0.0, 'A'), (0.1, 'D'), (0.3, 'X'), (0.6, 'A'), (0.7, 'X')]
    """
    phones = list(phones)
    alphabet = phone_alphabet(p for p, _, _ in phones)
    segments: list[Timing] = []
    for phone, start, stop in phones:
        code = phone_to_viseme(str(phone), alphabet=alphabet)
        if code is None:
            return None
        segments.append((code, float(start), float(stop)))
    for word in words:
        if not any(word[1] <= (s + e) / 2 <= word[2] for _, s, e in phones):
            segments += _letter_segments(word, char_to_viseme or {})
    return _keyframes(
        segments,
        total_duration=total_duration,
        rest_viseme=rest_viseme,
        min_gap_for_rest=min_gap_for_rest,
    )


def clip_timings(audio: AudioClip, field: str) -> Optional[list[Timing]]:
    """``audio``'s ``words`` or ``phones`` as a list of ``(label, start_s, end_s)``;
    ``None`` when it has none (or its ``an`` predates the field).

    >>> clip_timings(AudioClip(duration=1.0, phones=[("M", 0, 0.1)]), "phones")
    [('M', 0.0, 0.1)]
    >>> clip_timings(AudioClip(duration=1.0), "phones") is None
    True
    """
    timings = getattr(audio, field, None)
    if not timings:
        return None
    return [(str(t[0]), float(t[1]), float(t[2])) for t in timings]


def phones_track(
    audio: AudioClip,
    *,
    phone_to_viseme: PhoneToViseme = phone_viseme,
    char_to_viseme: Optional[Mapping[str, str]] = None,
    rest_viseme: str = REST_VISEME,
    convention: str = "rhubarb",
) -> Optional[VisemeTrack]:
    """The mouth track of a clip whose phones are timed (``AudioClip.phones``, a
    take timed by a forced aligner, an#491), carrying the clip's words too;
    ``None`` when it has no phones, or one ``phone_to_viseme`` does not know.

    >>> clip = AudioClip(duration=0.5, phones=[("M", 0.1, 0.2)], words=[("m", 0.1, 0.2)])
    >>> track = phones_track(clip)
    >>> [v.code for v in track.visemes], track.words
    (['X', 'A', 'X', 'X'], [('m', 0.1, 0.2)])
    >>> phones_track(AudioClip(duration=0.5)) is None
    True
    """
    phones = clip_timings(audio, "phones")
    if not phones:
        return None
    words = clip_timings(audio, "words")
    visemes = phones_to_visemes(
        phones,
        total_duration=audio.duration,
        words=words or (),
        phone_to_viseme=phone_to_viseme,
        char_to_viseme=char_to_viseme,
        rest_viseme=rest_viseme,
    )
    if visemes is None:
        return None
    return VisemeTrack(
        visemes=visemes, convention=convention, duration=audio.duration, words=words
    )
