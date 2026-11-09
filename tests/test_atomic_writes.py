"""A write killed mid-way keeps the previous file (cutan#188): the factory's part
writes, the descriptor, a carved prop, a clip's truth files and a pulled project
file all go through ``dol.atomic_write``. The kill is the final ``os.replace``
failing: the temp file has the new bytes, the target must still hold the old."""

from __future__ import annotations

import os

import pytest


@pytest.fixture()
def killed_before_replace(monkeypatch):
    def boom(*_a, **_k):
        raise OSError("killed")

    monkeypatch.setattr(os, "replace", boom)


def test_a_killed_part_write_keeps_the_previous_part(tmp_path, killed_before_replace):
    from cutan.characters import drawn

    part = tmp_path / "arm.svg"
    part.write_bytes(b"<svg>old</svg>")
    with pytest.raises(OSError):
        drawn.write_bytes(part, b"<svg>new</svg>")
    assert part.read_bytes() == b"<svg>old</svg>"


def test_a_killed_descriptor_write_keeps_the_previous_descriptor(tmp_path, monkeypatch):
    from cutan.characters.descriptor_io import (
        descriptor_path,
        load_descriptor,
        write_descriptor,
    )
    from cutan.characters.factory import new_character

    new_character(tmp_path, name="ned", seed="ned", use_dicebear=False)
    desc = load_descriptor(tmp_path / "ned")
    before = descriptor_path(tmp_path / "ned").read_bytes()
    desc.name = "renamed"
    monkeypatch.setattr(os, "replace", lambda *a, **k: (_ for _ in ()).throw(OSError("killed")))
    with pytest.raises(OSError):
        write_descriptor(tmp_path / "ned", desc)
    assert descriptor_path(tmp_path / "ned").read_bytes() == before


def test_a_killed_project_record_write_keeps_the_previous_record(tmp_path, killed_before_replace):
    from cutan.projects_store import STORE_RECORD, _write_record

    record = tmp_path / STORE_RECORD
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_bytes(b"{}")
    with pytest.raises(OSError):
        _write_record(tmp_path, {"project_id": "p", "files": {}})
    assert record.read_bytes() == b"{}"


def test_a_killed_png_save_keeps_the_previous_picture(tmp_path, killed_before_replace):
    from PIL import Image

    from cutan.carve.files import save_png

    picture = tmp_path / "a.png"
    Image.new("RGBA", (2, 2), (1, 2, 3, 255)).save(picture)
    before = picture.read_bytes()
    with pytest.raises(OSError):
        save_png(Image.new("RGBA", (2, 2), (9, 9, 9, 255)), picture)
    assert picture.read_bytes() == before


def test_a_killed_write_leaves_a_temp_the_push_keeps_local(tmp_path, killed_before_replace):
    """A write killed for real (not by a patched replace) leaves `.name.<hex>.tmp`;
    the push excludes it so a half-written file is never uploaded."""
    from cutan.projects_store import DEFAULT_PUSH_EXCLUDES
    from an.project import gitignore_matcher

    assert gitignore_matcher(DEFAULT_PUSH_EXCLUDES)("artifacts/audio/.a.wav.3f9c1d.tmp")
