"""The super-resolution seam of cutan.carve (cutan#110): ``carve(superres=...)``.

The part keeps the strategy's resolution and every coordinate stays in the
source's pixels. The model strategy is tested through an injected session (a
nearest-neighbour stand-in, so the tiling can be checked exactly) and, where
the model file is already cached, on the real model.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

pytest.importorskip("cv2", reason="carving needs OpenCV: pip install 'cutan[carve]'")

import cv2  # noqa: E402

from cutan.carve import carve, carve_head, frame_source, write_prop  # noqa: E402
from cutan.carve.superres import (  # noqa: E402
    MODELS,
    RealESRGAN,
    Resample,
    as_superres,
    models_dir,
)

FIX = Path(__file__).resolve().parent / "fixtures" / "carve"


def _img(name):
    return Image.open(FIX / f"{name}.png").convert("RGB")


def _mask(name):
    return np.asarray(Image.open(FIX / f"{name}_mask.png")) > 127


def _iou_at_source(part, truth):
    """IoU with the source-sized truth of a carving brought back to the source's pixels."""
    k = part.scale
    a = part.alpha
    small = cv2.resize(
        a, (round(a.shape[1] / k), round(a.shape[0] / k)), interpolation=cv2.INTER_AREA
    )
    full = np.zeros(truth.shape, bool)
    x0, y0 = (round(v) for v in part.offset)
    h, w = small.shape
    full[y0 : y0 + h, x0 : x0 + w] = (small > 0.5)[
        : truth.shape[0] - y0, : truth.shape[1] - x0
    ]
    return (full & truth).sum() / (full | truth).sum()


class _Nearest:
    """A stand-in for an ONNX session: ``factor``x nearest neighbour, on fixed tiles."""

    def __init__(self, factor=4, tile=256):
        self.factor, self.tile, self.calls = factor, tile, 0

    def get_inputs(self):
        return [type("I", (), {"name": "input"})()]

    def run(self, names, feeds):
        (x,) = feeds.values()
        assert x.shape == (1, 3, self.tile, self.tile) and x.dtype == np.float32
        self.calls += 1
        return [x.repeat(self.factor, axis=2).repeat(self.factor, axis=3)]


def test_the_part_keeps_the_superresolved_pixels_in_source_coordinates():
    img = _img("cartoon")
    plain = carve(img, point=(160, 150), detach=3)
    big = carve(img, point=(160, 150), detach=3, superres=Resample(3))
    assert big.scale == 3.0 and plain.scale == 1.0
    # three times the pixels, the same anchor, the same place in the source
    assert (
        abs(big.size[0] - 3 * plain.size[0]) <= 3
        and abs(big.size[1] - 3 * plain.size[1]) <= 3
    )
    assert np.allclose(big.anchor, plain.anchor, atol=0.01)
    ((ax, ay),) = big.to_part([(160, 150)])
    assert (ax / big.size[0], ay / big.size[1]) == pytest.approx(big.anchor)
    assert big.meta["source_to_part"][0][0] == 3.0
    assert _iou_at_source(big, _mask("cartoon")) > 0.97
    # the recipe names the strategy and replays the carve
    assert big.recipe["superres"] == {
        "superres": "resample",
        "factor": 3,
        "method": "cubic",
    }
    assert (
        "superres" not in plain.recipe
    )  # a carve without it records what it always did
    again = carve(img, **big.recipe)
    assert again.recipe == big.recipe and again.size == big.size


def test_provenance_and_the_prop_record_the_strategy(tmp_path):
    src = frame_source(
        "https://www.youtube.com/watch?v=abcdefghijk",
        t=3,
        license="all-rights-reserved",
    )
    part = carve(
        _img("cartoon"), point=(160, 150), detach=3, superres="resample", source=src
    )
    doc = write_prop(part, tmp_path / "p")
    assert doc.source.extra["carve"]["recipe"]["superres"]["superres"] == "resample"
    assert tuple(doc.view_box[2:]) == part.size  # the prop is drawn from all of them


def test_the_model_runs_in_overlapping_tiles_with_no_seam():
    rng = np.random.default_rng(0)
    rgb = rng.integers(0, 256, (300, 530, 3), dtype=np.uint8)  # several tiles each way
    session = _Nearest()
    sr = RealESRGAN(session=session)
    out = sr(rgb)
    assert out.shape == (1200, 2120, 3) and sr.factor == 4
    assert (
        session.calls == 2 * 3
    )  # 224 px of new pixels per tile at the default overlap
    assert np.array_equal(out, rgb.repeat(4, axis=0).repeat(4, axis=1))
    # an injected session made these pixels, not the pinned model: said, and not replayable
    assert sr.recipe() == {
        "superres": "realesr-animevideov3",
        "overlap": 16,
        "session": "injected",
    }
    with pytest.raises(ValueError, match="cannot be replayed"):
        as_superres(sr.recipe())
    pinned = RealESRGAN().recipe()
    assert pinned["sha256"] == MODELS["realesr-animevideov3"].sha256
    assert as_superres(pinned).recipe() == pinned
    with pytest.raises(ValueError, match="never runs another model"):
        as_superres({**pinned, "sha256": "0" * 64})
    tiny = RealESRGAN(session=_Nearest())(
        rgb[:1, :3]
    )  # smaller than one tile, a single row
    assert tiny.shape == (4, 12, 3)


