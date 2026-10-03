"""Declare ``an``'s cutout-animation production genre to nw, ready to use (nw#101).

A host that catalogs the federation's genres (the unified reelee AV connector,
reelee-web's ``GET /api/genres``) offers ``cutout_animation`` beside the others,
creates its projects where the host asks (nw#84), and serves two ops on them:
``status`` and ``render``.

How the pieces map onto nw:

- **Storage** (:mod:`nw.storage`). A cut-out project is an ``an`` project
  folder (``an.toml``, ``scene.md``, the mall). nw's graph lives *inside* it, in
  a ``dol`` store under ``.an/nw/graph`` (:func:`project_storage`), not in a
  SQLite file beside it, and nw's manifest ``project.json`` sits at the root so
  a host recognises the folder as an nw project. :func:`register_project_storage`
  teaches nw to open any such folder this way, so a host that only knows the
  path reaches the same graph.
- **Engine.** Free and local at the nw level: nothing is planned through
  ``falaw`` (the shape of ``nw/renderers/still.py``'s ``Plan(calls=())``), and
  ``render`` runs :func:`an.render.render_project`, whose own shot cache
  re-renders only the shots whose inputs changed (an ADR 0004). It is not a
  ``Transform`` or a ``nw.renderers`` strategy: those slots are written for the
  music-video shot pipeline. Like muvid's genres it is engine-less at the nw
  level and offered through ops, which is what makes ``is_ready()`` true.
- **Freshness.** ``render`` records the scene document as an authored entity
  (its digests, with a stable id) and the film as an annotation derived from
  it, through :meth:`nw.ProjectGraph.add_annotation`. Edit ``scene.md`` and
  ``status`` reports the film stale (:func:`nw.stale_verdicts`).
- **Spend.** ``render`` is marked ``spends=True``: a voice whose document
  declares ``provider: elevenlabs`` is spoken by ElevenLabs (an#305), so a host
  must route it through its money approval. A project whose voices declare no
  paid provider renders with no key and no bill.

**Import-safe and opt-in.** Only ``nw`` and ``dol`` at module top. ``an`` is
imported inside the functions, and ``an/__init__.py`` does not import this module,
so ``import an`` stays nw-free. A host imports ``cutan.nw`` explicitly.

**On the slug.** ``cutout_animation`` is a persisted identifier
(``cutan/__init__.py``); it does not change.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Callable, Optional
from uuid import uuid4

from nw import (
    Genre,
    GenreOp,
    GenreOpCancelled,
    GenreOpRefused,
    MappingStorage,
    register_genre,
    register_genre_ops,
    register_genre_project_factory,
    register_project_storage,
)
from nw.storage import PROJECT_FILE_NAME, json_docs

CUTOUT_ANIMATION_SLUG = "cutout_animation"

#: Where nw's graph lives inside an ``an`` project folder.
GRAPH_SUBPATH: tuple[str, ...] = (".an", "nw", "graph")
#: The ``an`` project marker a folder must carry for :func:`project_storage` to claim it.
AN_PROJECT_MARKER = "an.toml"

SCENE_TIER = "cutout-scene"
SCENE_SCHEMA_URI = "annot://schema/cutout-scene/v1"
FILM_TIER = "cutout-film"
FILM_SCHEMA_URI = "annot://schema/cutout-film/v1"
#: The scene files whose bytes are the film's authored input. ``scene.json`` is
#: the IR the renderer reads; ``scene.md`` is what a person edits.
SCENE_FILES: tuple[str, ...] = ("scene.md", "ir/scene.json")
ATTRIBUTION = "agent:cutan"


CUTOUT_ANIMATION = register_genre(
    Genre(
        slug=CUTOUT_ANIMATION_SLUG,
        title="Animation (cutout)",
        description=(
            "A written scene becomes an animated short: characters, dialogue and "
            "camera moves rendered as 2D cutout animation, with speech synthesized "
            "and mouths lip-synced to it. Renders locally; speech is free unless a "
            "voice declares a paid provider."
        ),
        status="available",
        transform_names=(),
        strategy_names=(),
        projection_entrypoint=None,
        intake_kinds=("text/markdown",),
        cost_profile=None,
    )
)


# --- storage ----------------------------------------------------------------


def project_storage(project_dir: str | Path) -> MappingStorage:
    """The :class:`nw.MappingStorage` of the ``an`` project at ``project_dir``.

    nw's documents are JSON files at the project root (``project.json``, the
    ``.nw/`` sentinels); its graph is a ``dol`` store under :data:`GRAPH_SUBPATH`.
    """
    pdir = Path(project_dir).resolve()
    return MappingStorage(
        root=pdir,
        graph=json_docs(pdir.joinpath(*GRAPH_SUBPATH)),
        docs=json_docs(pdir),
    )


def _resolve_storage(root: Path) -> Optional[MappingStorage]:
    """Claim an ``an`` project folder that is also an nw project; never writes."""
    if (root / AN_PROJECT_MARKER).is_file() and (root / PROJECT_FILE_NAME).is_file():
        return project_storage(root)
    return None


register_project_storage(CUTOUT_ANIMATION_SLUG, _resolve_storage)


# --- creation ---------------------------------------------------------------


def _default_projects_dir() -> Path:
    from an.library.root import library_root

    return library_root(package="cutan") / "projects"


def _cutout_project_factory(
    caller, project_id, *, title, template, params, projects_dir=None
):
    """Create a cut-out project at ``projects_dir/<project_id>``.

    ``projects_dir`` is where the host keeps its projects (nw#84). ``None`` is
    this machine's cutan library (``~/.local/share/cutan/projects``, or
    ``$CUTAN_HOME/projects``), the folder ``an init`` users already use; a
    multi-tenant host always passes its own, since ``caller`` is not used to
    separate anyone here.
    """
    import nw
    from an.project import init as an_init

    base = Path(projects_dir) if projects_dir is not None else _default_projects_dir()
    pdir = base / project_id
    if (pdir / PROJECT_FILE_NAME).exists() or (pdir / AN_PROJECT_MARKER).exists():
        raise FileExistsError(f"a project already exists at {pdir}")
    an_init(pdir, name=title)
    project = nw.Project.init(pdir, title=title, storage=project_storage(pdir))
    return {"project": project, "project_id": project_id, "title": title}


register_genre_project_factory(CUTOUT_ANIMATION_SLUG, _cutout_project_factory)


# --- the scene and the film in nw's graph ------------------------------------


def _scene_body(root: Path) -> dict:
    digests = {}
    for rel in SCENE_FILES:
        path = root / rel
        if path.is_file():
            digests[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    if not digests:
        raise GenreOpRefused(f"no scene in this project (looked for {SCENE_FILES})")
    return {"scene_files": digests}


def _record_scene(project) -> object:
    """Upsert the scene document as the film's authored input; return its id."""
    return project.graph.upsert_entity(
        tier=SCENE_TIER,
        body_schema_uri=SCENE_SCHEMA_URI,
        body=_scene_body(Path(project.root)),
        was_attributed_to=ATTRIBUTION,
    )


