"""Draw the carve test fixtures: synthetic frames with their exact subject masks.

Run from the repo root to regenerate (deterministic; numpy + Pillow only):

    python tests/fixtures/carve/make_fixtures.py

Every image is drawn here, so it is ours (CC0) and its ground truth is exact:
``<name>.png`` is the frame, ``<name>_mask.png`` the subject (white). The
frames stand for the cases cutan#10 measured: a flat cartoon frame with a
caption glyph touching the head, a saturated stage backdrop, a single prop on
a busy background, a sharp object on a blurred one, a wall clock whose hands
come off, and a head on shoulders.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
SS = 4  # supersampling: shapes are drawn 4x and averaged down (anti-aliased edges)


def _canvas(w, h, colour):
    return Image.new("RGB", (w * SS, h * SS), colour)


def _down(img):
    return img.resize((img.width // SS, img.height // SS), Image.LANCZOS)


def _mask_down(mask):
    return mask.resize((mask.width // SS, mask.height // SS), Image.BOX).point(
        lambda v: 255 if v >= 128 else 0
    )


def _s(*xs):
    return [x * SS for x in xs]


def cartoon():
    """OverSimplified-like: a two-tone flat set, an outlined figure, a caption glyph on its head.

    The head's interior is the wall's exact colour (enclosed by its outline),
    the case where a plain colour key fails and a border-connected one works.
    """
    wall, floor, ink, shirt = (238, 232, 214), (205, 164, 105), (25, 22, 20), (176, 48, 44)
    img = _canvas(320, 240, wall)
    d = ImageDraw.Draw(img)
    d.rectangle(_s(0, 170, 320, 240), fill=floor)
    mask = Image.new("L", img.size, 0)
    m = ImageDraw.Draw(mask)
    for draw, fill_head, fill_body in ((d, wall, shirt), (m, 255, 255)):
        draw.rectangle(_s(130, 120, 190, 200), fill=fill_body if draw is m else ink)
        draw.rectangle(_s(134, 124, 186, 196), fill=fill_body)
        draw.ellipse(_s(120, 40, 200, 120), fill=255 if draw is m else ink)
        draw.ellipse(_s(124, 44, 196, 116), fill=fill_head)
    d.ellipse(_s(145, 70, 153, 78), fill=ink)  # eyes
    d.ellipse(_s(167, 70, 175, 78), fill=ink)
    d.arc(_s(148, 80, 172, 100), 20, 160, fill=ink, width=3 * SS)
    # a caption glyph (a thick "T") touching the head by a 2-px neck: not the subject
    d.rectangle(_s(199, 76, 229, 78), fill=ink)
    d.rectangle(_s(212, 60, 250, 68), fill=(250, 214, 60))
    d.rectangle(_s(227, 60, 235, 98), fill=(250, 214, 60))
    d.rectangle(_s(212, 60, 250, 62), fill=ink)
    return _down(img), _mask_down(mask)


def chroma():
    """A saturated purple stage drape (a gradient plus noise) behind a skin-and-grey figure."""
    rng = np.random.default_rng(1)
    h, w = 200, 260
    yy = np.linspace(0, 1, h)[:, None]
    drape = np.stack([110 + 40 * yy, 40 + 10 * yy, 170 + 50 * yy], axis=2) * np.ones((1, w, 1))
    drape += rng.normal(0, 6, drape.shape)
    img = Image.fromarray(np.clip(drape, 0, 255).astype(np.uint8)).resize((w * SS, h * SS))
    d = ImageDraw.Draw(img)
    mask = Image.new("L", img.size, 0)
    m = ImageDraw.Draw(mask)
    for draw, skin, coat in ((d, (226, 182, 150), (90, 90, 96)), (m, 255, 255)):
        draw.ellipse(_s(95, 30, 165, 110), fill=skin)
        draw.rounded_rectangle(_s(80, 105, 180, 200), radius=18 * SS, fill=coat)
    d.ellipse(_s(112, 60, 122, 70), fill=(40, 30, 30))
    d.ellipse(_s(138, 60, 148, 70), fill=(40, 30, 30))
    return _down(img), _mask_down(mask)


def busy():
    """A single prop (a lamp) on a striped, multi-coloured wall: GrabCut's case.

    Four backdrop colours, so no flat key holds; none of them is the prop's
    (a stripe the shade's colour defeats GrabCut too: IoU 0.80 measured).
    """
    img = _canvas(240, 200, (200, 200, 200))
    d = ImageDraw.Draw(img)
    for i, c in enumerate([(120, 160, 200), (150, 190, 140), (190, 150, 190), (110, 140, 170)] * 8):
        d.rectangle(_s(i * 12, 0, i * 12 + 12, 200), fill=c)
    mask = Image.new("L", img.size, 0)
    m = ImageDraw.Draw(mask)
    for draw, shade, stem in ((d, (250, 240, 200), (60, 50, 45)), (m, 255, 255)):
        draw.polygon(_s(90, 40, 150, 40, 170, 100, 70, 100), fill=shade)
        draw.rectangle(_s(114, 100, 126, 160), fill=stem)
        draw.ellipse(_s(85, 150, 155, 175), fill=stem)
    return _down(img), _mask_down(mask)


def blurred():
    """A sharp, textured object on a strongly blurred textured background: the focus matte's case."""
    rng = np.random.default_rng(2)
    h, w = 180, 240
    bg = Image.fromarray(rng.integers(0, 255, (h, w, 3), dtype=np.uint8)).filter(
        ImageFilter.GaussianBlur(9)
    )
    tex = Image.fromarray(rng.integers(0, 255, (h, w, 3), dtype=np.uint8))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).ellipse((70, 40, 170, 140), fill=255)
    img = Image.composite(tex, bg, mask)
    return img, mask


