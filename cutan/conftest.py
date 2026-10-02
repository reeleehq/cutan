"""Doctest collection for ``cutan``: ``nw`` is an optional dependency of ``cutan.nw`` only."""

collect_ignore: list[str] = []

try:  # pragma: no cover - depends on the environment, not the code
    import nw  # noqa: F401
except ImportError:  # pragma: no cover
    collect_ignore.append("nw.py")
