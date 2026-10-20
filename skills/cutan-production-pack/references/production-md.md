# PRODUCTION.md: the brief for humans

`PRODUCTION.md` is what the pipeline owner reads first, and what the writer checks to see that you understood them. Plain prose and tables; no code. Sections, in this order (leave out one that has nothing to say):

1. **Title and logline**: one or two sentences.
2. **Length and look**: total length, resolution and frame rate, the named style if any with its cost class, or the palette and mood in words.
3. **Cast**: a table, one row per character: id (as in `cast.sh`), who they are in a line, how they look (and why: what tells them apart), how they sound (age, accent, pitch, pace, attitude: the same words as the voice document's `notes`, which voices are designed from), the moods their lines use.
4. **Sets, props and art**: each environment and prop, what it shows, and where its art came from: the writer's pictures (which generator or artist, which prompt), your own SVG drawings (say so: they are placeholders unless the writer chose the flat look), or not yet made (with the prompt or the brief for it). Reference sheets under `reference/`, and what the pipeline owner must still do with them.
5. **Shot list**: a table: shot id, length, framing (wide, two-shot, close single), camera, what happens in a line.
6. **Sound**: music and effects the film wants, described (the pack carries no audio).
7. **Decisions I made**: every choice the writer did not ask for (a colour, a gait, a camera move, a style rule you departed from) with a reason in a few words.
8. **Voices chosen**: for each voice, the option the writer chose in the voice-design round and its `voice_id`, or "not designed yet".
9. **Open questions**: what the writer or the pipeline owner still has to decide (voice casting, licences for drawings, art to commission).
10. **Check**: the check's final line (from the connector's check tool or the validator) (for example `PASS: 13/13 checks passed, 0 warning(s)`) and its remaining warnings, or "Not validated: checked by hand against the checklist."

`examples/the-umbrella/PRODUCTION.md` shows the shape.
