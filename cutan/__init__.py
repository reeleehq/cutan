"""cutan: cut-out animation, as a genre package on the ``an`` core.

``an`` is the core of structured animation (scene documents, the timing kernel,
renderers, audio, storage, verification). A *genre* adds what one kind of
animation needs and registers it with the core; ``cutan`` is the first genre to
leave ``an``: rigged characters, faces and expressions, lip-sync visemes, swap
sets and views, cut-out styles and impacts (ADR 0001 in ``an``'s
``misc/docs/adr/``, tracked by an#225 under the epic an#231).

Rigged characters (``cutan.characters``), faces (``cutan.expression``), impacts
(``cutan.impacts``), the cut-out compile passes (``cutan.compile``), lip-sync
providers (``cutan.audio``), the style lint (``cutan.verify``) and the genre object
(``cutan.genre``) lived inside ``an`` until the P8 move (an#225); ``an`` keeps
warning aliases at the old import paths. Install it with ``pip install "an[cutout]"``;
``an`` finds it through the ``an.genres`` entry point.

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

#: The entry-point name this distribution declares (``pyproject.toml``): the name
#: ``an`` used to declare for the in-distribution genre, so the handover was by name.
ENTRY_POINT_NAME: str = GENRE_NAME

#: Where the entry point points.
ENTRY_POINT_VALUE: str = "cutan.genre:CUTOUT"

#: The persisted renderer name of cut-out shots (``an.stage`` claims it).
RENDERER_NAME: str = "cutout"

#: The package whose data root holds the genre's asset library and projects
#: (``~/.local/share/cutan`` by default; ``CUTAN_HOME`` overrides it).
LIBRARY_NAME: str = "cutan"

#: The lowest ``an.genres.API_LEVEL`` this ``cutan`` runs against ("the lowest ``an``
#: it supports", ADR 0001 decision 8, said without a version pin: ``an``'s version is
#: assigned by CI at merge). Level 2 is the move itself: ``Genre.services``,
#: ``ActionKind.lowering``, ``EntityKind.swap_declaration`` and ``an.stage.rig``.
#: Level 3 is the public rig builder (an#338): ``an.stage.rig.build_rig_subtree``,
#: ``rig_origin``, ``RigDocument`` and ``omit_unset_rig_fields``. Level 4 is the rest
#: pose (an#339): ``register_rest_pose_migration`` and ``rig_rest_problems``. Level 5
#: is nested chains (an#340): ``build_rig_subtree(skip_slots=)``, ``slot_parent_chain``,
#: ``slot_node_paths``, ``rig_affordances``, ``RigError``.
REQUIRED_AN_API_LEVEL: int = 5


def require_an() -> None:
    """Refuse, with an upgrade hint, to load against an ``an`` older than this ``cutan`` needs.

    >>> require_an()
    """
    import an.genres

    level = getattr(an.genres, "API_LEVEL", 0)
    if level < REQUIRED_AN_API_LEVEL:
        raise ImportError(
            f"cutan needs an.genres API level {REQUIRED_AN_API_LEVEL} or higher; this an "
            f"provides {level}. Upgrade an: pip install -U an"
        )


# The named style specs (package data, cutan#4): ``cutan.style_spec("south_park")``.
from cutan.styles import style_spec, style_specs  # noqa: E402

__all__ = [
    "ENTRY_POINT_GROUP",
    "ENTRY_POINT_NAME",
    "ENTRY_POINT_VALUE",
    "GENRE_NAME",
    "LIBRARY_NAME",
    "REQUIRED_AN_API_LEVEL",
    "RENDERER_NAME",
    "require_an",
    "style_spec",
    "style_specs",
]