def clock():
    """A wall clock (brown rim, cream face, numeral ticks) with its two grey hands at 10:10.

    Its ground truth is three masks: the whole clock, and each hand.
    """
    wall, rim, face, tick, hand = (240, 236, 222), (122, 74, 40), (250, 244, 220), (30, 30, 30), (95, 95, 100)
    img = _canvas(220, 220, wall)
    d = ImageDraw.Draw(img)
    cx, cy, r = 110, 110, 90
    d.ellipse(_s(cx - r, cy - r, cx + r, cy + r), fill=rim)
    d.ellipse(_s(cx - r + 12, cy - r + 12, cx + r - 12, cy + r - 12), fill=face)
    for k in range(12):
        a = np.radians(k * 30)
        x, y = cx + 64 * np.sin(a), cy - 64 * np.cos(a)
        d.ellipse(_s(x - 3, y - 3, x + 3, y + 3), fill=tick)
    masks = {}
    for name, deg, length, width in (("hour", -60, 40, 7), ("minute", 60, 62, 5)):
        a = np.radians(deg)
        ex, ey = cx + length * np.sin(a), cy - length * np.cos(a)
        d.line(_s(cx, cy, ex, ey), fill=hand, width=width * SS)
        mk = Image.new("L", img.size, 0)
        ImageDraw.Draw(mk).line(_s(cx, cy, ex, ey), fill=255, width=width * SS)
        masks[name] = mk
    d.ellipse(_s(cx - 6, cy - 6, cx + 6, cy + 6), fill=tick)  # the hub (stays on the face)
    whole = Image.new("L", img.size, 0)
    ImageDraw.Draw(whole).ellipse(_s(cx - r, cy - r, cx + r, cy + r), fill=255)
    return _down(img), _mask_down(whole), {k: _mask_down(v) for k, v in masks.items()}


#: The head fixture's face box and jaw contour (source pixels), for carve_head.
HEAD_FACE_BOX = (110, 50, 190, 150)
HEAD_JAW = [(110 + 40 + 40 * np.cos(t), 100 + 50 * np.sin(t)) for t in np.linspace(0, np.pi, 17)]


def head():
    """A drawn head (an ellipse face, hair, ears) on a neck and shoulders, on a flat backdrop."""
    back, skin, hair, shirt = (200, 220, 236), (232, 190, 160), (80, 50, 30), (40, 90, 150)
    img = _canvas(300, 260, back)
    d = ImageDraw.Draw(img)
    d.rectangle(_s(60, 190, 240, 260), fill=shirt)  # shoulders run off the frame
    d.rectangle(_s(132, 140, 168, 200), fill=skin)  # the neck
    d.ellipse(_s(104, 88, 116, 110), fill=skin)  # ears
    d.ellipse(_s(184, 88, 196, 110), fill=skin)
    d.ellipse(_s(110, 50, 190, 150), fill=skin)  # the face (the HEAD_FACE_BOX)
    d.chord(_s(106, 36, 194, 100), 180, 360, fill=hair)
    d.ellipse(_s(132, 92, 142, 102), fill=(30, 30, 30))
    d.ellipse(_s(158, 92, 168, 102), fill=(30, 30, 30))
    d.arc(_s(135, 112, 165, 132), 20, 160, fill=(150, 60, 60), width=3 * SS)
    return _down(img)


def main() -> None:
    def save(name, img, mask=None):
        img.save(HERE / f"{name}.png", optimize=True)
        if mask is not None:
            mask.save(HERE / f"{name}_mask.png", optimize=True)

    save("cartoon", *cartoon())
    save("chroma", *chroma())
    save("busy", *busy())
    save("blurred", *blurred())
    img, whole, hands = clock()
    save("clock", img, whole)
    for k, v in hands.items():
        v.save(HERE / f"clock_{k}_mask.png", optimize=True)
    save("head", head())


if __name__ == "__main__":
    main()
