"""OfflineLipSync — deterministic transcript → viseme track. No network, no binary.

The default lip-sync provider for `an`. Maps each meaningful character of the
transcript to a Rhubarb-convention viseme letter (A–H + X), then distributes
keyframes evenly across the audio's duration. Repeated visemes get collapsed
into a single keyframe so the mouth doesn't "stutter" on long vowel runs.

Crude but visible. Use ``RhubarbLipSync`` for real phoneme alignment once
you've installed the Rhubarb binary.

A clip that knows its timings is followed instead of spread: its phones first
(``AudioClip.phones``, a take timed by a forced aligner, an#491: each phone's own
mouth shape, :mod:`cutan.audio.phones`), else its words (``AudioClip.words``,
an#490: each word's letters over its span).

>>> from an.audio.tts import AudioClip
>>> ls = OfflineLipSync()
>>> track = ls.align(AudioClip(duration=1.0, transcript="hello"), "hello")
>>> track.convention
'rhubarb'
>>> track.duration
1.0
>>> len(track.visemes) >= 2
True
"""

from __future__ import annotations

from typing import Iterable

from an.audio.lipsync import Viseme, VisemeTrack, word_timings_to_visemes
from an.audio.tts import AudioClip

from cutan.audio.phones import PhoneToViseme, clip_timings, phone_viseme, phones_track

# Map a single ASCII character (lowercased) to a Rhubarb viseme letter.
# A=closed (P/B/M, rest), B=tight open (D/S/T/Z/N/L), C=eh, D=ah/wide,
# E=ohh, F=ooh, G=teeth-on-lip (F/V), H=th, X=idle.
_CHAR_TO_VISEME: dict[str, str] = {
    # closed lips
    "p": "A",
    "b": "A",
    "m": "A",
    # teeth-on-lip
    "f": "G",
    "v": "G",
    # th-ish
    "h": "C",
    # vowel families
    "a": "D",
    "e": "C",
    "i": "B",
    "o": "E",
    "u": "F",
    "y": "B",
    # alveolar consonants
    "d": "B",
    "t": "B",
    "s": "B",
    "z": "B",
    "n": "B",
    "l": "B",
    "r": "B",
    # remaining consonants — neutral semi-open
    "c": "C",
    "g": "C",
    "j": "C",
    "k": "C",
    "q": "C",
    "w": "F",
    "x": "C",
}
_REST_VISEME: str = "X"


def clip_words(audio: AudioClip) -> list[tuple[str, float, float]] | None:
    """The word timings ``audio`` carries (``AudioClip.words``, a recorded take
    imported with a timed transcript — an#490), as a list; ``None`` when it has
    none or when the core predates the field.

    >>> clip_words(AudioClip(duration=1.0)) is None
    True
    """
    return clip_timings(audio, "words")


class OfflineLipSync:
    """Default lip-sync provider: deterministic char-to-viseme mapping.

    Implements the ``LipSyncProvider`` protocol.
    """

    name: str = "offline"
    convention: str = "rhubarb"
    #: A pure function of the transcript, and nothing is billed: ``an cache gc``
    #: may re-make a missing track in memory (an#311, cutan#29).
    repeatable: bool = True
    billed: bool = False

    def __init__(
        self,
        *,
        char_to_viseme: dict[str, str] | None = None,
        phone_to_viseme: PhoneToViseme = phone_viseme,
    ) -> None:
        self._mapping = (
            dict(char_to_viseme) if char_to_viseme else dict(_CHAR_TO_VISEME)
        )
        self._phone_to_viseme = phone_to_viseme

    def align(self, audio: AudioClip, transcript: str) -> VisemeTrack:
        # The aligner said which sound is when (an#491): each phone's own mouth
        # shape, not a word's letters spread over its span (a word with no
        # phones under it keeps its letters). A phone the table does not know
        # leaves this to the words below.
        from_phones = phones_track(
            audio,
            phone_to_viseme=self._phone_to_viseme,
            char_to_viseme=self._mapping,
            rest_viseme=_REST_VISEME,
            convention=self.convention,
        )
        if from_phones is not None:
            return from_phones
        words = clip_words(audio)
        if words:
            # The clip knows when its words were spoken (a recorded take imported
            # with a timed transcript, an#490): the mouth follows them, as the
            # whisper provider's does, instead of an even spread over the clip.
            return VisemeTrack(
                visemes=word_timings_to_visemes(
                    words,
                    total_duration=audio.duration,
                    char_to_viseme=self._mapping,
                    rest_viseme=_REST_VISEME,
                ),
                convention=self.convention,
                duration=audio.duration,
                words=words,
            )
        codes = list(self._codes_for(transcript))
        if not codes:
            # Empty transcript → just rest at start, rest at end.
            return VisemeTrack(
                visemes=[
                    Viseme(time=0.0, code=_REST_VISEME),
                    Viseme(time=max(0.0, audio.duration), code=_REST_VISEME),
                ],
                convention=self.convention,
                duration=audio.duration,
            )
        # Distribute one keyframe per code over [0, duration].
        n = len(codes)
        duration = max(audio.duration, 1e-3)
        visemes: list[Viseme] = []
        # Always lead with rest at t=0
        visemes.append(Viseme(time=0.0, code=_REST_VISEME))
        for i, code in enumerate(codes):
            t = (i + 1) / (n + 1) * duration
            visemes.append(Viseme(time=t, code=code))
        # Trailing rest
        visemes.append(Viseme(time=duration, code=_REST_VISEME))
        return VisemeTrack(
            visemes=visemes, convention=self.convention, duration=audio.duration
        )

    def _codes_for(self, transcript: str) -> Iterable[str]:
        """Per-character viseme codes; collapses adjacent duplicates."""
        previous: str | None = None
        for raw in transcript:
            ch = raw.lower()
            if not ch.isalpha():
                # Spaces, punctuation → mouth rest. Insert if not redundant.
                if previous != _REST_VISEME:
                    previous = _REST_VISEME
                    yield _REST_VISEME
                continue
            code = self._mapping.get(ch, "C")
            if code == previous:
                continue
            previous = code
            yield code
