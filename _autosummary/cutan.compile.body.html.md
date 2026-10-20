# cutan.compile.body

Derive a body-attached prop’s placement from its character, in every shot.

A prop that declares `metadata.body_attachment` ([`cutan.body_attachment`](cutan.body_attachment.html.md#module-cutan.body_attachment))
and is placed WITHOUT `stage.at` is placed by its body: before the scene is
built (the `body_placement` compile pass, order 90), its `stage.at` and
`stage.scale` are derived from where its character stands in this shot, by
[`cutan.body_attachment.place_body_prop()`](cutan.body_attachment.html.md#cutan.body_attachment.place_body_prop). The attachment is then declared
once, in the character’s own units (its bones), and every framing (a two-shot,
a close-up) derives the same relation: the prop’s size relative to the
character and its anchor on the body cannot drift between shots.

A prop placed WITH `stage.at` keeps the author’s placement, and
`cutout.body_attachment` checks it against the same derivation.

Nothing changes for a stored scene: no prop declared a body attachment before
this existed, and a prop that declares none is never touched.

```pycon
>>> from an.ir.schema import Shot
>>> derive_body_placements(Shot(id="s"), {}).id
's'
```

### Functions

| [`derive_body_placements`](#cutan.compile.body.derive_body_placements)(shot, mall)   | `shot` with every body-attached prop that has no `stage.at` placed by its body.   |
|---------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------|

### cutan.compile.body.derive_body_placements(shot, mall)

`shot` with every body-attached prop that has no `stage.at` placed by
its body. Returns `shot` itself when nothing is derived. A prop whose
placement cannot be derived (no character in the shot, the character in the
default layout or mirrored, a socket naming a missing bone, unmeasurable
art, crossed limbs) is left as it is: `cutout.body_attachment` says why.

* **Return type:**
  [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)
