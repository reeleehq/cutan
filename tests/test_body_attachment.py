"""Body continuity (cutout.body_attachment): a prop that depicts a character's limbs
must be drawn in the character's view and meet the character's bones.

The two mistakes a production shipped, each as a failing case: a steering wheel
with the driver's hands drawn from the driver's seat (first person, or the back
of the body) laid over a driver seen from in front, and the same wheel placed by
eye to the side of the driver's head, wider than his shoulders. The geometry is
held to the COMPILED shot, so the check and the compiler cannot disagree. No
browser, no render.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from PIL import Image

from an.ir.schema import AssetRef, SetAction, Shot, StagePlacement
from an.project import init, load
from an.stage.compile import compile_shot
from an.stage.serialize import to_dict
from cutan.body_attachment import (
    BODY_ATTACHMENT_KEY,
    body_attachment_of,
    place_body_prop,
    solve_placement,
)
from cutan.characters import new_character
from cutan.verify.body import body_attachment_findings

ART = (400, 200)  # the wheel's raster size, pixels
PAUL_AT, PAUL_SCALE = (200.0, 300.0), 2.0
#: Sockets: the shoulders, above the wheel's rim (outside the art, v < 0).
SOCKETS = [{"bone": "arm_l", "at": [0.25, -0.6]}, {"bone": "arm_r", "at": [0.75, -0.6]}]


def _prop(root: Path, name: str, attachment: dict | None) -> None:
    d = root / "assets" / "props" / name
    (d / "parts").mkdir(parents=True)
    Image.new("RGBA", ART, (0, 0, 0, 255)).save(d / "parts" / "wheel.png")
    doc = {
        "kind": "PropDescriptor",
        "name": name,
        "slots": [{"name": "body", "bone": "root", "attachment": "wheel"}],
        "skins": {"default": {"slots": {"body": {"wheel": {"path": "parts/wheel.png"}}}}},
        "metadata": {BODY_ATTACHMENT_KEY: attachment} if attachment is not None else {},
    }
    (d / "prop.json").write_text(json.dumps(doc), encoding="utf-8")


@pytest.fixture(scope="module")
def project():
    with tempfile.TemporaryDirectory() as d:
        root = init(Path(d) / "p")
        new_character(root / "assets" / "characters", name="paul", seed="paul", use_dicebear=False)
        _prop(root, "wheel", {"character": "paul", "view": "front", "sockets": SOCKETS})
        _prop(root, "wheel_pov", {"character": "paul", "view": "first_person", "sockets": SOCKETS})
        _prop(root, "wheel_back", {"character": "paul", "view": "back", "sockets": SOCKETS})
        _prop(root, "wheel_crossed", {"character": "paul", "view": "front", "sockets": [
            {"bone": "arm_l", "at": [0.75, -0.6]}, {"bone": "arm_r", "at": [0.25, -0.6]}]})
        _prop(root, "plain", None)
        yield load(root).mall


def _shot(prop: str, at, scale, *, actions=(), paul=True) -> Shot:
    ents = [AssetRef(kind="character", id="paul", store="characters", ref="paul",
                     stage=StagePlacement(at=PAUL_AT, scale=PAUL_SCALE))] if paul else []
    ents.append(AssetRef(kind="prop", id="w", store="props", ref=prop,
                         stage=StagePlacement(at=at, scale=scale)))
    return Shot(id="s", renderer="cutout", duration=1.0, entities=ents, actions=list(actions))


def _placed(mall, prop="wheel"):
    return place_body_prop(mall["props"][prop], mall["characters"]["paul"],
                           character_at=PAUL_AT, character_scale=PAUL_SCALE, art_size=ART)


def _findings(mall, shot, *, poses=True):
    from an.motion import stage_poses

    p = stage_poses(shot, mall=mall) if poses else None
    return body_attachment_findings(shot, mall, poses=p, path="timeline/0")


def test_the_derived_placement_passes(project):
    fit = _placed(project)
    assert fit["residual_px"] < 0.5
    assert _findings(project, _shot("wheel", fit["at"], fit["scale"])) == []


def test_the_sockets_land_on_the_shoulders_in_the_compiled_shot(project):
    """The check's geometry is the compiler's: the socket computed from the prop's
    placement equals the point read off the compiled prop node and its visual box,
    and the bone the one read off the compiled arm."""
    fit = _placed(project)
    doc = to_dict(compile_shot(_shot("wheel", fit["at"], fit["scale"]), project, strict_assets=True))
    nodes = {n["name"]: n for n in doc["scene"]["children"]}
    w = nodes["w"]
    (body,) = w["children"]
    v, t, s = body["visual"], body["transform"], w["transform"]["scale_x"]
    for sock in SOCKETS:
        u, vv = sock["at"]
        x = w["transform"]["x"] + s * (t["x"] + (u - v["anchor_x"]) * v["width"])
        y = w["transform"]["y"] + s * (t["y"] + (vv - v["anchor_y"]) * v["height"])
        ba = body_attachment_of(project["props"]["wheel"])
        targets = solve_placement(
            *_models(project), ba, art_size=ART,
            character_pose={"x": PAUL_AT[0], "y": PAUL_AT[1], "scale_x": PAUL_SCALE, "scale_y": PAUL_SCALE})["targets"]
        bone = targets[[q["bone"] for q in SOCKETS].index(sock["bone"])]
        assert (x, y) == pytest.approx(bone, abs=0.5)
    paul = nodes["paul"]
    arm = next(n for n in paul["children"] if n["name"] in ("arm_l", "left_arm"))
    shoulder = (paul["transform"]["x"] + PAUL_SCALE * arm["transform"]["x"],
                paul["transform"]["y"] + PAUL_SCALE * arm["transform"]["y"])
    assert shoulder == pytest.approx(targets[0], abs=0.5)


def _models(mall):
    from cutan.body_attachment import character_model, prop_model

    return prop_model(mall["props"]["wheel"]), character_model(mall["characters"]["paul"])


def test_a_wheel_beside_the_head_and_wider_than_the_body_is_an_error(project):
    """The production's second mistake: placed by eye, right of the head, too big."""
    fit = _placed(project)
    shot = _shot("wheel", (fit["at"][0] + 90, fit["at"][1]), fit["scale"] * 1.8)
    size, meet = _findings(project, shot)
    assert size[0] == "error" and "80% larger relative to 'paul'" in size[2]
    assert meet[0] == "error" and "do not meet 'paul'" in meet[2]
    assert f"[{fit['at'][0]:g}, {fit['at'][1]:g}]" in meet[2]  # says where it belongs


