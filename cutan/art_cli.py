"""``an art ...`` — art from an image model, keyed and fitted for a cut-out art package (cutan#100).

Thin string-typed wrappers over :mod:`cutan.carve.generate`, dispatched by typer
the same way as ``an character ...`` (the ``cli.art`` service):

    an art generate SPEC.json --out assets/environments/car/plates [--only cabin,road]

The spec is ``{name: {prompt, size, background, key, fit, model, quality}}``;
each image becomes ``<name>.png`` with its provenance in ``art_sources.json``.
"""

from __future__ import annotations

__all__ = ["generate"]


def generate(
    spec: str,
    out: str,
    only: str = "",
    keep_raw: bool = False,
    overwrite: bool = False,
    model: str = "",
) -> str:
    """Generate each image of a spec with an image model, key its backdrop colour to alpha, fit it, and write it with its provenance.

    spec: a JSON file: {name: {prompt, size, background (opaque|transparent), key (magenta|green|a matte recipe), fit [w, h], model, quality}}
    out: the folder to write <name>.png and art_sources.json into (an environment's plates/, a prop's parts/)
    only: comma-separated names to make (default: all)
    keep_raw: also write the model's own image as <name>.raw.png
    overwrite: make an image again when <name>.png exists (each generation is billed)
    model: the default generator's model, where the spec names none (default: gpt-image-2)
    """
    from cutan.carve.generate import AixGenerator, generate_art

    made = generate_art(
        spec,
        out_dir=out,
        generator=AixGenerator(model=model) if model else None,
        only=[n.strip() for n in only.split(",") if n.strip()] or None,
        keep_raw=keep_raw,
        overwrite=overwrite,
    )
    lines = [f"{a.path}  {a.size[0]}x{a.size[1]}  ({a.source.provider}, {a.source.license})" for a in made]
    return "\n".join(lines + [f"provenance: {made[0].path.parent / 'art_sources.json'}"] if made else ["nothing made"])


_dispatch_funcs = [generate]
