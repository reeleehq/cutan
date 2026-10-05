"""Where carved pixels came from: an ``AssetSource`` for a frame of a video or an image.

Provenance by construction: a carve takes its source at the start, and the
part folder it writes carries it in the descriptor's ``source``, so
``an library publish`` records the rights without flags, and ``an credits``
lists the part as what it is (``all-rights-reserved`` footage you do not own
is NOT PUBLISHABLE, and says so).

The licence is never guessed: :func:`frame_source` requires one. A local file
is recorded by its name, never its path: a descriptor travels into libraries
and credits, and an absolute path is private information.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from an.ir.assets import AssetSource

__all__ = ["frame_source", "youtube_id"]

_YT_HOSTS = frozenset(
    {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "music.youtube.com",
        "youtube-nocookie.com",
        "www.youtube-nocookie.com",
    }
)


def _host(url: str) -> str:
    return (urlsplit(url).hostname or "").lower()


def youtube_id(url: str) -> str | None:
    """The video id of a YouTube URL, else ``None``.

    >>> youtube_id("https://www.youtube.com/watch?v=AAGIi62-sAU&t=34")
    'AAGIi62-sAU'
    >>> youtube_id("https://youtu.be/AAGIi62-sAU?t=3"), youtube_id("https://example.org/a.png")
    ('AAGIi62-sAU', None)
    >>> youtube_id("https://notyoutube.com/watch?v=x"), youtube_id("https://WWW.YOUTUBE.COM:443/shorts/abc")
    (None, 'abc')
    """
    parts = urlsplit(url)
    host = _host(url)
    if host == "youtu.be":
        vid = parts.path.lstrip("/").split("/")[0]
        return vid or None
    if host in _YT_HOSTS:
        q = dict(parse_qsl(parts.query))
        if q.get("v"):
            return q["v"]
        m = re.match(r"/(?:shorts|embed|live|v)/([^/?#]+)", parts.path)
        return m.group(1) if m else None
    return None


def _public_url(url: str) -> str:
    """``url`` without what must not be published: the user and password, the
    query (signed-URL tokens, tracking ids) and the fragment.

    >>> _public_url("https://bob:pw@cdn.example.org/a.png?X-Amz-Signature=abc#x")
    'https://cdn.example.org/a.png'
    """
    parts = urlsplit(url)
    host = parts.hostname or ""
    netloc = f"{host}:{parts.port}" if parts.port else host
    return urlunsplit((parts.scheme, netloc, parts.path, "", ""))


def _url_time(url: str) -> float | None:
    """The ``t`` (or ``start``) of a URL in seconds: ``90``, ``90s``, ``1m30s``, ``1h2m3s``.

    >>> _url_time("https://youtu.be/x?t=1m30s"), _url_time("https://youtu.be/x?t=90")
    (90.0, 90.0)
    >>> _url_time("https://youtu.be/x") is None
    True
    """
    parts = urlsplit(url)
    q = {**dict(parse_qsl(parts.fragment)), **dict(parse_qsl(parts.query))}  # #t=45 too
    raw = q.get("t") or q.get("start")
    if not raw:
        return None
    if re.fullmatch(r"\d+(\.\d+)?", raw):
        return float(raw)
    m = re.fullmatch(r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+(?:\.\d+)?)s)?", raw)
    if not m or not any(m.groups()):
        return None
    h, mi, se = m.groups()
    return int(h or 0) * 3600 + int(mi or 0) * 60 + float(se or 0)


def _with_time(url: str, t: float) -> str:
    """``url`` with its ``t`` query parameter set to whole seconds (YouTube's deep link)."""
    parts = urlsplit(url)
    q = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k != "t"]
    q.append(("t", str(int(t))))
    return urlunsplit(parts._replace(query=urlencode(q)))


def _local_name(ref: str) -> str | None:
    """The file name of a local reference (a path, a ``file:`` URL), else ``None``."""
    scheme = urlsplit(ref).scheme.lower()
    drive = len(scheme) == 1  # C:\\clip.mp4 parses with scheme 'c'
    if scheme not in ("", "file") and not drive:
        return None
    path = urlsplit(ref).path if scheme == "file" else ref
    return re.split(r"[\\/]", path.rstrip("\\/"))[-1] or None


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
    PUBLISHABLE). A YouTube URL is normalised to its watch page (tracking
    parameters dropped) with a ``&t=`` deep link; ``t`` defaults to the URL's
    own. Any other URL keeps its scheme, host and path only (no password, no
    query: signed-URL tokens are credentials). A local file (a path, a
    ``file:`` URL) is recorded by its name only: provider ``local``, the name
    in ``extra.file``, no path anywhere; a ``data:`` URI is refused. ``t``,
    ``title`` and ``note`` go into ``extra`` beside any other keyword.

    >>> s = frame_source("https://www.youtube.com/watch?v=AAGIi62-sAU&si=track",
    ...                  t=34.6, license="all-rights-reserved", author="OverSimplified")
    >>> s.provider, s.id, s.url
    ('youtube', 'AAGIi62-sAU', 'https://www.youtube.com/watch?v=AAGIi62-sAU&t=34')
    >>> s.source_page_url, s.extra["frame_time_s"]
    ('https://www.youtube.com/watch?v=AAGIi62-sAU', 34.6)
    >>> frame_source("https://youtu.be/AAGIi62-sAU?t=1m30s", license=None).extra["frame_time_s"]
    90.0
    >>> local = frame_source("/home/me/private/clip.mp4", t=3, license="all-rights-reserved")
    >>> local.provider, local.url, local.extra["file"], "/home" in local.attribution
    ('local', None, 'clip.mp4', False)
    """
    vid = youtube_id(url) if url else None
    page = None
    shown = url
    if url and urlsplit(url).scheme.lower() == "data":
        raise ValueError(
            "a data: URI is the image itself, not where it came from: pass its origin"
        )
    local = _local_name(url) if url else None
    if local is not None:
        extra["file"] = local
        provider = provider or "local"
        shown, url = local, None
    elif vid is not None:
        provider = provider or "youtube"
        page = f"https://www.youtube.com/watch?v={vid}"
        if t is None:
            t = _url_time(url)
        url = _with_time(page, t) if t is not None else page
        shown = url
    else:
        if url:
            url = shown = _public_url(url)
        if provider is None:
            provider = (_host(url) if url else "") or "unknown"
    if t is not None:
        extra["frame_time_s"] = float(t)
    if title is not None:
        extra["title"] = title
    if note is not None:
        extra["note"] = note
    if attribution is None and shown:
        when = f" at {t:g} s" if t is not None else ""
        by = f" by {author}" if author else ""
        attribution = (
            f"Carved from {title or shown}{by}{when} ({license or 'licence unknown'})."
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
