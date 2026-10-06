# cutan.styles.copies

Copies of a style spec, and whether they are stale (cutan#19).

A spec changes between cutan releases (targets re-measured, roles re-cast), and
what a production copies out of it is a snapshot: the StylePack
([`cutan.styles.style_pack()`](cutan.styles.html.md#cutan.styles.style_pack)), a voice cast to one of the spec’s roles
([`style_voice()`](#cutan.styles.copies.style_voice)), a kit’s members built from them. Each copy records where
it came from in `metadata.style_spec = {name, sha256}` ([`spec_origin()`](#cutan.styles.copies.spec_origin)),
and `an validate` compares that digest with the installed spec’s
([`check_style_copies()`](#cutan.styles.copies.check_style_copies)): a copy of an older spec is said, with what to
re-derive. A copy from a spec file, or one that records no digest, is never
compared (only a shipped spec has an installed version to compare with).

```pycon
>>> spec_origin("south_park")["name"]
'south_park'
```

### Module Attributes

| [`SPEC_ORIGIN_KEY`](#cutan.styles.copies.SPEC_ORIGIN_KEY)   | Where a copy records the spec it came from, inside its `metadata`.   |
|--------------------------------------------------------------------|----------------------------------------------------------------------|

### Functions

| [`check_style_copies`](#cutan.styles.copies.check_style_copies)(ctx)           | `an validate`: the style pack the scene names, and every voice its lines speak with, warn when they were copied from an older version of the shipped spec they record (cutan#19).   |
|------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`spec_origin`](#cutan.styles.copies.spec_origin)(spec)                 | `{name, sha256}` of the spec `spec` names (a shipped style's name, a file), as a copy records it; no `sha256` for an in-memory mapping.                                             |
| [`stale_copy_problem`](#cutan.styles.copies.stale_copy_problem)(doc, \*, what) | Why `doc` (a copy that recorded its spec) is stale, or `None`: the shipped spec it names has changed since the copy was made.                                                       |
| [`style_voice`](#cutan.styles.copies.style_voice)(spec, role)           | The partial voice document `spec` casts `role` as (<br/><br/>```<br/>``<br/>```<br/><br/>an.audio.takes.                                                                            |

### cutan.styles.copies.SPEC_ORIGIN_KEY *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'style_spec'*

Where a copy records the spec it came from, inside its `metadata`.

### cutan.styles.copies.check_style_copies(ctx)

`an validate`: the style pack the scene names, and every voice its lines
speak with, warn when they were copied from an older version of the shipped
spec they record (cutan#19). Once per validation.

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### cutan.styles.copies.spec_origin(spec)

`{name, sha256}` of the spec `spec` names (a shipped style’s name, a
file), as a copy records it; no `sha256` for an in-memory mapping.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### cutan.styles.copies.stale_copy_problem(doc, , what)

Why `doc` (a copy that recorded its spec) is stale, or `None`: the
shipped spec it names has changed since the copy was made.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### cutan.styles.copies.style_voice(spec, role)

The partial voice document `spec` casts `role` as (`an.audio.takes.
style_voice_role`: target names resolved to values), with the spec it came
from recorded, so a later re-measure of the style is noticed. Merge it beside
a `voice_id`: `{**style_voice("oversimplified", "eager"), "voice_id": ...}`.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

```pycon
>>> doc = style_voice("oversimplified", "narrator")
>>> doc["metadata"]["style_spec"]["name"], "targets" in doc["takes"]["cues"]["deadpan"]
('oversimplified', True)
```
