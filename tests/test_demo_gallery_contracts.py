"""Contracts of the demo gallery and the supersample test that `an`'s tests used to read as source.

`an` keeps the generic halves (the GIF recipe, the cross-arch capture's call); the parts
that read THIS repository's files live here (an#225).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_the_gif_recipe_has_one_home_in_an_media_gif():
    source = (ROOT / "misc" / "demos" / "build_demos.py").read_text(encoding="utf-8")
    assert "palettegen" not in source, "the recipe has one home, an.media.gif"


def test_the_demo_gallery_renders_cold_like_the_bench():
    demos = (ROOT / "misc" / "demos" / "build_demos.py").read_text(encoding="utf-8")
    # The two direct `render(...)` calls, and `_render` for every other demo.
    assert demos.count("incremental=False") == 2
    assert 'kwargs.setdefault("incremental", False)' in demos


def test_the_supersample_contract_is_asserted_where_chromium_frames_exist():
    """`an`'s lane has no Pillow-and-Chromium; the behavioural test is in this repo and must keep its size assertion."""
    behavioural = (Path(__file__).with_name("test_cutout_render.py")).read_text(encoding="utf-8")
    assert "def test_a_supersampled_render_puts_declared_size_frames_on_disk" in behavioural
    assert "read_png_dimensions" in behavioural


def test_the_demo_builder_keeps_its_throwaway_characters_out_of_the_real_registry(
    monkeypatch, tmp_path
):
    """``misc/demos/build_demos.py`` draws characters into temp projects; each run once left ~60 records behind (an#302)."""
    from an.library import registry

    spec = importlib.util.spec_from_file_location(
        "_build_demos_redirect_test", ROOT / "misc" / "demos" / "build_demos.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # a slots dataclass resolves its module by name
    try:
        spec.loader.exec_module(module)
        sentinel = tmp_path / "before"
        monkeypatch.setattr(registry, "_account_home", lambda: sentinel)
        home = module._keep_machine_registry_private()
        assert registry._account_home() == home != sentinel
    finally:
        sys.modules.pop(spec.name, None)
