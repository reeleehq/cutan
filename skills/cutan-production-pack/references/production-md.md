# PRODUCTION.md: the brief for humans

`PRODUCTION.md` is what the pipeline owner reads first, and what the writer checks to see that you understood them. Plain prose and tables; no code. Sections, in this order (leave out one that has nothing to say):

1. **Title and logline**: one or two sentences.
2. **Length and look**: total length, resolution and frame rate, the named style if any with its cost class, or the palette and mood in words.
3. **Cast**: a table, one row per character: id (as in `cast.sh`), who they are in a line, how they look (and why: what tells them apart), how they sound (age, accent, pitch, pace, attitude: the pipeline owner casts a voice from this), the moods their lines use.
4. **Sets and props**: each environment and prop, what it shows, which you drew (and that they are your own drawings), and anything you described but could not draw.
5. **Shot list**: a table: shot id, length, framing (wide, two-shot, close single), camera, what happens in a line.
6. **Sound**: music and effects the film wants, described (the pack carries no audio).
7. **Decisions I made**: every choice the writer did not ask for (a colour, a gait, a camera move, a style rule you departed from) with a reason in a few words.
8. **Open questions**: what the writer or the pipeline owner still has to decide (voice casting, licences for drawings, art to commission).
9. **Check**: the validator's final line (for example `PASS: 13/13 checks passed, 0 warning(s)`) and its remaining warnings, or "Not validated: checked by hand against the checklist."

`examples/the-umbrella/PRODUCTION.md` shows the shape.
