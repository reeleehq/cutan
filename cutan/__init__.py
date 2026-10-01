"""cutan: cut-out animation, as a genre package on the ``an`` core.

``an`` is the core of structured animation (scene documents, the timing kernel,
renderers, audio, storage, verification). A *genre* adds what one kind of
animation needs and registers it with the core; ``cutan`` is the first genre to
leave ``an``: rigged characters, faces and expressions, lip-sync visemes, swap
sets and views, cut-out styles and impacts (ADR 0001 in ``an``'s
``misc/docs/adr/``, tracked by an#225 under the epic an#231).

**Status: scaffold.** The cut-out code still lives inside ``an`` and is
moved here in batches, expand -> migrate -> contract: each module arrives here,
``an`` keeps a deprecation re-export for one release, then drops it. Until the
genre object itself moves, ``an`` ships it and this package registers nothing.

The identifiers below are the genre's **persisted** names (ADR 0001 decision 9):
they are written into documents, stores and entry-point metadata, and none of
them changes when code moves between distributions.

>>> GENRE_NAME
'cutout_animation'
>>> ENTRY_POINT_GROUP, ENTRY_POINT_NAME
('an.genres', 'cutout_animation')
>>> RENDERER_NAME, LIBRARY_NAME
('cutout', 'cutan')
"""

#: The genre's slug: the ``an.genres`` entry-point name and the ``nw`` genre id.
GENRE_NAME: str = "cutout_animation"

#: The entry-point group ``an.genres.load()`` reads.
ENTRY_POINT_GROUP: str = "an.genres"

#: The entry-point name this distribution will declare: the SAME name ``an``
#: declares today, so the handover is by name. ``an.genres`` de-duplicates by
#: entry-point name with ``an``'s in-distribution declaration first, so while
#: ``an`` still ships the genre, a declaration here is shadowed, never doubled.
ENTRY_POINT_NAME: str = GENRE_NAME

#: Where the entry point will point once the genre object lives here.
ENTRY_POINT_VALUE: str = "cutan.genre:CUTOUT"

#: The persisted renderer name of cut-out shots (``an.stage`` claims it).
RENDERER_NAME: str = "cutout"

#: The package whose data root holds the genre's asset library and projects
#: (``~/.local/share/cutan`` by default; ``CUTAN_HOME`` overrides it).
LIBRARY_NAME: str = "cutan"

__all__ = [
    "ENTRY_POINT_GROUP",
    "ENTRY_POINT_NAME",
    "ENTRY_POINT_VALUE",
    "GENRE_NAME",
    "LIBRARY_NAME",
    "RENDERER_NAME",
]
