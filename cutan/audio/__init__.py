"""The cut-out genre's lip-sync providers: letters, Rhubarb and word timings to mouth shapes.

Moved from ``an.audio`` (an#225). ``an.audio`` keeps the protocols
(:class:`~an.audio.lipsync.LipSyncProvider`, :class:`~an.audio.lipsync.VisemeTrack`),
text-to-speech and the pipeline; a viseme only means something to a genre that
draws mouths. The genre registers these by name as ``lipsync.<name>`` services
(:mod:`cutan.genre`), which is how ``render(lipsync="offline")`` and
``an render --lipsync rhubarb`` keep working.

>>> offline_factory().name
'offline'
"""

from __future__ import annotations

from cutan.audio.injectable_lipsync import StaticWordTimings, WordTimingsLipSync
from cutan.audio.offline_lipsync import OfflineLipSync
from cutan.audio.rhubarb_lipsync import RhubarbLipSync
from cutan.audio.whisper_lipsync import WhisperLipSync

#: The language a provider aligns for when the caller says nothing (Rhubarb's
#: recognizer follows it, an#96): the same default ``an.audio.providers`` has.
DFLT_LANGUAGE: str = "en"


def offline_factory(**_: object) -> OfflineLipSync:
    """The deterministic char-to-viseme provider (the default)."""
    return OfflineLipSync()


def rhubarb_factory(*, language: str = DFLT_LANGUAGE, **_: object) -> RhubarbLipSync:
    """Rhubarb Lip Sync (needs the ``rhubarb`` binary); ``language`` picks its recognizer."""
    return RhubarbLipSync(language=language)


def whisper_factory(**_: object) -> WhisperLipSync:
    """Word timings from Whisper, distributed over the mouth shapes."""
    return WhisperLipSync()


__all__ = [
    "OfflineLipSync",
    "RhubarbLipSync",
    "StaticWordTimings",
    "WhisperLipSync",
    "WordTimingsLipSync",
    "offline_factory",
    "rhubarb_factory",
    "whisper_factory",
]
