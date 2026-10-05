# Working in the cutan repo

`cutan` is the cut-out animation genre of [`an`](https://github.com/thorwhalen/an), split out of it per ADR 0001 (an#225, epic an#231). It depends on `an`; `an` never imports it (except through the registered hooks, `an.genres`).

## Read first

- `an`'s `CLAUDE.md` and `misc/docs/architecture_as_built.md` (§0a: core and genre, the seams this package plugs into). Decisions and the plan: `misc/docs/adr/0001-core-genre-split.md` and `misc/docs/plan_core_and_cutan_2026-10.md` in `an`.
- This repo's skills (`.claude/skills/`): `cutan` (downstream: authoring cut-out scenes), `cutan-style`, `cutan-art-package`, and `cutan-dev-{expression,lipsync,rig-contract,swap-channels}` for the areas of the same names. Read the matching `cutan-dev-*` before touching a face, lip-sync, the rig contract or swap channels; for a pixel, an encode flag or the camera, the `an-dev-render-pipeline` and `an-dev-stage` skills in `an`.

## Layout

```
cutan/genre.py        CUTOUT, the Genre object (entry point cutout_animation = "cutan.genre:CUTOUT"); nw.py: the nw declaration
cutan/characters/     descriptor schema (CharacterDescriptor), factory, play resolution, methods, vocabulary, checks, CLI
cutan/expression/     expression presets, axes, bindings, the face provider
cutan/compile/        passes.py (the cut-out passes over an.stage.compile), lowering.py (play/expression lowering, swap declaration), coarticulate.py, gaze.py
cutan/audio/          lip-sync providers (offline, rhubarb, whisper, word timings)
cutan/impacts/        impact choreography and ground truth;  cutan/verify/style.py: the style lint;  cutan/library.py: the character analyser
cutan/carve/          photo/frame → matted, provenance-carrying part: matte strategies, refine, head mode, split_parts, write_prop (cutan[carve])
cutan/styles/         the named style specs (*.yaml, package data) and their loader: style_spec(name), style_specs(); python -m cutan.styles
cutan/motion.py       the rig presets (nod, point, turn, walk, waddle, speech_pulse; an#322) and PRESETS, the table a `play` resolves in
cutan/runtime/        visuals.js: the procedural mouth and eye, registered through the stage runtime's anRegisterVisual
cutan/bench.py        CUTOUT_FIXTURES and run_bench() over this repo's misc/bench/ corpus
tests/  examples/  misc/bench/{corpus,golden}/  misc/demos/  misc/docs/ (design notes: locomotion_gaits.md)  .claude/skills/
```

## Rules

- **Persisted identifiers never change** (`cutan/__init__.py` lists them): `renderer: cutout`, the genre slug `cutout_animation`, the `CharacterDescriptor` document kind and its `schema_version`, the `character` asset kind and `characters` store, the action kinds `play` and `expression`, the compiled document's wire shape, the provenance provider string `"an character factory"` (licence `cc0-1.0`), the lip-sync provider names, the swap set names (`viseme`, `eyelid`, `view`, `hands`, `body_facing`) and the visual kinds `mouth` and `eye`.
- **The pixel gate stays with the core.** The corpus contract hashes (`tests/test_expression_compose.py`) and the blessed golden frames (`misc/bench/golden/`) must not move without a bless record that says why. A PR here that can change a pixel is exercised against `an` main in CI. Never write that a rendering behaviour is "verified in CI" without saying where.
- **Import `an` freely; `an` imports nothing of `cutan`.** If the core needs something from this package, add a registry or hook in `an` first (a service, `ActionKind.lowering`, `EntityKind.swap_declaration`, a compile pass, a runtime script). The compile passes may import `an.stage.compile` helpers (underscore names included): a genre depending on the core is allowed.
- **A change to any module here changes the core's shot-cache key** (`an.stage.cache_key.genre_code_modules` keys every module of this package), so a cut-out shot re-renders after an upgrade. That is intended.
- `cutan.REQUIRED_AN_API_LEVEL` is the lowest `an.genres.API_LEVEL` this package runs against (instead of a version pin: `an`'s version is assigned by CI at merge). Raise it in the same change that uses a new seam.
- Local packages carry no version pins: `an`, not `an>=…`.
- One `CLI`: `cutan` adds no console script. Its commands are `an character …` and `an impacts …`.
- Shims in `an` (`an.characters`, `an.expression`, `an.impacts`, `an.audio.*_lipsync`, `an.verify.style`, `an.library.character`, `an.genres.cutout`, `an.genre`, `an.adapters.cutout.{coarticulate,gaze}`, and the rig presets' names in `an.motion`, an#322) are removed when no package under `$PP` imports an old path and 14 days have passed (checked by a script, not by memory).
- Decisions of the move (the lead's, 2026-10-02): the bench *runner* stays in `an` (generic); skill names `cutan-style` and `cutan-dev-*`, with stubs of the old names left in `an` for one cycle; `an.genres.API_LEVEL` instead of a version floor.

## Tests

`pytest` from the repo root runs the tests and the doctests (`--doctest-modules` over `cutan/`, as CI does). The render tests are gated like `an`'s (`tests/conftest.py`): they need a headless browser and `ffmpeg`, and skip with a stated reason where those are absent. Tests that load a committed project in place depend on `scene.md` and `ir/scene.json` having the same age, which a fresh checkout gives them.

## Data

The genre's library root is `~/.local/share/cutan` (`CUTAN_HOME` overrides it), resolved by `an.library.root.library_root(package="cutan")`. Nothing in this repository holds assets or project data beyond the committed corpus and examples.
