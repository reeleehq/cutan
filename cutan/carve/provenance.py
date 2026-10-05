"""Where carved pixels came from: an ``AssetSource`` for a frame of a video or an image.

Provenance by construction: a carve takes its source at the start, and the
part folder it writes carries it in the descriptor's ``source``, so
``an library publish`` records the rights without flags, and ``an credits``
lists the part as what it is (``all-rights-reserved`` footage you do not own
is NOT PUBLISHABLE, and says so).

The licence is never guessed: :func:`frame_source` requires one.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from an.ir.assets import AssetSource

__all__ = ["frame_source", "youtube_id"]

_YT_HOSTS = ("youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be")


def youtube_id(url: str) -> str | None:
    """The video id of a YouTube URL, else ``None``.

    >>> youtube_id("https://www.youtube.com/watch?v=AAGIi62-sAU&t=34")
    'AAGIi62-sAU'
    >>> youtube_id("https://youtu.be/AAGIi62-sAU?t=3"), youtube_id("https://example.org/a.png")
    ('AAGIi62-sAU', None)
    """
    parts = urlsplit(url)
    host = parts.netloc.lower()
    if host == "youtu.be":
        vid = parts.path.lstrip("/").split("/")[0]
        return vid or None
    if host.endswith("youtube.com"):
        q = dict(parse_qsl(parts.query))
        if "v" in q:
            return q["v"]
        m = re.match(r"/(?:shorts|embed|live)/([^/?#]+)", parts.path)
        return m.group(1) if m else None
    return None


def _with_time(url: str, t: float) -> str:
    """``url`` with its ``t`` query parameter set to whole seconds (YouTube's deep link)."""
    parts = urlsplit(url)
    q = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k != "t"]
    q.append(("t", str(int(t))))
    return urlunsplit(parts._replace(query=urlencode(q)))


def frame_source(
    url: str | None,
    *,
    license: str | None,
    t: float | None = None,
    author: str | None = None,
    author_url: str | None = None,
    title: str | None = None,
    provider: str | None = None,
    attribution: str | None = None,
    note: str | None = None,
    cacheable: bool = True,
    **extra: Any,
) -> AssetSource:
    """The provenance of a part carved from ``url`` (a video at time ``t``, or an image).

    ``license`` is required (keyword-only, no default): ``None`` records the
    rights as UNKNOWN, which is a statement too. For footage you do not own,
    ``"all-rights-reserved"`` (``an credits`` then lists the part as NOT
    PUBLISHABLE). A YouTube URL gets the provider, its video id, a deep link
    with ``&t=`` and the plain watch page as ``source_page_url``. ``t`` and
    ``title`` go into ``extra`` beside any other keyword.

    >>> s = frame_source("https://www.youtube.com/watch?v=AAGIi62-sAU",
    ...                  t=34.6, license="all-rights-reserved", author="OverSimplified")
    >>> s.provider, s.id, s.url
    ('youtube', 'AAGIi62-sAU', 'https://www.youtube.com/watch?v=AAGIi62-sAU&t=34')
    >>> s.source_page_url, s.extra["frame_time_s"]
    ('https://www.youtube.com/watch?v=AAGIi62-sAU', 34.6)
    """
    vid = youtube_id(url) if url else None
    page = None
    if vid is not None:
        provider = provider or "youtube"
        page = f"https://www.youtube.com/watch?v={vid}"
        if t is not None:
            url = _with_time(page, t)
    elif provider is None:
        provider = urlsplit(url).netloc if url else "local"
    if t is not None:
        extra["frame_time_s"] = float(t)
    if title is not None:
        extra["title"] = title
    if note is not None:
        extra["note"] = note
    if attribution is None and url:
        when = f" at {t:g} s" if t is not None else ""
        by = f" by {author}" if author else ""
        attribution = (
            f"Carved from {title or url}{by}{when} ({license or 'licence unknown'})."
        )
    return AssetSource(
        provider=provider,
        id=vid,
        url=url,
        source_page_url=page,
        license=license,
        author=author,
        author_url=author_url,
        attribution=attribution,
        cacheable=cacheable,
        extra=extra,
    )