def test_first_person_art_with_the_character_on_screen_is_an_error(project):
    """The production's first mistake: hands drawn from the driver's own eyes."""
    fit = _placed(project)
    (f,) = _findings(project, _shot("wheel_pov", fit["at"], fit["scale"]))
    assert f[0] == "error" and "first-person" in f[2]
    assert _findings(project, _shot("wheel_pov", (0, 0), 1.0, paul=False)) == []


def test_art_of_another_view_is_an_error_and_a_turn_at_the_start_counts(project):
    fit = _placed(project)
    found = _findings(project, _shot("wheel_back", fit["at"], fit["scale"]))
    assert [f[0] for f in found] == ["error"] and "'front' view" in found[0][2]
    turned = [SetAction(target="paul", property="view", value="back", at=0.0)]
    (f,) = _findings(project, _shot("wheel_back", fit["at"], fit["scale"], actions=turned))
    assert f[0] == "info"  # the view agrees; sockets are declared on the rest view


def test_crossed_limbs_are_refused(project):
    fit = _placed(project)
    (f,) = _findings(project, _shot("wheel_crossed", fit["at"], fit["scale"]))
    assert f[0] == "error" and "crossed" in f[2]
    with pytest.raises(ValueError, match="crossed"):
        _placed(project, "wheel_crossed")


def test_a_set_at_the_start_moves_the_placement_checked(project):
    fit = _placed(project)
    moved = [SetAction(target="w", property="x", value=fit["at"][0] + 120, at=0.0)]
    (f,) = _findings(project, _shot("wheel", fit["at"], fit["scale"], actions=moved))
    assert "do not meet" in f[2]


def test_without_built_poses_the_stage_placement_is_read(project):
    fit = _placed(project)
    assert _findings(project, _shot("wheel", fit["at"], fit["scale"]), poses=False) == []


def test_a_prop_without_a_declaration_and_an_absent_character(project):
    assert _findings(project, _shot("plain", (0, 0), 1.0)) == []
    (f,) = _findings(project, _shot("wheel", (0, 0), 1.0, paul=False))
    assert f[0] == "warning" and "not on stage" in f[2]


