"""Art from an image model, keyed and fitted for an art package (cutan#100).

Offline: a stub generator stands in for the model; the default generator is
checked for what it hands ``aix``, not by calling a paid API.
"""

from __future__ import annotations

import json
import sys
import types

import numpy as np
import pytest
from PIL import Image

pytest.importorskip("cv2")

from cutan.art_cli import generate as cli_generate  # noqa: E402
from cutan.carve import generate as G  # noqa: E402

MAGENTA = (246, 3, 242)  # what gpt-image draws for "#ff00ff", anti-aliased
SUBJECT = (40, 110, 200)


class Painter:
    """A car with a magenta window: the subject, a hole in it, a soft edge."""

    provider, model, license = "stub", "toy-1", "cc0-1.0"

    def __init__(self, *, mode="RGB"):
        self.calls = []
        self.mode = mode

    def __call__(self, prompt, *, size, background, quality=None, model=None):
        self.calls.append(
            dict(prompt=prompt, size=size, background=background, model=model)
        )
        w, h = (int(x) for x in size.split("x"))
        im = Image.new("RGB", (w, h), MAGENTA)
        im.paste(SUBJECT, (w // 8, h // 4, 7 * w // 8, 3 * h // 4))
        im.paste(MAGENTA, (w // 3, h // 3, w // 2, h // 2))  # the window
        im.paste((143, 57, 221), (w // 8 - 1, h // 4, w // 8, 3 * h // 4))  # spilt rim
        if self.mode == "RGBA":
            im = im.convert("RGBA")
            im.putpixel((w // 2 + 4, h // 2 + 4), (*SUBJECT, 0))  # model's own alpha
        return im


SPEC = {
    "car": {"prompt": "a car, magenta windows", "size": "160x96", "key": "magenta"},
    "road": {"prompt": "a road", "size": "160x96", "fit": [80, 40]},
}


def test_the_key_makes_the_backdrop_and_the_window_see_through(tmp_path):
    (car, road) = G.generate_art(SPEC, out_dir=tmp_path, generator=Painter())
    a = np.asarray(Image.open(car.path))
    assert a.shape == (96, 160, 4)
    assert a[2, 2, 3] == 0, "the backdrop is keyed"
    assert a[40, 65, 3] == 0, "the window is keyed"
    assert a[60, 40, 3] == 255 and tuple(a[60, 40, :3]) == SUBJECT
    # the rim keeps no magenta: what is visible is the subject's colour
    visible = a[a[..., 3] > 0][:, :3].astype(int)
    assert not (
        (visible[:, 0] > 120) & (visible[:, 1] < 60) & (visible[:, 2] > 120)
    ).any()
    # an unkeyed spec is the model's image, fitted
    assert Image.open(road.path).size == (80, 40) and road.size == (80, 40)


def test_the_models_own_alpha_is_kept(tmp_path):
    (car,) = G.generate_art(
        SPEC, out_dir=tmp_path, generator=Painter(mode="RGBA"), only=["car"]
    )
    assert np.asarray(Image.open(car.path))[52, 84, 3] == 0


def test_the_provenance_is_recorded_beside_the_images(tmp_path):
    G.generate_art(SPEC, out_dir=tmp_path, generator=Painter(), only=["car"])
    G.generate_art(SPEC, out_dir=tmp_path, generator=Painter(), only=["road"])
    sources = json.loads((tmp_path / G.SOURCES_FILE).read_text())
    assert set(sources) == {"car.png", "road.png"}, "a second run merges, not replaces"
    car = sources["car.png"]
    assert (car["provider"], car["id"], car["license"]) == ("stub", "toy-1", "cc0-1.0")
    assert (
        car["extra"]["prompt"] == SPEC["car"]["prompt"]
        and car["extra"]["key"] == "magenta"
    )


def test_an_existing_image_is_kept_not_paid_for_twice(tmp_path):
    G.generate_art(SPEC, out_dir=tmp_path, generator=Painter(), only=["car"])
    painter = Painter()
    made = G.generate_art(SPEC, out_dir=tmp_path, generator=painter)
    assert [(a.name, a.kept) for a in made] == [("car", True), ("road", False)]
    assert [c["prompt"] for c in painter.calls] == [SPEC["road"]["prompt"]]
    assert made[0].source.extra["prompt"] == SPEC["car"]["prompt"], "read from the record"
    assert not (tmp_path / "road.raw.png").exists(), "the raw image goes once the PNG is written"
    G.generate_art(SPEC, out_dir=tmp_path, generator=painter, overwrite=True, keep_raw=True)
    assert (tmp_path / "car.raw.png").exists() and len(painter.calls) == 3


def test_a_failure_after_the_generation_keeps_the_paid_image_and_a_rerun_uses_it(
    tmp_path, monkeypatch
):
    real_key = G.key_backdrop
    calls = {"n": 0}

    def key_that_breaks_after_the_probe(image, key):
        calls["n"] += 1
        if image.size != (2, 2):  # the pre-payment probe passes; the real key fails
            raise RuntimeError("the key broke")
        return real_key(image, key)

    monkeypatch.setattr(G, "key_backdrop", key_that_breaks_after_the_probe)
    painter = Painter()
    with pytest.raises(RuntimeError):
        G.generate_art(SPEC, out_dir=tmp_path, generator=painter, only=["car"])
    assert (tmp_path / "car.raw.png").exists() and not (tmp_path / "car.png").exists()
    record = json.loads((tmp_path / G.SOURCES_FILE).read_text())
    assert record["car.png"]["extra"]["prompt"] == SPEC["car"]["prompt"], "recorded at once"
    monkeypatch.setattr(G, "key_backdrop", real_key)
    (car,) = G.generate_art(SPEC, out_dir=tmp_path, generator=painter, only=["car"])
    assert len(painter.calls) == 1, "the rerun keyed the paid image, not a new one"
    assert car.source.sha256 and not (tmp_path / "car.raw.png").exists()


def test_a_broken_record_is_named_not_a_traceback(tmp_path):
    (tmp_path / G.SOURCES_FILE).write_text("{ cut off")
    with pytest.raises(ValueError, match="art_sources.json"):
        G.generate_art(SPEC, out_dir=tmp_path, generator=Painter(), only=["road"])


def test_a_misspelt_or_malformed_key_fails_before_anything_is_paid_for(tmp_path):
    painter = Painter()
    for key in ("magneta", {"matte": "chroma", "hue": "pink"}):
        with pytest.raises(ValueError, match="key"):
            G.generate_art(
                {"car": {**SPEC["car"], "key": key}}, out_dir=tmp_path, generator=painter
            )
    assert painter.calls == []


def test_the_magenta_key_keeps_pink_and_purple_subject_colours():
    colours = {"orchid": (218, 112, 214), "lavender": (230, 230, 250),
               "deep pink": (255, 20, 147), "violet": (238, 130, 238)}  # fmt: skip
    im = Image.new("RGB", (8 * len(colours), 8), MAGENTA)
    for i, c in enumerate(colours.values()):
        im.paste(c, (8 * i + 2, 2, 8 * i + 6, 6))
    a = np.asarray(G.key_backdrop(im, "magenta"))[..., 3]
    assert a[0, 0] == 0
    kept = {name: int(a[4, 8 * i + 4]) for i, name in enumerate(colours)}
    assert all(v == 255 for v in kept.values()), kept


def test_the_record_names_the_models_provider_and_the_pngs_digest(tmp_path, monkeypatch):
    class OtherProvider(G.AixGenerator):
        def __call__(self, prompt, **kw):
            return Painter()(prompt, **kw)

    (car,) = G.generate_art(
        {"car": {**SPEC["car"], "model": "gemini/imagen-4.0-generate-001"}},
        out_dir=tmp_path,
        generator=OtherProvider(),
    )
    assert (car.source.provider, car.source.license) == ("gemini", None)
    import hashlib

    assert car.source.sha256 == hashlib.sha256(car.path.read_bytes()).hexdigest()
    assert G.generate_art(SPEC, out_dir=tmp_path / "b", generator=Painter(), only=[]) == []


def test_the_spec_is_checked_before_anything_is_generated(tmp_path):
    with pytest.raises(ValueError, match="no such art"):
        G.generate_art(SPEC, out_dir=tmp_path, generator=Painter(), only=["boat"])
    for bad, match in (
        ({"x": {"prompt": " "}}, "prompt is empty"),
        ({"x": {"prompt": "p", "background": "clear"}}, "opaque"),
        ({"x": {"prompt": "p", "fit": [0, 10]}}, "positive"),
        ({"x": {"prompt": "p", "colour": "red"}}, "'x'"),
        ({"x": {"prompt": "p", "fit": "1280x720"}}, "fit is"),
        ({"x": {"prompt": "p", "fit": [1, 2, 3]}}, "fit is"),
        ({"x": {"prompt": "p", "size": "huge"}}, "size"),
        ({"x": "a prompt"}, "'x'"),
        ([{"prompt": "p"}], "mapping"),
        ({"x": {"prompt": 3}}, "not text"),
        ({"x": {"prompt": "p", "fit": [1.7, 2.2]}}, "whole numbers"),
        ({"x": {"prompt": "p", "size": "0x0"}}, "size"),
        ({"../x": {"prompt": "p"}}, "file name"),
    ):
        with pytest.raises(ValueError, match=match):
            G.art_specs(bad)
    spec_file = tmp_path / "spec.json"
    spec_file.write_text(
        json.dumps({"cabin": {"prompt": "a cabin", "key_magenta": True}})
    )
    assert G.art_specs(spec_file)[0].key == "magenta"


def test_a_spec_names_its_model_and_the_record_says_which(tmp_path):
    painter = Painter()
    spec = {"car": {**SPEC["car"], "model": "gpt-image-1.5"}}
    (car,) = G.generate_art(spec, out_dir=tmp_path, generator=painter)
    assert painter.calls[0]["model"] == "gpt-image-1.5"
    assert car.source.id == "gpt-image-1.5"


def test_the_default_generator_asks_aix_for_base64_and_the_background(monkeypatch):
    seen = {}

    def generate_image(prompt, **kw):
        seen.update(kw, prompt=prompt)
        buf = __import__("io").BytesIO()
        Image.new("RGB", (8, 8), MAGENTA).save(buf, "PNG")
        return types.SimpleNamespace(as_bytes=lambda: buf.getvalue())

    monkeypatch.setitem(
        sys.modules, "aix", types.SimpleNamespace(generate_image=generate_image)
    )
    im = G.AixGenerator()("p", size="1024x1024", background="transparent")
    assert im.size == (8, 8)
    assert seen["response_format"] is None and seen["background"] == "transparent"
    assert seen["model"] == G.DEFAULT_MODEL and "quality" not in seen, "the provider's default"


def test_the_cli_writes_and_reports(tmp_path, monkeypatch):
    monkeypatch.setattr(G, "AixGenerator", lambda **_: Painter())
    spec_file = tmp_path / "spec.json"
    spec_file.write_text(json.dumps(SPEC))
    text = cli_generate(str(spec_file), str(tmp_path / "plates"), only="road")
    assert "road.png  80x40" in text and "art_sources.json" in text
    assert not (tmp_path / "plates" / "car.png").exists()


def test_a_palette_image_is_fitted_smoothly():
    im = Image.new("RGB", (40, 20), (255, 255, 255))
    im.paste((0, 0, 0), (0, 0, 20, 20))
    fitted = G.cover_fit(im.convert("P"), (20, 10))
    assert fitted.mode == "RGBA"
    assert len({px[:3] for px in fitted.getdata()}) > 2, "resampled, not nearest"


def test_a_prop_is_carved_by_its_key_and_written_with_its_source(tmp_path):
    """cutan#162: a generated part goes through carve() and write_prop."""
    spec = {"mug": {"prompt": "a mug on magenta", "size": "160x96", "key": "magenta",
                    "prop": {"point": [40, 48], "landmarks": {"grip": [30, 40]}}}}  # fmt: skip
    painter = Painter()
    (mug,) = G.generate_art(spec, out_dir=tmp_path, generator=painter)
    assert mug.path == tmp_path / "mug" / "prop.json"
    doc = json.loads(mug.path.read_text())
    assert doc["kind"] == "PropDescriptor"
    assert doc["source"]["provider"] == "stub" and doc["source"]["extra"]["prompt"] == "a mug on magenta"
    assert any(b["name"] == "grip" for b in doc["bones"]), "the landmark is a bone"
    assert list((tmp_path / "mug" / "parts").glob("*.png"))
    assert not (tmp_path / "mug.raw.png").exists()
    record = json.loads((tmp_path / G.SOURCES_FILE).read_text())
    assert "mug/prop.json" in record
    again = G.generate_art(spec, out_dir=tmp_path, generator=painter)
    assert again[0].kept and len(painter.calls) == 1, "an existing prop is not paid for twice"


def test_a_prop_spec_is_checked_before_payment():
    for entry, match in (
        ({"prompt": "p", "prop": {"colour": "red"}}, "prop is a mapping"),
        ({"prompt": "p", "prop": {}, "fit": [10, 10]}, "for plates"),
        ({"prompt": "p", "prop": {}, "background": "transparent"}, "for plates"),
    ):
        with pytest.raises(ValueError, match=match):
            G.art_specs({"x": entry})
