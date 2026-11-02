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
        self.calls.append(dict(prompt=prompt, size=size, background=background, model=model))
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
    assert not ((visible[:, 0] > 120) & (visible[:, 1] < 60) & (visible[:, 2] > 120)).any()
    # an unkeyed spec is the model's image, fitted
    assert Image.open(road.path).size == (80, 40) and road.size == (80, 40)


def test_the_models_own_alpha_is_kept(tmp_path):
    (car,) = G.generate_art(SPEC, out_dir=tmp_path, generator=Painter(mode="RGBA"), only=["car"])
    assert np.asarray(Image.open(car.path))[52, 84, 3] == 0


def test_the_provenance_is_recorded_beside_the_images(tmp_path):
    G.generate_art(SPEC, out_dir=tmp_path, generator=Painter(), only=["car"])
    G.generate_art(SPEC, out_dir=tmp_path, generator=Painter(), only=["road"])
    sources = json.loads((tmp_path / G.SOURCES_FILE).read_text())
    assert set(sources) == {"car.png", "road.png"}, "a second run merges, not replaces"
    car = sources["car.png"]
    assert (car["provider"], car["id"], car["license"]) == ("stub", "toy-1", "cc0-1.0")
    assert car["extra"]["prompt"] == SPEC["car"]["prompt"] and car["extra"]["key"] == "magenta"


def test_an_existing_image_is_not_paid_for_twice(tmp_path):
    G.generate_art(SPEC, out_dir=tmp_path, generator=Painter(), only=["car"])
    painter = Painter()
    with pytest.raises(FileExistsError, match="car"):
        G.generate_art(SPEC, out_dir=tmp_path, generator=painter)
    assert painter.calls == [], "refused before any generation"
    G.generate_art(SPEC, out_dir=tmp_path, generator=painter, overwrite=True, keep_raw=True)
    assert (tmp_path / "car.raw.png").exists() and len(painter.calls) == 2


def test_the_spec_is_checked_before_anything_is_generated(tmp_path):
    with pytest.raises(ValueError, match="no such art"):
        G.generate_art(SPEC, out_dir=tmp_path, generator=Painter(), only=["boat"])
    for bad, match in (
        ({"x": {"prompt": " "}}, "prompt is empty"),
        ({"x": {"prompt": "p", "background": "clear"}}, "opaque"),
        ({"x": {"prompt": "p", "fit": [0, 10]}}, "positive"),
        ({"x": {"prompt": "p", "colour": "red"}}, "'x'"),
    ):
        with pytest.raises(ValueError, match=match):
            G.art_specs(bad)
    spec_file = tmp_path / "spec.json"
    spec_file.write_text(json.dumps({"cabin": {"prompt": "a cabin", "key_magenta": True}}))
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

    monkeypatch.setitem(sys.modules, "aix", types.SimpleNamespace(generate_image=generate_image))
    im = G.AixGenerator()("p", size="1024x1024", background="transparent")
    assert im.size == (8, 8)
    assert seen["response_format"] is None and seen["background"] == "transparent"
    assert seen["model"] == G.DEFAULT_MODEL and seen["quality"] == G.DEFAULT_QUALITY


def test_the_cli_writes_and_reports(tmp_path, monkeypatch):
    monkeypatch.setattr(G, "AixGenerator", lambda **_: Painter())
    spec_file = tmp_path / "spec.json"
    spec_file.write_text(json.dumps(SPEC))
    text = cli_generate(str(spec_file), str(tmp_path / "plates"), only="road")
    assert "road.png  80x40" in text and "art_sources.json" in text
    assert not (tmp_path / "plates" / "car.png").exists()
