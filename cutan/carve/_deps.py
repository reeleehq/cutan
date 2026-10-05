"""The optional dependencies of ``cutan.carve``, imported lazily with an install hint.

Carving needs OpenCV (``pip install "cutan[carve]"``); two matte strategies
need more: ``rembg`` (``cutan[rembg]``) and the face locator ``insightface``
(``cutan[faces]``). Nothing here is imported until a carve runs, so
``import cutan`` stays light.
"""

from __future__ import annotations

import importlib
import importlib.util
from types import ModuleType

#: ``{import name: (what needs it, the install command)}``.
OPTIONAL_DEPENDENCIES: dict[str, tuple[str, str]] = {
    "cv2": ("carving (every matte strategy)", 'pip install "cutan[carve]"'),
    "rembg": ("the rembg matte", 'pip install "cutan[rembg]"'),
    "insightface": ("the face locator of carve_head", 'pip install "cutan[faces]"'),
}


class MissingDependencyError(ImportError):
    """An optional dependency of ``cutan.carve`` is not installed."""


def require(name: str) -> ModuleType:
    """Import ``name``, or raise :class:`MissingDependencyError` saying how to install it."""
    try:
        return importlib.import_module(name)
    except ImportError as e:
        need, cmd = OPTIONAL_DEPENDENCIES.get(name, (name, f"pip install {name}"))
        raise MissingDependencyError(
            f"{need} needs {name!r}, which is not installed: {cmd}"
        ) from e


def cv2() -> ModuleType:
    """OpenCV."""
    return require("cv2")


def check_requirements(*, verbose: bool = True) -> dict[str, bool]:
    """Which optional dependencies of carving are installed (printing how to get the rest).

    >>> sorted(check_requirements(verbose=False))
    ['cv2', 'insightface', 'rembg']
    """
    found = {
        name: importlib.util.find_spec(name) is not None
        for name in OPTIONAL_DEPENDENCIES
    }
    if verbose:
        for name, ok in found.items():
            need, cmd = OPTIONAL_DEPENDENCIES[name]
            print(
                f"{'ok     ' if ok else 'missing'} {name:12s} {need}"
                + ("" if ok else f": {cmd}")
            )
    return found
