"""Carve: a photo or a video frame in, a matted, normalised, provenance-carrying cut-out part out (cutan#10).

Every production that carves parts re-wrote the same pipeline by hand:
locate → crop → matte → cut → de-spill → normalise → publish with provenance.
This is that pipeline once, with the matte as a strategy seam, because no
single method wins: a colour key beats a neural matte on flat cartoon frames,
a neural matte wins on photos, GrabCut on a single prop in a rough box.

>>> import numpy as np
>>> frame = np.full((90, 120, 3), 245, np.uint8)            # a flat backdrop
>>> frame[20:70, 30:90] = (40, 110, 200)                    # a prop on it
>>> part = carve(frame, point=(60, 45))                     # flat_colour, the default
>>> part.size, part.anchor, part.quality.warnings()
((70, 60), (0.5, 0.5), [])

- **One part:** :func:`carve` (``matte=`` a name from :data:`MATTES` or a
  :class:`Matte`; ``Polygon(points) & FlatColour()`` is a hand outline cleaned
  by a key). A video frame comes from :func:`grab_frame`.
- **A head:** :func:`carve_head` cuts the neck under the jaw and puts the face
  on a fixed canvas (512², the face centre as origin); the face is a hand box
  or found by a locator (``insightface``, ``pip install "cutan[faces]"``).
- **Moving parts:** :func:`split_parts` lifts parts off a carving, each with a
  pivot (clock hands off the face), painting the base in under them.
- **Provenance:** :func:`frame_source` (a licence is required, a YouTube URL
  gets its ``&t=`` deep link); :func:`write_prop` writes ``prop.json`` +
  ``parts/`` with the source in the descriptor, recipe and quality included,
  so ``an library publish`` gets the rights by construction.
- **Quality:** every :class:`Carving` carries :class:`CarveQuality` (coverage,
  backdrop left on the rim, glyphs left attached, a subject cut off by the
  crop); ``quality.warnings()`` says which look wrong.

Needs OpenCV: ``pip install "cutan[carve]"`` (``check_requirements()`` lists
what is installed). Nothing here is imported by ``import cutan``.
"""

from cutan.carve._deps import MissingDependencyError, check_requirements
from cutan.carve.core import (
    CarveQuality,
    Carving,
    carve,
    carve_head,
    grab_frame,
    load_rgb,
)
from cutan.carve.head import Face, InsightFaceLocator, neck_cut, pick_face
from cutan.carve.mattes import (
    MATTES,
    Chroma,
    FlatColour,
    Focus,
    GrabCut,
    Hint,
    Matte,
    Polygon,
    Rembg,
    as_matte,
    border_colours,
)
from cutan.carve.parts import Part, PartSet, PartSpec, split_parts
from cutan.carve.prop import write_prop
from cutan.carve.provenance import frame_source, youtube_id

__all__ = [
    "MATTES",
    "CarveQuality",
    "Carving",
    "Chroma",
    "Face",
    "FlatColour",
    "Focus",
    "GrabCut",
    "Hint",
    "InsightFaceLocator",
    "Matte",
    "MissingDependencyError",
    "Part",
    "PartSet",
    "PartSpec",
    "Polygon",
    "Rembg",
    "as_matte",
    "border_colours",
    "carve",
    "carve_head",
    "check_requirements",
    "frame_source",
    "grab_frame",
    "load_rgb",
    "neck_cut",
    "pick_face",
    "split_parts",
    "write_prop",
    "youtube_id",
]
