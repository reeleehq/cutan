"""The bench's corpus API, rooted at THIS repository's cut-out corpus.

Tests moved here from ``an`` call ``repo_root()`` and read ``DFLT_FIXTURES``; in cutan
those are the cut-out corpus (:mod:`cutan.bench`) and this checkout.
"""

from __future__ import annotations

from pathlib import Path

from cutan.bench import CUTOUT_FIXTURES as DFLT_FIXTURES  # noqa: F401
from cutan.bench import REPO_ROOT


def repo_root() -> Path:
    """This checkout (the one that holds ``misc/bench/``)."""
    return REPO_ROOT


def run_bench(**kwargs):
    """``an.bench.run.run_bench`` rooted at this checkout."""
    from an.bench.run import run_bench as _run

    return _run(root=REPO_ROOT, **kwargs)