def _films(project) -> list:
    return list(_iter_tier(project, FILM_TIER))


def _iter_tier(project, tier: str):
    import nw

    return nw.annotations_at_tier(project.storage, tier)


def _record_film(project, scene_id, output: Path, *, output_name: str):
    from lacing import (
        Annotation,
        MediaRef,
        Provenance,
        RationalTime,
        TimeInterval,
        hash_file,
    )

    ann = Annotation(
        id=uuid4(),
        tier=FILM_TIER,
        reference=MediaRef(
            asset_id=project.graph.asset_id, interval=TimeInterval.from_seconds(0, 0)
        ),
        body={
            "output_name": output_name,
            "path": output.relative_to(project.root).as_posix(),
            "sha256": hash_file(output),
        },
        body_schema_uri=FILM_SCHEMA_URI,
        provenance=Provenance(
            was_generated_by="an.render.render_project",
            was_attributed_to=ATTRIBUTION,
            was_derived_from=[scene_id],
            generated_at_time=RationalTime.now(),
            activity="render",
        ),
    )
    # Keep one film per output name: the new render replaces the old record.
    for old in _films(project):
        if old.body.get("output_name") == output_name:
            project.graph.remove_annotation(old.id)
    project.graph.add_annotation(ann)
    return ann


# --- ops --------------------------------------------------------------------


def _status(project) -> dict:
    """What the cut-out project holds: its scene, its rendered films, and whether
    each film is stale (the scene changed since it was rendered)."""
    import nw
    from an.project import load

    root = Path(project.root)
    scene = load(root, check_kinds=False).scene
    films = _films(project)
    stale_ids: set = set()
    if films:
        # A read writes nothing, so an edit made outside nw (scene.md changed on
        # disk, not yet recorded) is detected by comparing the recorded scene to
        # the files; once recorded, nw's verdicts say the same thing.
        recorded = list(_iter_tier(project, SCENE_TIER))
        try:
            current = _scene_body(root)
        except GenreOpRefused:
            current = None
        if not recorded or recorded[0].body != current:
            stale_ids = {f.id for f in films}
        else:
            stale_ids = {
                v.annotation.id
                for v in nw.stale_verdicts_all(project.storage)
                if v.is_stale
            }
    return {
        "title": scene.meta.title or root.name,
        "shots": len(scene.timeline),
        "films": [
            {
                "output_name": f.body.get("output_name"),
                "path": f.body.get("path"),
                "stale": f.id in stale_ids,
            }
            for f in films
        ],
    }


def _render(
    project,
    *,
    output_name: str = "main",
    force_render: bool = False,
    should_cancel: Optional[Callable[[], bool]] = None,
) -> dict:
    """Render the scene to a film (``output/<output_name>.mp4``).

    Only shots whose inputs changed are re-rendered (an's shot cache);
    ``force_render`` renders every shot. Speech is spoken by each voice's own
    provider: free offline unless a voice declares a paid one (ElevenLabs)."""
    from an.render import render_project

    if should_cancel is not None and should_cancel():
        raise GenreOpCancelled("cancelled before rendering")
    scene_id = _record_scene(project)
    output = Path(
        render_project(
            project.root,
            output_name=output_name,
            force_render=force_render,
            echo_warnings=False,
        )
    )
    film = _record_film(project, scene_id, output, output_name=output_name)
    return {"output_name": output_name, "path": film.body["path"]}


CUTOUT_ANIMATION_OPS: tuple[GenreOp, ...] = register_genre_ops(
    CUTOUT_ANIMATION_SLUG,
    [
        GenreOp(
            name="status",
            fn=_status,
            title="Show the scene and its films",
            effect="read",
        ),
        GenreOp(
            name="render",
            fn=_render,
            title="Render the film",
            effect="render",
            runs="job",
            spends=True,
            host_params=("should_cancel",),
        ),
    ],
)

__all__ = [
    "CUTOUT_ANIMATION",
    "CUTOUT_ANIMATION_OPS",
    "CUTOUT_ANIMATION_SLUG",
    "project_storage",
]
