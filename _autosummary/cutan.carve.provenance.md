# cutan.carve.provenance

Where carved pixels came from: an `AssetSource` for a frame of a video or an image.

Provenance by construction: a carve takes its source at the start, and the
part folder it writes carries it in the descriptor’s `source`, so
`an library publish` records the rights without flags, and `an credits`
lists the part as what it is (`all-rights-reserved` footage you do not own
is NOT PUBLISHABLE, and says so).

The licence is never guessed: [`frame_source()`](#cutan.carve.provenance.frame_source) requires one. A local file
is recorded by its name, never its path: a descriptor travels into libraries
and credits, and an absolute path is private information.

### Functions

| [`frame_source`](#cutan.carve.provenance.frame_source)(url, \*, license[, t, author, ...])   | The provenance of a part carved from `url` (a video at time `t`, or an image).   |
|-----------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------|
| [`youtube_id`](#cutan.carve.provenance.youtube_id)(url)                                    | The video id of a YouTube URL, else `None`.                                      |

### cutan.carve.provenance.frame_source(url, , license, t=None, author=None, author_url=None, title=None, provider=None, attribution=None, note=None, cacheable=True, \*\*extra)

The provenance of a part carved from `url` (a video at time `t`, or an image).

`license` is required (keyword-only, no default): `None` records the
rights as UNKNOWN, which is a statement too. For footage you do not own,
`"all-rights-reserved"` (`an credits` then lists the part as NOT
PUBLISHABLE). A YouTube URL is normalised to its watch page (tracking
parameters dropped) with a `&t=` deep link; `t` defaults to the URL’s
own. Any other URL keeps its scheme, host and path only (no password, no
query: signed-URL tokens are credentials). A local file (a path, a
`file:` URL) is recorded by its name only: provider `local`, the name
in `extra.file`, no path anywhere; a `data:` URI is refused. `t`,
`title` and `note` go into `extra` beside any other keyword.

* **Return type:**
  `AssetSource`

```pycon
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
```

### cutan.carve.provenance.youtube_id(url)

The video id of a YouTube URL, else `None`.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

```pycon
>>> youtube_id("https://www.youtube.com/watch?v=AAGIi62-sAU&t=34")
'AAGIi62-sAU'
>>> youtube_id("https://youtu.be/AAGIi62-sAU?t=3"), youtube_id("https://example.org/a.png")
('AAGIi62-sAU', None)
>>> youtube_id("https://notyoutube.com/watch?v=x"), youtube_id("https://WWW.YOUTUBE.COM:443/shorts/abc")
(None, 'abc')
```
