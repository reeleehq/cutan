# cutan.bench

The cut-out genre’s bench corpus: eight scenes that use characters, and their goldens.

Moved from `an.bench.corpus` (an#225). The bench RUNNER stays in `an`
(`an.bench.run.run_bench`); the scenes, their blessed golden frames and their
ledger rows live in this repository’s `misc/bench/`. Run it from a source
checkout of `cutan`:

```pycon
>>> sorted(CUTOUT_FIXTURES)[:3]
['aa_probe', 'dialogue', 'expressions']
```

### Module Attributes

| [`REPO_ROOT`](#cutan.bench.REPO_ROOT)       | The checkout whose `examples/` and `misc/bench/` hold the corpus.                                                                                                                                                      |
|------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`CUTOUT_FIXTURES`](#cutan.bench.CUTOUT_FIXTURES) | the descriptor (SVG-sprite) path is 12x more sensitive to a rasteriser flip than the procedural one (2.94% vs 0.24% of pixels under GPU-vs-software), so a procedural-only corpus under-reports the case that matters. |

### Functions

| [`run_bench`](#cutan.bench.run_bench)(\*\*kwargs)   | `an.bench.run.run_bench` over [`CUTOUT_FIXTURES`](#cutan.bench.CUTOUT_FIXTURES), rooted at this checkout.   |
|--------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------|

### cutan.bench.CUTOUT_FIXTURES *: [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), Fixture]* *= {'aa_probe': Fixture(path='misc/bench/corpus/aa_probe', prepare=None, expect_visual_kinds=frozenset({'rect'}), golden_frames=(0.0, 0.25), golden_note='the fourth bar sweeping horizontally (4,200 px). The three angled bars are pinned and do not move — they are the AA subject.'), 'dialogue': Fixture(path='misc/bench/corpus/dialogue', prepare=None, expect_visual_kinds=frozenset({'rect', 'eye', 'ellipse', 'mouth'}), golden_frames=(0.0, 0.6), golden_note="the mouth mid-line: frame 14 sits on the \`h\`/\`a\` of 'shape' and shows \`A\`, the winner of its 0.14 s window under the an#97 vote; the old drop-not-hold condenser showed \`C\` there, having dropped the \`D\` and \`A\` that followed inside the window. Frame 0 shows \`E\` — the winner of the first window, after the lead pulled the line's opening cues to 0 — where the old path showed the rest. The head is lifted 34 px above its rest by an absolute \`set\` so the placeholder rig's mouth clears the torso. The second golden sits INSIDE the spoken interval; \`single_character\`'s second golden samples after its line ends (its first, at t=0, is on the led first shape) and \`promote_demo\` renders mute in the bench (no visemes in its IR, by design). The visemes are the offline provider's, stamped into the committed ir/scene.json; the bench renders with auto_audio=False and reads them from there."), 'expressions': Fixture(path='misc/bench/corpus/expressions', prepare=None, expect_visual_kinds=frozenset({'svg_sprite'}), golden_frames=(0.125, 0.375, 0.625, 0.875, 1.125, 1.375, 1.625, 1.875), golden_note="eight 0.25 s shots of one silent synthesized character holding one expression preset each (neutral, happy, sad, angry, surprised, afraid, thinking, skeptical — the two presets whose faces differ only by a mouth form the silent rest does not show, disgusted and amused, are left out), sampled at each shot's mid-frame (an#98). What moves between goldens is the FACE SOLVER's output alone: brow height and angle, the eyelid key, and the mouth form's rest. The character is named \`face\` because its seeded blink phase puts no blink window inside any 0.25 s shot (the blink clock restarts per shot), so no golden straddles a blink; it is lowered by an absolute \`set face y\` so the head clears the frame's top edge at 320x240. Its rig is committed whole (parts and descriptor, \`viseme@happy\`/\`viseme@sad\` variants included) and, since an#99, the eye stack (sclera/pupil/lid slots, a filled closed lid, \`gaze_travel\`), so the pupils also make their seeded ambient saccades — sub-pixel at 320x240 and inside the face crop. The pairwise distinguishability test in tests/test_expression_goldens.py reads these same PNGs."), 'graded_field': Fixture(path='misc/bench/corpus/graded_field', prepare=None, expect_visual_kinds=frozenset({'svg_sprite'}), golden_frames=(0.0, 0.1667), golden_note='the white marker sweeping across the gradient (6,270 px). Frame 4, not the obvious mid-scene frame 6: the marker advances by a sub-pixel step, so on frames 0, 1, 6, 8 and 11 it lands on an exact pixel boundary and AA-off changes ZERO pixels there. A blessed pair that no available mutation can move is a gate that cannot go red.'), 'multi_shot': Fixture(path='misc/bench/corpus/multi_shot', prepare=None, expect_visual_kinds=frozenset({'rect', 'ellipse'}), golden_frames=(0.0, 0.25), golden_note='the whole picture: 0.25s is the FIRST frame of the second shot, so the pair spans the concat boundary (75,050 px). A golden pair inside one shot would not notice a shot rendered in the wrong order.'), 'promote_demo': Fixture(path='examples/promote_demo', prepare=<function \_prepare_promote_demo>, expect_visual_kinds=frozenset({'svg_sprite'}), golden_frames=(0.0, 2.9167), golden_note="a blink — the compiled eyelid swap shows the closed-eye art at t=2.9167 (an earlier note blamed 'the idle animation', which nothing on the render path consumes). Measured: frame 0 against duration/2 differs by exactly ZERO pixels here, so the obvious second time would have blessed one image twice."), 'saturated_outline': Fixture(path='misc/bench/corpus/saturated_outline', prepare=None, expect_visual_kinds=frozenset({'svg_sprite'}), golden_frames=(0.0, 0.25), golden_note='the head plate rotating through 0.3 rad (1,187 px).'), 'single_character': Fixture(path='examples/single_character', prepare=<function \_declare_procedural_rig.<locals>.prepare>, expect_visual_kinds=frozenset({'rect', 'ellipse'}), golden_frames=(0.0, 1.0), golden_note='a blink (the compiled scale_y squash on the procedural eyes) plus, since an#97, the mouth: 253 pixels differ, 172 from the blink and 81 from the mouth (frame 0 shows the led first shape of the 0.71 s line, frame 24 the closed rest after it, which the frame-ceiled window now samples). Blinks occupy 3.5% of frames, so before the lead frame 0 against duration/2 was a pixel-identical pair on this scene; the mouth now separates them by 81 px.')}*

the descriptor
(SVG-sprite) path is 12x more sensitive to a rasteriser flip than the
procedural one (2.94% vs 0.24% of pixels under GPU-vs-software), so a
procedural-only corpus under-reports the case that matters.

The four scenes an#38 adds, each for a **measured** reason:

- `graded_field` — a real gradient (98 distinct luma levels down the centre
  column) over a large flat block. Banding has no edge in it, so every
  edge-masked metric is blind to it; and the gradient itself sits OUTSIDE the
  flat mask by construction (`flat_mask` demands a zero 4-neighbour delta),
  which is why the scene carries a flat block too — measured 0.2795 of the
  frame, against 0.0341 for a gradient alone.
- `saturated_outline` — maximally saturated fills under a pure-black 12px
  outline. The shipped examples are 31 colours on white and their measured
  4:2:0 edge error is ~3x smaller, so the chroma metric under-reports exactly
  the artefact class the epic cares about. Highest edge-mask fraction in the
  corpus (0.0566).
- `aa_probe` — three bars pinned at 7, 23 and 45 degrees. Axis-aligned
  `drawRect` edges are bit-identical with MSAA on or off, so a corpus of
  axis-aligned art cannot validate an AA metric at all. Measured under the
  real AA lever (PixiJS `antialias: false`): `edge_transition_width`
  2.9866 -> 2.0000 and `video_stream_bytes` **+6.1%**. That last number is
  why this scene is load-bearing rather than decorative — on
  `single_character` the same lever moves the bytes **-6.1%**, the opposite
  of the declared direction, because AA-off on axis-aligned art removes
  intermediate colours instead of creating a staircase. Family F is only an
  honest witness for `disabled_aa` on a scene with non-axis-aligned edges.
- `multi_shot` — two shots, so `an/render.py`’s `_ffmpeg_concat` is
  exercised at all (a single-shot render short-circuits it to
  `shutil.copy`) and `file_bytes` stops meaning two different things
  depending on shot count. Its shot ids are `intro` then `beat`
  **deliberately**: they sort the other way, so any code that recovers shot
  order from the directory name instead of the timeline pairs source frames
  against the wrong half of the concatenated video, and this fixture is what
  notices.

One measured fact that shapes the set: the \*\*descriptor path is nearly blind
to the AA lever\*\* (96 differing pixels out of 12.4M on `promote_demo`),
because MSAA applies to WebGL geometry and an SVG sprite is a pre-rasterised
texture. So the descriptor scenes are in the corpus for the rasteriser
sensitivity the cross-arch work measured, not as AA witnesses.
The cut-out corpus (see the reasons per scene, which moved with them).

* **Type:**
  The corpus. One fixture per render path, deliberately both

### cutan.bench.REPO_ROOT *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)* *= PosixPath('/home/runner/work/cutan/cutan')*

The checkout whose `examples/` and `misc/bench/` hold the corpus.

### cutan.bench.run_bench(\*\*kwargs)

`an.bench.run.run_bench` over [`CUTOUT_FIXTURES`](#cutan.bench.CUTOUT_FIXTURES), rooted at this checkout.