def test_a_malformed_declaration_is_an_error():
    shot = Shot(id="s", entities=[AssetRef(kind="prop", id="w", store="props", ref="w")])
    props = {"w": {"kind": "PropDescriptor", "name": "w",
                   "metadata": {BODY_ATTACHMENT_KEY: {"character": "p", "view": "front", "sockets": "x"}}}}
    (f,) = body_attachment_findings(shot, {"props": props})
    assert f[0] == "error" and "malformed" in f[2]


def test_an_validate_runs_it(project):
    """Registered as a genre check: `validate_semantic` (what `an validate` and
    `an render` run) reports it."""
    import an.genres
    from an.ir.schema import Meta, SceneIR
    from an.ir.validate import validate_semantic

    an.genres.load()
    fit = _placed(project)
    scene = SceneIR(meta=Meta(title="t"), timeline=[_shot("wheel_pov", fit["at"], fit["scale"])])
    report = validate_semantic(scene, available_characters=project["characters"],
                               available_props=project["props"])
    assert any("first-person" in f.description and f.severity == "error" for f in report.findings), report.findings


def test_a_prop_without_stage_at_is_placed_by_its_body_in_every_framing(project):
    """The production's third mistake: each framing placed the wheel by hand, so
    Paul's size relative to his own hands changed at the cut. Without `stage.at`
    the compiler derives it from Paul, in each framing, in proportion."""
    from an.ir.schema import AssetRef as A

    got = []
    for at, scale in (((200.0, 300.0), 2.0), ((-50.0, 520.0), 3.4)):
        shot = Shot(id="s", renderer="cutout", duration=1.0, entities=[
            A(kind="character", id="paul", store="characters", ref="paul", stage=StagePlacement(at=at, scale=scale)),
            A(kind="prop", id="w", store="props", ref="wheel")])
        doc = to_dict(compile_shot(shot, project, strict_assets=True))
        nodes = {n["name"]: n["transform"] for n in doc["scene"]["children"]}
        got.append((nodes["w"]["scale_x"] / nodes["paul"]["scale_x"],
                    ((nodes["w"]["x"] - nodes["paul"]["x"]) / scale, (nodes["w"]["y"] - nodes["paul"]["y"]) / scale)))
        assert _findings(project, shot) == []
    (r1, a1), (r2, a2) = got
    assert r1 == pytest.approx(r2, rel=1e-3) and a1 == pytest.approx(a2, abs=0.01)


def test_a_drifting_size_across_shots_is_caught_by_the_scene_check(project):
    """Each shot's size within the scale tolerance of the declaration would pass
    alone at 4% either way; across the cut the drift is 8%."""
    import an.genres
    from an.ir.schema import Meta, SceneIR
    from an.ir.validate import validate_semantic

    an.genres.load()
    fit = _placed(project)
    shots = [_shot("wheel", fit["at"], fit["scale"] * 1.04), _shot("wheel", fit["at"], fit["scale"] * 0.96)]
    shots[1] = shots[1].model_copy(update={"id": "s2"})
    report = validate_semantic(SceneIR(meta=Meta(title="t"), timeline=shots),
                               available_characters=project["characters"], available_props=project["props"])
    drift = [f for f in report.findings if "drift apart at the cut" in f.description]
    assert drift and drift[0].severity == "error", report.findings


def test_both_mirrored_passes_and_one_mirrored_is_an_error(project):
    fit = _placed(project)
    cx = PAUL_AT[0]
    both = [SetAction(target="paul", property="scale_x", value=-PAUL_SCALE, at=0.0),
            SetAction(target="w", property="scale_x", value=-fit["scale"], at=0.0),
            SetAction(target="w", property="x", value=2 * cx - fit["at"][0], at=0.0)]
    assert _findings(project, _shot("wheel", fit["at"], fit["scale"], actions=both)) == []
    one = both[:1]
    (f,) = _findings(project, _shot("wheel", fit["at"], fit["scale"], actions=one))
    assert f[0] == "error" and "mirrored" in f[2]


def test_a_view_other_than_the_rest_view_checks_the_view_not_the_sockets(project):
    """Sockets are declared on the rest view's bones; a side view moves and hides arms."""
    from cutan.body_attachment import BODY_ATTACHMENT_KEY as K

    props = dict(project["props"].items()) if hasattr(project["props"], "items") else {}
    side = json.loads(json.dumps(project["props"]["wheel"]))
    side["metadata"][K]["view"] = "side"
    stores = {"props": {"wheel": side}, "characters": project["characters"]}
    turned = [SetAction(target="paul", property="view", value="side", at=0.0)]
    (f,) = body_attachment_findings(_shot("wheel", (0, 0), 1.0, actions=turned), stores)
    assert f[0] == "info" and "rest view only" in f[2]
    del props