def test_a_callable_is_a_strategy_and_its_factor_is_read():
    part = carve(
        _img("cartoon"),
        point=(160, 150),
        detach=3,
        superres=lambda rgb: rgb.repeat(2, axis=0).repeat(2, axis=1),
    )
    assert part.scale == 2.0
    with pytest.raises(ValueError, match="not one whole factor"):
        carve(_img("cartoon"), superres=lambda rgb: rgb[:, :-1])


def test_strategies_are_named_and_checked():
    assert as_superres(None) is None
    assert as_superres({"superres": "realesr-animevideov3", "overlap": 8}).overlap == 8
    with pytest.raises(ValueError, match="no super-resolution strategy"):
        as_superres("magic")
    with pytest.raises(ValueError, match="no super-resolution model"):
        RealESRGAN("magic")
    with pytest.raises(ValueError, match="overlap"):
        RealESRGAN(overlap=128)
    with pytest.raises(ValueError, match="method"):
        Resample(2, method="sinc")


def test_a_thin_part_is_not_called_see_through_because_the_feather_scaled():
    img = np.full((60, 80, 3), 240, np.uint8)
    img[20:24, 10:70] = (40, 40, 40)  # a 4 px blade
    plain = carve(img, feather=1.5, detach=0)
    big = carve(img, feather=1.5, detach=0, superres=Resample(4))
    assert (
        plain.quality.soft_interior_share < 0.05
        and big.quality.soft_interior_share < 0.05
    )


def test_the_model_file_is_fetched_once_and_checked_by_hash(tmp_path, monkeypatch):
    monkeypatch.setenv("CUTAN_MODELS_DIR", str(tmp_path / "models"))
    assert models_dir() == tmp_path / "models"
    with pytest.raises(FileNotFoundError, match="huggingface.co"):
        RealESRGAN(download=False).model_file()
    wrong = tmp_path / "wrong.onnx"
    wrong.write_bytes(b"not the model")
    with pytest.raises(ValueError, match="sha256"):
        RealESRGAN(path=wrong).model_file()
    assert (
        "path" not in RealESRGAN(path=wrong).recipe()
    )  # a local path never reaches provenance
    cached = tmp_path / "models" / MODELS["realesr-animevideov3"].filename
    cached.parent.mkdir(parents=True)
    cached.write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="delete it"):
        RealESRGAN().model_file()


def test_a_head_is_normalised_from_the_superresolved_pixels():
    from tests.test_carve import _head_face

    plain = carve_head(_img("head"), face=_head_face())
    big = carve_head(_img("head"), face=_head_face(), superres=Resample(2))
    assert big.size == plain.size and big.anchor == plain.anchor
    assert big.recipe["superres"]["factor"] == 2
    assert (
        big.recipe["upscale"] == 1 and plain.recipe["upscale"] == 3
    )  # no interpolation on top
    a, b = plain.alpha > 0.5, big.alpha > 0.5
    assert (a & b).sum() / (a | b).sum() > 0.95


_MODEL = models_dir() / MODELS["realesr-animevideov3"].filename


@pytest.mark.skipif(
    not _MODEL.exists(),
    reason=f"the model is not cached at {_MODEL} (no download in tests)",
)
def test_the_real_model_sharpens_a_thin_line():
    pytest.importorskip("onnxruntime")
    img = np.full((40, 60, 3), 235, np.uint8)
    cv2.line(
        img, (5, 30), (55, 8), (40, 30, 30), 2, lineType=cv2.LINE_AA
    )  # a 2-px blade
    part = carve(img, superres="realesr-animevideov3", detach=0)
    assert part.scale == 4.0
    interp = carve(img, superres=Resample(4), detach=0)
    # the model's edge is harder than interpolation's: fewer half-transparent pixels
    soft = lambda p: float(((p.alpha > 0.1) & (p.alpha < 0.9)).mean())  # noqa: E731
    assert soft(part) < soft(interp)


def test_landmarks_of_a_superresolved_part_stay_at_their_source_points(tmp_path):
    from an.stage.rig import SCENE_PX_PER_VIEW_BOX, rig_structure

    plain = carve(_img("cartoon"), point=(160, 150), detach=3)
    big = carve(_img("cartoon"), point=(160, 150), detach=3, superres=Resample(4))
    marks = {"grip": (150, 160), "tip": (170, 120)}
    # the same prop drawn from 4x the pixels: its points land at the same scene place
    a, b = (
        rig_structure(write_prop(p, tmp_path / n, ours=True, landmarks=marks)).anchors
        for p, n in ((plain, "plain"), (big, "big"))
    )
    ka = SCENE_PX_PER_VIEW_BOX / plain.size[1]
    kb = SCENE_PX_PER_VIEW_BOX / big.size[1]
    for name in marks:
        assert np.allclose(
            np.divide(a[name].offset, ka), np.divide(b[name].offset, kb * 4), atol=0.5
        )
