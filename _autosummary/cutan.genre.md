# cutan.genre

The cut-out animation genre, declared as one object.

ADR 0001 §First slice: the cut-out genre’s IR extensions register through the
same door any genre uses — the `an.genres` entry point (this distribution’s
`pyproject.toml` declares `cutout_animation = "cutan.genre:CUTOUT"`) —
instead of being wired into the core. `CUTOUT` lists:

- **action kinds** `play` ([`cutan.characters.registration`](cutan.characters.registration.md#module-cutan.characters.registration)) and
  `expression` ([`cutan.expression.registration`](cutan.expression.registration.md#module-cutan.expression.registration));
- **entity kind** `character`, whose nodes are stage nodes (`stage.node`);
- the **\`\`[emotion]\`\`** dialogue sugar;
- its **semantic checks**: `play` and `expression` resolution, brow
  acting on a character whose brows cannot act (an#252), the turn
  checks (contradicted `from_direction`, a mouth hidden while speaking) and
  view continuity across a cut, placed in the report where they always were;
- its **capabilities** and the **character analyser** (ADR 0002:
  [`cutan.library`](cutan.library.md#module-cutan.library)), its **vocabulary** (motion and expression
  > presets, IR-field notes: [`cutan.characters.vocabulary`](cutan.characters.vocabulary.md#module-cutan.characters.vocabulary); the methods:

  [`cutan.characters.methods`](cutan.characters.methods.md#module-cutan.characters.methods)) and its **aspects**, `locomotion`,
  : `speech` and `expression`, each with a default chain that ends in a
    method requiring nothing.

Its `name` is the persisted genre slug `cutout_animation`, the one
`cutan.nw` declares to `nw` (ADR 0001 decision 9: persisted identifiers do
not change). It also offers the core **services** (`an.genres.register_service()`):
the `an character` / `an impacts` CLI namespaces, the `offline` / `rhubarb` /
`whisper` lip-sync providers, the licence lookup for pre-`source` descriptors, the
library’s publish warning and the expression labels `judge_emotion` uses; and the
**runtime script** that draws the mouth and the eye.

Importing this module registers nothing: `an.genres.load()` (or
`an.genres.register_genre()`) does.

```pycon
>>> CUTOUT.provides()["action kinds"]
('play', 'expression')
```

### Module Attributes

| [`CUTOUT_GENRE_NAME`](#cutan.genre.CUTOUT_GENRE_NAME)   | The genre's persisted slug (also `cutan.nw.CUTOUT_ANIMATION_SLUG`).   |
|----------------------------------------------------------------------|-----------------------------------------------------------------------|

### cutan.genre.CUTOUT_GENRE_NAME *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'cutout_animation'*

The genre’s persisted slug (also `cutan.nw.CUTOUT_ANIMATION_SLUG`).
