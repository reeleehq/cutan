# Cut detection for the style lint: the histogram jump vs `mixing.video.shots` (cutan#151)

Measured 2026-11-02. **Decision: keep `cutan.verify.style`'s histogram-jump detector. It found 34 of 37 hand-labelled cuts and no false one. Offer it to `mixing` as a shot strategy** (reeleehq/mixing#164).

## The question

Without an IR shot list (any mp4), `cutan.verify.style` finds cuts itself. A frame counts as a cut when the L1 distance between its 8×8×8 colour histogram and the previous frame's exceeds 0.6 and the mean grey difference exceeds 8. `mixing.video.shots` is the fleet's shot detector. Its `"diff"` strategy samples the video at a low frame rate as 64×36 grayscale frames, takes the mean absolute difference, and applies an adaptive threshold, using either the `"level"` or the `"spike"` rule. The question was whether the lint should take its cuts from mixing.

## Method

- The six study clips of the cut-out styles research (an `misc/docs/cutout_styles_research.md` §3). They are kept outside every repository.
- For each clip, the candidate cuts are the union of four detectors' outputs, merged within 0.6 s. The four are: the histogram detector, mixing `diff` at 2 Hz `level` (its default), mixing `diff` at 5 Hz `spike`, and mixing's array stages run on the lint's own full-rate 320×180 frames with the `spike` rule.
- Each candidate was labelled real or not by eye from before/after frames. Cuts that none of the four found are not counted, so recall is relative to that union.
- A detector's cut matches a labelled cut within 0.6 s. Three dark Norstein candidates and one OverSimplified text overlay were unclear and count neither way.

## Result (true cuts found / labelled, false cuts)

| clip | labelled | histogram | 2 Hz level (mixing default) | 2 Hz spike | 5 Hz level | 5 Hz spike | full-rate level | full-rate spike |
|---|---|---|---|---|---|---|---|---|
| South Park | 8 | 6, 0 | 8, 0 | 8, 0 | 8, 0 | 8, 0 | 8, 1 | 8, 1 |
| OverSimplified | 10 | 10, 0 | 10, 6 | 9, 2 | 10, 13 | 10, 1 | 10, 20 | 10, 0 |
| Kurzgesagt | 6 | 6, 0 | 6, 12 | 5, 5 | 6, 22 | 3, 0 | 6, 110 | 5, 0 |
| Reiniger | 4 | 4, 0 | 4, 0 | 4, 0 | 4, 1 | 4, 0 | 4, 23 | 4, 5 |
| Gilliam | 2 | 2, 0 | 2, 10 | 2, 2 | 2, 32 | 2, 1 | 2, 109 | 2, 59 |
| Norstein | 7 | 6, 0 | 7, 6 | 6, 0 | 6, 1 | 6, 0 | 7, 119 | 7, 52 |
| **total** | **37** | **34, 0** | 37, 34 | 34, 9 | 36, 69 | 33, 2 | 37, 382 | 36, 117 |

The full-rate columns use mixing's adaptive threshold, which is calibrated on 64×36 frames, on 320×180 frames. They show that the mixing stages cannot be dropped in on the lint's frames as they are.

## Reading

- **What the lint measures is cut rate and shot length.** A false cut ruins both, and it also removes a step from the cadence statistics, which skip the step into a cut. The histogram detector has no false cuts on these clips. mixing's default reads Kurzgesagt's camera moves and Gilliam's and Norstein's fast motion and grain as cuts.
- **The histogram's misses are reverse shots in one palette.** These are South Park's Cartman/Heidi cuts (2) and one dark Norstein cut. mixing's spike rule catches them. The union of the histogram detector and 5 Hz spike scored 36/37 with 2 false. That is a possible later improvement, but adopting it means re-measuring the cut-rate targets of every style spec (the module's rule: an estimator changes only together with its targets).
- The cut-rate targets in the style specs were calibrated with the histogram detector. Switching detectors would measure a different quantity against them.

The scripts and contact sheets are kept with the agent working notes for cutan#151. They are not committed, because the sheets are frames of copyrighted clips.
