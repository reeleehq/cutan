"""``python -m cutan.styles [NAME] [--path]``: list the style specs, print one, or its path.

With no name, one line per spec: its name, cost class and title. With a name,
the spec's YAML (comments included), or with ``--path`` the file it lives in.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence

from cutan.styles import (
    UnknownStyleError,
    style_spec,
    style_spec_path,
    style_spec_text,
    style_specs,
)


def _main(argv: Sequence[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="python -m cutan.styles",
        description="The named cut-out style specs that ship with cutan.",
    )
    parser.add_argument("name", nargs="?", help="a style name; omit it to list them")
    parser.add_argument(
        "--path", action="store_true", help="print the spec file's path, not its text"
    )
    args = parser.parse_args(list(argv))
    if args.name is None:
        for name in style_specs():
            spec = style_spec(name)
            print(f"{name}\t{spec.get('cost_class', '')}\t{spec.get('title', '')}")
        return 0
    try:
        if args.path:
            print(style_spec_path(args.name))
        else:
            sys.stdout.write(style_spec_text(args.name))
    except UnknownStyleError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
