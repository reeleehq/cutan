"""Phones to mouth shapes: an aligner's phone timings as a Rhubarb viseme track.

A recorded take imported with a forced aligner's output carries its phones,
``AudioClip.phones``: ``(phone, start_s, end_s)`` from the clip's start (an#491),
in ARPAbet (MFA's English models: ``HH``, ``AH0``) or IPA (``mfa:ipa``: ``h``,
``ə``). The take's record knows which, but the clip does not, so each phone is
read by its own shape: an upper-case ASCII phone is ARPAbet, anything else IPA.

:func:`phones_to_visemes` gives one keyframe per change of mouth shape, at the
phone's start, and closes the mouth in silences; :func:`phone_viseme` is the
table it reads, which a caller replaces with ``phone_to_viseme=``.
:func:`phones_track` is what a lip-sync provider calls: the clip's track from its
phones, or ``None`` to align some other way.

>>> [(v.time, v.code) for v in phones_to_visemes(
...     [("HH", 0.1, 0.2), ("AH0", 0.2, 0.3), ("L", 0.3, 0.4), ("OW1", 0.4, 0.6)],
...     total_duration=1.0,
... )]
[(0.0, 'X'), (0.1, 'C'), (0.3, 'H'), (0.4, 'F'), (0.6, 'X'), (1.0, 'X')]
"""

from __future__ import annotations

import unicodedata
from typing import Callable, Iterable, Optional

from an.audio.lipsync import Viseme, VisemeTrack
from an.audio.tts import AudioClip

#: ``(phone, start_s, end_s)``, as ``AudioClip.phones`` holds them.
PhoneTiming = tuple[str, float, float]

REST_VISEME: str = "X"

#: A pause between two phones longer than this closes the mouth (seconds): the
#: word-timing rule's value (``an.audio.lipsync.word_timings_to_visemes``).
MIN_GAP_FOR_REST_S: float = 0.20

#: What aligners write for silence and noise: the mouth rests.
SILENCES: frozenset[str] = frozenset({"", "sil", "sp", "spn", "<eps>", "<unk>"})

# Rhubarb's shapes: A closed (P B M), B clenched teeth (most consonants, EE),
# C open (EH, AE), D wide (AA), E slightly rounded (AO, ER), F puckered (UW, OW,
# W), G teeth on lip (F V), H tongue raised (L).

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
    "a": "D", "ɑ": "D", "ɒ": "D", "ɐ": "D",
    "æ": "C", "ɛ": "C", "e": "C", "ə": "C", "ʌ": "C", "ɜ": "C",
    "ɝ": "E", "ɚ": "E", "ɔ": "E",
    "o": "F", "u": "F", "ʊ": "F", "ʉ": "F", "y": "F",
    "i": "B", "ɪ": "B",
    # consonants
    "p": "A", "b": "A", "m": "A",
    "f": "G", "v": "G",
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


def _ipa_base(phone: str) -> str:
    return "".join(
        ch
        for ch in unicodedata.normalize("NFD", phone)
        if ch not in _IPA_MODIFIERS and not unicodedata.combining(ch)
    )


def phone_viseme(phone: str) -> Optional[str]:
    """The Rhubarb shape of one phone, ARPAbet or IPA; :data:`REST_VISEME` for a
    silence; ``None`` for a phone neither table knows.

    >>> phone_viseme("AA1"), phone_viseme("M"), phone_viseme("tʃ"), phone_viseme("iː")
    ('D', 'A', 'B', 'B')
    >>> phone_viseme("sil"), phone_viseme("Q9"), phone_viseme("ʘ")
    ('X', None, None)
    """
    if phone.strip().lower() in SILENCES:
        return REST_VISEME
    if phone.isascii() and phone.upper() == phone and phone[:1].isalpha():
        return ARPABET_TO_VISEME.get(phone.rstrip("012"))
    base = _ipa_base(phone)
    return IPA_TO_VISEME.get(base) or IPA_TO_VISEME.get(base[:1])


def phones_to_visemes(
    phones: Iterable[PhoneTiming],
    *,
    total_duration: float,
    phone_to_viseme: Callable[[str], Optional[str]] = phone_viseme,
    rest_viseme: str = REST_VISEME,
    min_gap_for_rest: float = MIN_GAP_FOR_REST_S,
) -> Optional[list[Viseme]]:
    """A viseme track from phone timings: rest at 0, a keyframe at each phone's
    start where the shape changes, rest at a silence phone, at a pause longer
    than ``min_gap_for_rest`` and after the last phone, and rest at
    ``total_duration``. Times are clamped to ``[0, total_duration]``.

    ``None`` when a phone is one ``phone_to_viseme`` does not know: a phone set
    this table was not written for is better spread by its words than guessed.

    >>> phones_to_visemes([("ʘ", 0.0, 0.1)], total_duration=1.0) is None
    True
    >>> [(v.time, v.code) for v in phones_to_visemes(
    ...     [("M", 0.0, 0.1), ("AA1", 0.1, 0.3), ("P", 0.6, 0.7)], total_duration=0.7)]
    [(0.0, 'X'), (0.0, 'A'), (0.1, 'D'), (0.3, 'X'), (0.6, 'A'), (0.7, 'X')]
    """
    end = max(0.0, total_duration)

    def clamp(t: float) -> float:
        return max(0.0, min(float(t), end))

    out = [Viseme(time=0.0, code=rest_viseme)]
    previous, prev_end = rest_viseme, 0.0
    for phone, start, stop in phones:
        code = phone_to_viseme(str(phone))
        if code is None:
            return None
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


def clip_timings(audio: AudioClip, field: str) -> Optional[list[PhoneTiming]]:
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
    phone_to_viseme: Callable[[str], Optional[str]] = phone_viseme,
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
    visemes = (
        phones_to_visemes(
            phones,
            total_duration=audio.duration,
            phone_to_viseme=phone_to_viseme,
            rest_viseme=rest_viseme,
        )
        if phones
        else None
    )
    if visemes is None:
        return None
    return VisemeTrack(
        visemes=visemes,
        convention=convention,
        duration=audio.duration,
        words=clip_timings(audio, "words"),
    )
