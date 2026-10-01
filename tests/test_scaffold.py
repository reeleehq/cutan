"""The scaffold's promises: cutan's persisted names agree with the core's, and the
genre is discoverable from exactly one distribution at every step of the move."""

from importlib.metadata import PackageNotFoundError, distribution

import pytest

import cutan


def test_entry_point_group_is_the_core_one():
    from an.genres import ENTRY_POINT_GROUP

    assert cutan.ENTRY_POINT_GROUP == ENTRY_POINT_GROUP


def test_the_genre_is_discoverable_once_by_its_reserved_name():
    """`an.genres` de-duplicates by entry-point name, so whichever distribution
    ships the genre (`an` today, cutan after the move), there is one."""
    from an.genres import discovered_entry_points

    found = [ep for ep in discovered_entry_points() if ep.name == cutan.ENTRY_POINT_NAME]
    assert len(found) == 1, found


def test_cutan_declares_no_genre_until_the_genre_object_moves():
    """Flip this test in the batch that moves `CUTOUT` here (an#225): from then on
    this distribution declares exactly `ENTRY_POINT_NAME = ENTRY_POINT_VALUE`."""
    try:
        eps = distribution("cutan").entry_points
    except PackageNotFoundError:  # running from a source tree that is not installed
        pytest.skip("cutan is not installed, so it has no entry points to inspect")
    assert [ep for ep in eps if ep.group == cutan.ENTRY_POINT_GROUP] == []


def test_library_root_is_cutan_s_own():
    from an.library.root import library_root

    root = library_root(package=cutan.LIBRARY_NAME, environ={"CUTAN_HOME": "/srv/cutan-lib"})
    assert root.as_posix() == "/srv/cutan-lib"
