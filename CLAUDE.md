# Working in the cutan repo

`cutan` is the cut-out animation genre of [`an`](https://github.com/thorwhalen/an), split out of it per ADR 0001. It is being created now; most of the code it will hold still lives in `an`.

## Read first

- The plan: `misc/docs/plan_core_and_cutan_2026-10.md` in the `an` repo, phase P8. Its §1 decisions are taken; do not reopen them.
- ADR 0001 (`misc/docs/adr/0001-core-genre-split.md` in `an`): the boundary rule, persisted identifiers (decision 9), and the order of work (decision 8: expand, migrate, contract).
- The module map: `misc/docs/core_from_three_genres.md` §5 in `an` (what is core, what is `an.stage`, what is `cutan`).
- `an`'s `CLAUDE.md` and `misc/docs/architecture_as_built.md`: the core's current shape and its invariants. Until a module moves, its rules live there.
- Tracking: issue [thorwhalen/an#225](https://github.com/thorwhalen/an/issues/225) under the epic [thorwhalen/an#231](https://github.com/thorwhalen/an/issues/231).

## Rules for the move

- **One batch at a time, each green on both sides.** A batch moves a set of modules here and leaves a deprecation re-export at the old `an` path for one release. `an`'s full suite and the corpus contract hashes stay unchanged after every batch.
- **Persisted identifiers never change** (`cutan/__init__.py` lists them): `renderer: cutout`, the genre slug `cutout_animation`, the `CharacterDescriptor` document kind and its `schema_version`, the `character` asset kind and `characters` store, the action kinds `play` and `expression`, the wire shape of the compiled document.
- **The genre is registered from one place only.** `an` ships it until the batch that moves the `CUTOUT` object; that batch adds the `an.genres` entry point here (name `cutout_animation`, value `cutan.genre:CUTOUT`) and removes `an`'s in-distribution line in the same coordinated release. `tests/test_scaffold.py` holds the rule.
- **`an` never imports `cutan` at module level** (the import firewall in `an`'s `tests/test_import_firewall.py`). If a move needs `an` to know about a cut-out concept, add a registry or hook in `an` first.
- **The pixel gate stays with the core.** A batch that can change a pixel gets `an`'s `run-browser-tests` label on its `an` PR. Never write that a rendering behaviour is "verified in CI" without saying where.
- Local packages carry no version pins: `an`, not `an>=…`.
- **Publishing is off** (`[tool.wads.ci.publish] enabled = false`) until the first batch gives the package real content; that batch turns it on.

## Data

The genre's library root is `~/.local/share/cutan` (`CUTAN_HOME` overrides it), resolved by `an.library.root.library_root(package="cutan")`. Nothing in this repository holds assets or project data.