def test_a_store_without_files_is_not_an_error(project):
    """No filesystem root: the art cannot be measured, so the sockets are not checked."""
    stores = {"props": {"wheel": project["props"]["wheel"]}, "characters": project["characters"]}
    (f,) = body_attachment_findings(_shot("wheel", (0, 0), 1.0), stores)
    assert f[0] == "info" and "cannot be measured" in f[2]


def test_broken_documents_never_crash_the_check(project):
    paul = project["characters"]["paul"]
    good = project["props"]["wheel"]
    cases = [
        ({"wheel": {**good, "metadata": ["x"]}}, {"paul": paul}),
        ({"wheel": {**good, "slots": "nope"}}, {"paul": paul}),
        ({"wheel": good}, {"paul": "not a document"}),
        ({"wheel": good}, {"paul": {**paul, "bones": "x"}}),
    ]
    for props, chars in cases:
        found = body_attachment_findings(_shot("wheel", (0, 0), 1.0), {"props": props, "characters": chars})
        assert all(f[0] in ("info", "warning", "error") for f in found)


def test_the_scene_binds_a_reusable_prop_to_another_character(project):
    from an.ir.schema import AssetRef as A

    fit = _placed(project)
    shot = Shot(id="s", renderer="cutout", duration=1.0, entities=[
        A(kind="character", id="jerry", store="characters", ref="paul", stage=StagePlacement(at=PAUL_AT, scale=PAUL_SCALE)),
        A(kind="prop", id="w", store="props", ref="wheel", overrides={"body_of": "jerry"},
          stage=StagePlacement(at=fit["at"], scale=fit["scale"]))])
    assert _findings(project, shot) == []


def test_an_undeclared_prop_builds_no_stage():
    calls = []
    shot = Shot(id="s", entities=[AssetRef(kind="prop", id="p", store="props", ref="plain")])
    body_attachment_findings(shot, {"props": {"plain": {"kind": "PropDescriptor", "name": "plain"}}},
                             poses=lambda: calls.append(1))
    assert calls == []


@pytest.mark.parametrize("case", ["default_layout", "mirrored", "side_view"])
def test_a_prop_that_cannot_be_derived_says_why(project, case):
    """No `stage.at` and no derivation: the compiler would draw it at the centre."""
    from an.ir.schema import AssetRef as A

    stage = None if case == "default_layout" else StagePlacement(at=PAUL_AT, scale=PAUL_SCALE)
    actions = {"mirrored": [SetAction(target="paul", property="scale_x", value=-PAUL_SCALE, at=0.0)],
               "side_view": [SetAction(target="paul", property="view", value="side", at=0.0)]}.get(case, [])
    shot = Shot(id="s", renderer="cutout", duration=1.0, actions=actions, entities=[
        A(kind="character", id="paul", store="characters", ref="paul", stage=stage),
        A(kind="prop", id="w", store="props", ref="wheel")])
    found = _findings(project, shot)
    assert [f[0] for f in found] == ["error"] and "cannot be placed by its body" in found[0][2], found


def test_one_socket_without_a_declared_scale_checks_no_size(project):
    one = json.loads(json.dumps(project["props"]["wheel"]))
    one["metadata"][BODY_ATTACHMENT_KEY]["sockets"] = SOCKETS[:1]
    from cutan.body_attachment import solve_placement as solve, character_model, prop_model, body_attachment_of as bao
    ba = bao(one)
    pose = {"x": PAUL_AT[0], "y": PAUL_AT[1], "scale_x": PAUL_SCALE, "scale_y": PAUL_SCALE}
    got = solve(prop_model(one), character_model(project["characters"]["paul"]), ba, art_size=ART, character_pose=pose)
    # hand-placed at a quarter of the fallback scale, the socket still on the shoulder
    s = got["scale"] / 4
    q = got["local"][0]
    at = (got["targets"][0][0] - s * q[0], got["targets"][0][1] - s * q[1])

    class Store(dict):
        _root = project["props"]._root if hasattr(project["props"], "_root") else None

    props = Store(wheel=one)
    found = body_attachment_findings(_shot("wheel", at, s), {"props": props, "characters": project["characters"]})
    assert not [f for f in found if "larger" in f[2] or "smaller" in f[2]], found
