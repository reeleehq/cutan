"""An expression's mouth form while the character is silent (an#253).

The intended behaviour, stated: under an expression whose preset prefers a
mouth form (``happy``, ``sad``, ...), the character's mouth shows that form's
rest shape (``viseme@<form>``'s ``X``) whenever no line of its own is playing;
a line under it speaks on the same set. Two things made the end-user test see
a neutral line instead: the factory drew a variant's smile as a shift of the
whole mouth, not a curve, and a form the character has no set for stayed
neutral without a word.
"""

from __future__ import annotations

import re
import warnings

from an.ir.schema import AssetRef, Dialogue, Meta, SceneIR, Shot

from cutan.characters import new_character
from cutan.characters.mouth_set import _DEFAULT_PALETTE, _shape_svg
from cutan.expression.registration import expression

_PATH = re.compile(r'<path d="M [\d.]+ (?P<corner>[\d.]+) Q [\d.]+ (?P<top>[\d.]+) ')


def _corner_and_top(smile: float) -> tuple[float, float]:
    svg = _shape_svg("x", canvas=(256, 128), palette=dict(_DEFAULT_PALETTE), smile=smile)
    m = _PATH.search(svg)
    return float(m["corner"]), float(m["top"])


def test_a_variant_curves_the_mouth_instead_of_moving_it():
    corner0, top0 = _corner_and_top(0.0)
    happy_corner, happy_top = _corner_and_top(0.35)
    sad_corner, sad_top = _corner_and_top(-0.35)
    # the middle (the control points) stays where the neutral mouth has it ...
    assert happy_top == top0 == sad_top
    # ... and the corners move against it: up for a smile, down for a frown (y down)
    assert happy_corner < corner0 - 5 and sad_corner > corner0 + 5


def test_the_neutral_mouth_is_drawn_as_it_always_was():
    svg = _shape_svg("x", canvas=(256, 128), palette=dict(_DEFAULT_PALETTE))
    assert 'd="M 89.60 64.24 Q 128.00 62.00 166.40 64.24 Q 128.00 65.84 89.60 64.24 Z"' in svg


def _scene(tmp_path, *actions, dialogue=()):
    from an.stores.characters import CharactersStore

    new_character(tmp_path, name="ned", use_dicebear=False, overwrite=True)  # variants: happy, sad, angry
    shot = Shot(
        id="s",
        duration=2.0,
        entities=[AssetRef(kind="character", id="c", store="characters", ref="ned")],
        actions=list(actions),
        dialogue=list(dialogue),
    )
    return SceneIR(meta=Meta(), timeline=[shot]), CharactersStore(tmp_path)


def _validate(scene, store):
    from an.ir.validate import validate_semantic

    report = validate_semantic(scene, available_characters=store)
    return [f for f in report.findings if "viseme@" in f.description]


def _compile_warnings(scene, store):
    from an.adapters.cutout.compile import compile_shot

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        compiled = compile_shot(scene.timeline[0], {"characters": store})
    return compiled, [str(w.message) for w in caught if "viseme@" in str(w.message)]


def test_a_silent_happy_holds_the_variants_rest_mouth(tmp_path):
    scene, store = _scene(tmp_path, expression("c", "happy"))
    assert _validate(scene, store) == []
    compiled, said = _compile_warnings(scene, store)
    assert said == []
    holds = [
        k["value"]
        for clip in compiled.model_dump(mode="json")["animations"].values()
        for ch in clip["channels"]
        if ch["property"] == "viseme@happy"
        for k in ch["keyframes"]
    ]
    assert holds and set(holds) == {"X"}


def test_a_form_the_character_has_no_set_for_is_said_with_the_fix(tmp_path):
    scene, store = _scene(tmp_path, expression("c", "disgusted"), expression("c", "disgusted"))
    (finding, _second) = _validate(scene, store)
    assert finding.severity == "warning"
    assert "'viseme@disgusted'" in finding.description
    assert "an character mouths ned --variants disgusted" in finding.description
    _, said = _compile_warnings(scene, store)
    assert len(said) == 1 and "an character mouths ned --variants disgusted" in said[0]
    # the dialogue sugar is the same expression: validate says it too
    line = Dialogue(speaker="c", text="No.", emotion="disgusted", start=0.2, duration=0.5)
    scene, store = _scene(tmp_path, dialogue=[line])
    (finding,) = _validate(scene, store)
    assert finding.ir_path.endswith("/dialogue/0/emotion")
