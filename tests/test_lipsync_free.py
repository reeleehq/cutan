"""The offline lip-sync is free and repeatable, so ``an cache gc`` can re-make
missing visemes in memory (cutan#29, an#311).

A provider counts as free and repeatable (``an.audio.pipeline.free_and_repeatable``)
when it DECLARES ``repeatable = True`` and ``billed = False``. Until the
offline lip-sync did, a shot whose visemes were gone was unkeyable under the
default ``lipsync=offline``, and a forced collection could drop it although
the next offline render would have reused it. The render here is a stand-in
(no browser, no ffmpeg): the keyer is real, so "reused" is a statement about
the shot keys.
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path

import pytest

from an import init
from an.adapters._base import RenderResult
from an.audio.pipeline import free_and_repeatable
from an.build import ShotCache
from an.build.gc import collect_garbage
from an.ir.compose import tween
from an.ir.schema import Dialogue, Meta, Resolution, SceneIR, Shot
from an.project import load

from cutan.audio.offline_lipsync import OfflineLipSync
from cutan.audio.rhubarb_lipsync import RhubarbLipSync, RhubarbNotFoundError

_ENV = "e" * 64
_LATER = 60.0  # collect "a minute from now": past the protection horizon


def _env():
    return lambda renderer_name: _ENV


@pytest.fixture
def rendered(monkeypatch):
    """Stands in for the cut-out render; returns the ids it was asked to draw."""
    import an.render as render_mod
    from an.adapters.cutout.render import CutoutRenderer

    seen: list[str] = []

    def fake(self, shot, ctx):
        seen.append(shot.id)
        work = Path(ctx.work_dir) / f"shot_{shot.id}"
        frames = work / "frames"
        frames.mkdir(parents=True, exist_ok=True)
        (frames / "frame_000000.png").write_bytes(shot.id.encode())
        out = work / f"{shot.id}.mp4"
        out.write_bytes(f"mp4 of {shot.id} @ {time.time_ns()}".encode())
        return RenderResult(
            mp4_path=out,
            duration=shot.duration,
            frame_manifest=sorted(frames.glob("*.png")),
            provenance={"shot_id": shot.id},
        )

    monkeypatch.setattr(CutoutRenderer, "render", fake)
    monkeypatch.setattr(
        render_mod, "_ffmpeg_concat", lambda inputs, out: shutil.copy(list(inputs)[0], out)
    )
    return seen


def _voiced_project(tmp_path, *texts: str) -> Path:
    root = init(tmp_path / "p")
    shots = [
        Shot(
            id=f"s{i}",
            duration=3.0,
            actions=[tween("root", "x", to=10.0 + i, duration=1.0)],
            dialogue=[Dialogue(speaker="x", text=text, voice_ref="bob")],
        )
        for i, text in enumerate(texts)
    ]
    load(root).mall["scenes"]["main"] = SceneIR(
        meta=Meta(fps=12, resolution=Resolution(width=160, height=120)), timeline=shots
    )
    return root


def _render(root, seen) -> list[str]:
    from an.render import render_project

    seen.clear()
    render_project(root, incremental=ShotCache(environment=_env()), tts="offline", lipsync="offline")
    return list(seen)


def test_the_offline_and_rhubarb_lipsyncs_declare_themselves_free_and_repeatable():
    assert OfflineLipSync().repeatable is True and OfflineLipSync().billed is False
    assert free_and_repeatable(OfflineLipSync())
    assert free_and_repeatable(RhubarbLipSync(binary_path="/bin/rhubarb"))


def test_rhubarb_says_when_this_machine_cannot_run_it(monkeypatch):
    """A free provider gc re-runs must say up front when it cannot run here,
    or a missing binary would read as a bug and refuse the whole collection."""
    monkeypatch.setattr(shutil, "which", lambda name: None)
    with pytest.raises(RhubarbNotFoundError, match="rhubarb"):
        RhubarbLipSync().check_available()
    RhubarbLipSync(binary_path="/bin/rhubarb").check_available()


def test_gc_remakes_offline_visemes_in_memory_and_the_next_render_reuses_every_shot(
    tmp_path, rendered
):
    root = _voiced_project(tmp_path, "hello there", "and again")
    assert _render(root, rendered) == ["s0", "s1"]
    mall = load(root).mall
    for name in ("audio", "visemes"):
        for key in list(mall[name]):
            del mall[name][key]
    report = collect_garbage(
        root, engine=ShotCache(environment=_env()), max_age=1.0, force=True,
        now=time.time() + _LATER,
    )
    assert report.deleted == []
    assert all(p.get("lipsync") != "offline" for p, _ in report.reach.skipped)
    assert list(mall["audio"]) == [] and list(mall["visemes"]) == []  # nothing written
    assert _render(root, rendered) == []
