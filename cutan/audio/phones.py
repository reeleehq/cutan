"""Phones to mouth shapes: the core's tables (``an.audio.phones``), and this genre's art direction.

The phone to Rhubarb-shape mapping, the alphabet detection and the phone-track
builder live in the core (``an.audio.phones``, an#727); this module re-exports
them under their old names and adds what is the cut-out genre's own:
:data:`TONGUE_ONLY_INTENSITY` (cutan#157), passed as ``intensity_of=``.

>>> [(v.time, v.code) for v in phones_to_visemes(
...     [("HH", 0.1, 0.2), ("AH0", 0.2, 0.3), ("L", 0.3, 0.4), ("OW1", 0.4, 0.6)],
...     total_duration=1.0,
... )]
[(0.0, 'X'), (0.1, 'C'), (0.3, 'H'), (0.4, 'F'), (0.6, 'X'), (1.0, 'X')]
"""

from __future__ import annotations

from collections.abc import Mapping

from an.audio.phones import (  # noqa: F401 - re-exported, the persisted import path
    ARPABET_TO_VISEME,
    DEFAULT_LETTER_VISEME,
    IPA_TO_VISEME,
    MIN_GAP_FOR_REST_S,
    NO_INTENSITY,
    REST_VISEME,
    SILENCES,
    TAKES_NEXT_SHAPE,
    PhoneToViseme,
    Segment,
    Timing,
    clip_timings,
    phone_alphabet,
    phone_viseme,
    phones_to_visemes,
    phones_track,
)

#: The ``cache_version`` of the providers that read a take's phones: a lip-sync
#: track cached before they did is re-aligned once (an#727).
PHONES_CACHE_VERSION: str = "phones-1"

#: How strongly a phone's shape holds against its neighbours in the co-articulation
#: vote (``Viseme.intensity``; the vote weighs ``DOMINANCE[shape] x intensity``,
#: ``cutan.compile.coarticulate``). Rhubarb's ``B`` codes both the EE vowel (lips
#: spread) and the tongue-only consonants (T D N K...), which barely move the
#: lips (JALI, Edwards et al. 2016: "tongue-only visemes have no influence on
#: the lips"); the letter alone cannot say, the phone can. Keyed by the phone's
#: base in either alphabet (ARPAbet upper case, IPA as written); a phone not
#: listed is 1.0. Values are art direction (cutan#157): a measurement, not a
#: sourced number.
TONGUE_ONLY_INTENSITY: Mapping[str, float] = {
    **{p: 0.4 for p in ("T", "D", "N", "K", "G", "NG", "S", "Z", "L")},
    **{p: 0.4 for p in ("t", "d", "n", "k", "ɡ", "g", "ŋ", "s", "z", "l")},
}
