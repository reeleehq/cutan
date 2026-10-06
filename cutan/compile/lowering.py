"""How the stage compiler lowers the cut-out genre's actions, and reads a character's swap sets.

The stage compiler (``an.stage.compile``) knows no cut-out kind by name. A genre
hands it an *action lowering* (:attr:`an.genres.ActionKind.lowering`) for each
kind that is more than a tween or set, and an *entity swap declaration*
(:attr:`an.genres.EntityKind.swap_declaration`) saying what a descriptor declares.
Both live here; the code they call is :mod:`cutan.compile.passes`.

>>> from cutan.characters.registration import PlayAction
>>> PLAY_LOWERING.extent_resolver(None)(PlayAction(target="a", animation="hop"))
0.5
"""

from __future__ import annotations

from typing import Any, Callable

from an.genres.registry import SwapDeclaration
from an.ir.migrate import migrate
from an.stage.compile import SCENE_PX_PER_VIEW_BOX, _track_root_of
from an.stores._common import art_exists_for

from cutan.characters.play import play_extent_for
from cutan.characters.schema import CHARACTER_DOCUMENT_KIND, CharacterDescriptor
from cutan.compile.passes import (
    _expand_preset_plays,
    preset_context_of,
    _resolve_play,
    _view_at,
    _view_spans,
)

#: The mall store holding character descriptors (a persisted name).
CHARACTERS_STORE: str = "characters"


class PlayLowering:
    """The ``play`` action kind, as the stage compiler lowers it (an#7, an#166, an#220)."""

    def extent_resolver(
        self, vocab: Any, *, products: Any = None
    ) -> Callable[[Any], float]:
        """``play -> seconds`` for a play that names no duration, read off its
        descriptor — and, for a walk, off the gait and scale the expansion will
        fill in (:func:`cutan.compile.passes.preset_context_of`, cutan#12).
        ``products`` is the shot's compile products (an#348), not read yet."""
        return play_extent_for(
            lambda entity_id: vocab.descriptors.get(entity_id) if vocab else None,
            context_of=preset_context_of(vocab),
        )

    def expand(self, flat_list: list, *, products: Any = None, **kw: Any) -> list:
        """Replace each ``play`` of a motion preset by the tweens and sets it stands for.
        ``products`` is the shot's compile products (an#348), not read yet."""
        return _expand_preset_plays(flat_list, **kw)

    def view_of(self, entity_swaps: Any, vocab: Any, *, duration: float):
        """``flat -> the view its entity is in then``, for characters with per-view face sets."""
        spans_by_entity = _view_spans(entity_swaps, vocab, duration=duration)
        if not spans_by_entity:
            return None

        def view_of(flat) -> str | None:
            entity = _track_root_of(flat.action.target)
            return _view_at(spans_by_entity.get(entity), flat.start)

        return view_of

    def clip(self, action: Any, **kw: Any):
        """The clip of one descriptor ``play`` (the presets were expanded already)."""
        return _resolve_play(action, **kw)


class ExpressionLowering:
    """The ``expression`` action kind: the face solver's input, so it makes no clip of its own."""

    def extent_resolver(self, vocab: Any, *, products: Any = None) -> None:
        return None

    def expand(self, flat_list: list, **kw: Any) -> list:
        """Drop the ``expression`` leaves: ``_add_face_clips`` sums them per (node, property)."""
        return [f for f in flat_list if f.action.kind != "expression"]

    def view_of(self, entity_swaps: Any, vocab: Any, *, duration: float) -> None:
        return None

    clip = None


PLAY_LOWERING = PlayLowering()
EXPRESSION_LOWERING = ExpressionLowering()


def character_swap_declaration(entity: Any, mall: Any) -> SwapDeclaration | None:
    """What a character's (migrated) descriptor declares, for the swap vocabulary.

    ``None`` when the store has no descriptor for the entity (a procedural or
    placeholder rig: its built nodes' sets ARE its declaration).
    """
    store = mall.get(CHARACTERS_STORE) or {}
    if entity.ref not in store:
        return None
    try:
        data = store[entity.ref]
    except KeyError:
        return None
    if not isinstance(data, dict) or data.get("kind") != CHARACTER_DOCUMENT_KIND.name:
        return None
    desc = CharacterDescriptor.model_validate(
        migrate(dict(data), kind=CHARACTER_DOCUMENT_KIND.name)
    )
    return SwapDeclaration(
        sets=desc.asset_sets,
        descriptor=desc,
        art_exists=art_exists_for(store, entity.ref),
        scale=SCENE_PX_PER_VIEW_BOX / float(desc.view_box[3] or 1),
    )
