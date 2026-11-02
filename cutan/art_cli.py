"""``an art ...`` — art from an image model, keyed and fitted for a cut-out art package (cutan#100).

Thin string-typed wrappers over :mod:`cutan.carve.generate`, dispatched by typer
the same way as ``an character ...`` (the ``cli.art`` service):

    an art generate SPEC.json --out assets/environments/car/plates [--only cabin,road]
    an art critique-plates [--project DIR]      # far plates of a travel holding near things

The spec is ``{name: {prompt, size, background, key, fit, model, quality}}``;
each image becomes ``<name>.png`` with its provenance in ``art_sources.json``.
"""

from __future__ import annotations

__all__ = ["generate", "critique_plates"]


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
    overwrite: make an image again when <name>.png exists (default: keep it; each generation is billed)
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
    lines = [
        f"{a.path}  {a.size[0]}x{a.size[1]}  "
        + (
            "(kept: already there; --overwrite makes it again)"
            if a.kept
            else f"({a.source.provider}, {a.source.license or 'licence unknown'})"
        )
        for a in made
    ]
    if not made:
        return "nothing made"
    return "\n".join(
        [*lines, f"provenance: {made[0].path.parent / 'art_sources.json'}"]
    )


def critique_plates(project: str = ".", model: str = "") -> str:
    """Ask a vision model whether each plate a travel lists `far` holds anything near (a tree, a pole, the road close up), which would stand still while the scenery streams past (a paid call per plate; warnings, never the gate).

    project: the project folder
    model: the vision model (default: an's vision judge's)
    """
    from an.cli_status import failed

    from cutan.verify.critic import critique_far_plates

    report = critique_far_plates(project, model=model or None)
    lines = [f"[{sev}] {where}: {msg}" for sev, where, msg in report.findings]
    lines.append(
        f"{len(report.calls)} judge call(s): " + ", ".join(c["plate"] for c in report.calls)
        if report.calls
        else "no far plate with a raster image to judge"
    )
    text = "\n".join(lines)
    return failed(text) if any(sev == "error" for sev, _, _ in report.findings) else text


_dispatch_funcs = [generate, critique_plates]
