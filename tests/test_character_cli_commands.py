"""The `an character ...` sub-commands, pinned by literal in the genre that owns them.

`an` used to spell these out in its own CLI test, so every new cutan
sub-command (cutan#71's `add-half-lid`) broke every lane of `an`. The core pins
its own commands; the genre pins its own, here, beside the list it guards.

MUTATION: delete any command from `cutan.characters.cli._dispatch_funcs`. The
per-command tests delete their own case along with the command, so only a
literal catches it.
"""

from __future__ import annotations

from cutan.characters.cli import _dispatch_funcs


def test_the_character_command_set_is_pinned_by_literal():
    assert [f.__name__.replace("_", "-") for f in _dispatch_funcs] == [
        "new",
        "mouths",
        "add-gaze",
        "add-half-lid",
        "add-views",
        "validate",
        "capabilities",
        "contract",
        "silhouette",
        "preview",
        "record",
    ]
