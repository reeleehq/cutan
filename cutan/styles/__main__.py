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
    try:
        if args.name is None:
            if args.path:
                parser.error("--path needs a style name")
            for name in style_specs():
                spec = style_spec(name)
                _write(
                    f"{name}\t{spec.get('cost_class', '')}\t{spec.get('title', '')}\n"
                )
        elif args.path:
            _write(f"{style_spec_path(args.name)}\n")
        else:
            _write(style_spec_text(args.name))
    except (UnknownStyleError, OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    return 0


def _write(text: str) -> None:
    """UTF-8 to stdout whatever the console's encoding (a spec may hold any character)."""
    sys.stdout.flush()
    sys.stdout.buffer.write(text.encode("utf-8"))
    sys.stdout.buffer.flush()


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
