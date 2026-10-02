"""Test helpers shared by several of cutan's tests (copied from ``an``'s tests, which keep theirs)."""

from __future__ import annotations

import io
import math
import wave

from an.audio.lipsync import Viseme, VisemeTrack

RATE = 22050
TONE_HZ = 440.0
DURATION_S = 1.5


def _sine_wav(hz=TONE_HZ, seconds=DURATION_S, rate=RATE) -> bytes:
    n = int(rate * seconds)
    frames = b"".join(
        int(12000 * math.sin(2 * math.pi * hz * i / rate)).to_bytes(2, "little", signed=True)
        for i in range(n)
    )
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(frames)
    return buf.getvalue()


class _RecordingLipSync:
    """Aligns nothing; records the audio it was handed."""

    name = "recording"
    convention = "rhubarb"

    def __init__(self):
        self.heard: list[bytes] = []

    def align(self, audio, transcript):
        self.heard.append(audio.bytes_)
        return VisemeTrack(visemes=[Viseme(0.0, "X")], duration=audio.duration)


def _extract_js_block(src: str, start_marker: str) -> str:
    """Lift a brace-delimited definition out of the runtime.js IIFE."""
    start = src.index(start_marker)
    i = src.index("{", start)
    depth = 0
    for j in range(i, len(src)):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                end = j + 1
                if src[end : end + 1] == ";":
                    end += 1
                return src[start:end]
    raise AssertionError(f"unbalanced braces after {start_marker!r}")
