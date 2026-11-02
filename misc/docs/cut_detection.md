# Cut detection for the style lint: the histogram jump vs `mixing.video.shots` (cutan#151)

Measured 2026-11-02. **Decision: keep `cutan.verify.style`'s histogram-jump detector.** On six cut-out clips it found 32 of 36 hand-labelled hard cuts with no false cut, or 2 false if one ambiguous Kurzgesagt reveal counts as a camera move (see Reading). That is on par with mixing's best setting (5 Hz `spike`: 33/36, 2 false), not a clear win. It is kept because the style targets were calibrated on it, it needs no new dependency, and it invents fewer cuts than any setting that finds more. It is offered to mixing as a strategy in reeleehq/mixing#164.

To use mixing's cuts instead, no new option is needed: `measure_style`, `measure_video` and `style_lint` already take `shot_durations`. Pass `[b - a for a, b in mixing.video.shots(mp4)]`.

## Method

- **Clips:** the six study clips of the cut-out styles research (an `misc/docs/cutout_styles_research.md` §3), kept outside every repository.
- **Candidates:** the union of four detectors' cuts, merged within 0.6 s. The four are: the histogram detector; mixing `diff` at 2 Hz `level` (its default); mixing `diff` at 5 Hz `spike`; and mixing's array stages on the lint's own full-rate 320×180 frames with `spike`.
- **Labels:** each candidate was labelled from before/after frames, with frame strips where it was unclear.
  - **A cut is a hard cut:** one frame to the next changes shot.
  - **Transitions count neither way:** a push or slide, a dissolve, a title overlay. That is four Kurzgesagt pushes and slides, three Norstein dissolves and one OverSimplified overlay.
  - The labeller could see which detectors flagged each candidate, so the labels are not blind.
- **Scoring:** one-to-one. Each hard cut is matched by at most one detection, and each detection credits at most one cut, nearest first, within 0.6 s. A detection near a transition counts neither way; every other detection is a false cut.
- **Coverage:** every detection of the spike variants scored below was among the labelled candidates. The level variants' extra detections are camera moves and motion.

## Result (hard cuts found / labelled, false cuts)

| clip | cuts | histogram | 2 Hz level (mixing default) | 2 Hz spike | 2 Hz spike, ratio 1.5 | 5 Hz level | 5 Hz spike | 5 Hz spike, ratio 1.5 |
|---|---|---|---|---|---|---|---|---|
| South Park | 8 | 6, 0 | 8, 0 | 8, 0 | 8, 0 | 8, 0 | 8, 0 | 8, 0 |
| OverSimplified | 10 | 9, 0 | 10, 6 | 9, 2 | 9, 2 | 10, 13 | 10, 1 | 10, 2 |
| Kurzgesagt | 5 | 5, 0 | 5, 8 | 5, 2 | 5, 3 | 5, 16 | 3, 0 | 4, 0 |
| Reiniger | 4 | 4, 0 | 4, 0 | 4, 0 | 4, 0 | 4, 1 | 4, 0 | 4, 0 |
| Gilliam | 2 | 2, 0 | 2, 10 | 2, 2 | 2, 4 | 2, 32 | 2, 1 | 2, 4 |
| Norstein | 7 | 6, 0 | 7, 6 | 6, 0 | 7, 1 | 6, 1 | 6, 0 | 6, 0 |
| **total** | **36** | **32, 0** | 36, 30 | 34, 6 | 35, 10 | 35, 63 | 33, 2 | 34, 6 |

mixing's adaptive threshold applied to the lint's own full-rate 320×180 frames found every cut, but with 350 false cuts (`level`) and 131 (`spike`). It is calibrated on 64×36 frames, so those stages cannot be dropped in on the lint's frames as they are.

## Reading

- **The histogram detector's misses are hard cuts between shots of one palette.** These are South Park's two Cartman/Heidi reverse shots, OverSimplified's photo-to-title-card cut (both on black), and one dark Norstein cut. mixing's spike rule catches most of them.
- **mixing's false cuts are motion.** These are Kurzgesagt's camera moves, Gilliam's and Norstein's fast motion and grain, and OverSimplified's crowds.
- **One label decides "no false cut".** At 56.6 s in Kurzgesagt, a character fades and slides in while the planet stays in frame. It is labelled a transition here, so it counts neither way. Read as a camera move, it makes the histogram's two detections there false (32/36, 2 false, level with 5 Hz spike).
- **For a lint that measures cut rate, shot length and cadence, a false cut is the worse error.** It splits a shot, and it hides a cadence step, because the step into a cut is skipped.
- **Blind spot:** dissolves are not detected by any of these detectors, so they are not measured here. Recall is relative to the cuts at least one of the four detectors found.
- **Not tested:** PySceneDetect (`strategy="pyscenedetect"`, not installed here), mixing's `min_shot_s`, and other `sigmas` values.
- **The calibration cuts both ways.** The style specs' cut-rate targets were measured with the histogram detector, so they inherit its misses. On the hand labels, South Park cuts 16.5 times a minute, against a target of [10, 14] (measured 12.4). Kurzgesagt makes 5.0 hard cuts a minute, against [6, 8] (measured 7.0, which counts that one slide twice). A render checked against its exact IR shot list measures true cuts, so the bands were re-derived to hold both counts (cutan#160): cuts per minute South Park [11, 19], Kurzgesagt [4, 8], OverSimplified [8, 12], Norstein [4, 9]; mean shot length South Park [2.5, 5] s, Kurzgesagt [6, 13] s.

The scripts, labels and contact sheets are kept with the agent working notes for cutan#151. They are not committed, because the sheets are frames of copyrighted clips.
