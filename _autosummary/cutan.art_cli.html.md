# cutan.art_cli

`an art ...` — art from an image model, keyed and fitted for a cut-out art package (cutan#100).

Thin string-typed wrappers over [`cutan.carve.generate`](cutan.carve.generate.html.md#module-cutan.carve.generate), dispatched by typer
the same way as `an character ...` (the `cli.art` service):

> an art generate SPEC.json –out assets/environments/car/plates [–only cabin,road]

The spec is `{name: {prompt, size, background, key, fit, model, quality}}`;
each image becomes `<name>.png` with its provenance in `art_sources.json`.

### Functions

| [`generate`](#cutan.art_cli.generate)(spec, out[, only, keep_raw, ...])   | Generate each image of a spec with an image model, key its backdrop colour to alpha, fit it, and write it with its provenance.   |
|-----------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------|

### cutan.art_cli.generate(spec, out, only='', keep_raw=False, overwrite=False, model='')

Generate each image of a spec with an image model, key its backdrop colour to alpha, fit it, and write it with its provenance.

spec: a JSON file: {name: {prompt, size, background (opaque|transparent), key (magenta|green|a matte recipe), fit [w, h], model, quality}}
out: the folder to write <name>.png and art_sources.json into (an environment’s plates/, a prop’s parts/)
only: comma-separated names to make (default: all)
keep_raw: also write the model’s own image as <name>.raw.png
overwrite: make an image again when <name>.png exists (default: keep it; each generation is billed)
model: the default generator’s model, where the spec names none (default: gpt-image-2)

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)
