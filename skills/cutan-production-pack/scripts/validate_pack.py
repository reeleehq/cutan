"""Check a cut-out production pack with cutan's own validators.

A thin front for :func:`cutan.pack.check_pack` (the checker lives in the
package so the reelee connector's "check this pack" tool and this script run
the same code). It lints every SVG and voice document, builds a scratch
project from the pack, runs ``cast.sh`` (only the factory commands the skill
documents, never a shell), validates every character and prop, and runs
``an validate --strict-assets`` on the scene. Nothing is rendered.

It needs ``pip install cutan`` (pure Python, no browser), which brings ``an``.
Where installing is impossible (Claude.ai's sandbox), use the reelee
connector's check tool instead, or the checklist in ``references/checklist.md``.
Exit status: 0 when nothing failed, 1 otherwise.

    python validate_pack.py path/to/pack            # check, then delete the scratch project
    python validate_pack.py path/to/pack --keep     # keep it and print where it is
    python validate_pack.py path/to/pack --json     # the report as data
"""

from __future__ import annotations

import sys

try:
    from cutan.pack import main
except ImportError:  # no cutan, or one older than the packaged checker
    sys.exit(
        "FAIL: this check needs cutan's packaged checker: run `pip install -U cutan` "
        "(it brings the `an` engine), then try again."
    )

if __name__ == "__main__":
    sys.exit(main())
