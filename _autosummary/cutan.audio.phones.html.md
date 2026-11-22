# cutan.audio.phones

Phones to mouth shapes: the core’s tables (`an.audio.phones`), and this genre’s art direction.

The phone to Rhubarb-shape mapping, the alphabet detection and the phone-track
builder live in the core (`an.audio.phones`, an#727); this module re-exports
them under their old names and adds what is the cut-out genre’s own:
[`TONGUE_ONLY_INTENSITY`](#cutan.audio.phones.TONGUE_ONLY_INTENSITY) (cutan#157), passed as `intensity_of=`.

```pycon
>>> [(v.time, v.code) for v in phones_to_visemes(
...     [("HH", 0.1, 0.2), ("AH0", 0.2, 0.3), ("L", 0.3, 0.4), ("OW1", 0.4, 0.6)],
...     total_duration=1.0,
... )]
[(0.0, 'X'), (0.1, 'C'), (0.3, 'H'), (0.4, 'F'), (0.6, 'X'), (1.0, 'X')]
```

### Module Attributes

| [`PHONES_CACHE_VERSION`](#cutan.audio.phones.PHONES_CACHE_VERSION)   | a lip-sync track cached before they did is re-aligned once (an#727).                                                                                                                      |
|-------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`TONGUE_ONLY_INTENSITY`](#cutan.audio.phones.TONGUE_ONLY_INTENSITY)  | How strongly a phone's shape holds against its neighbours in the co-articulation vote (`Viseme.intensity`; the vote weighs `DOMINANCE[shape] x intensity`, `cutan.compile.coarticulate`). |

### cutan.audio.phones.PHONES_CACHE_VERSION *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'phones-1'*

a lip-sync
track cached before they did is re-aligned once (an#727).

* **Type:**
  The `cache_version` of the providers that read a take’s phones

### cutan.audio.phones.TONGUE_ONLY_INTENSITY *: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [float](https://docs.python.org/3/builtins/functions.html#float)]* *= {'D': 0.4, 'G': 0.4, 'K': 0.4, 'L': 0.4, 'N': 0.4, 'NG': 0.4, 'S': 0.4, 'T': 0.4, 'Z': 0.4, 'd': 0.4, 'g': 0.4, 'k': 0.4, 'l': 0.4, 'n': 0.4, 's': 0.4, 't': 0.4, 'z': 0.4, 'ŋ': 0.4, 'ɡ': 0.4}*

How strongly a phone’s shape holds against its neighbours in the co-articulation
vote (`Viseme.intensity`; the vote weighs `DOMINANCE[shape] x intensity`,
`cutan.compile.coarticulate`). Rhubarb’s `B` codes both the EE vowel (lips
spread) and the tongue-only consonants (T D N K…), which barely move the
lips (JALI, Edwards et al. 2016: “tongue-only visemes have no influence on
the lips”); the letter alone cannot say, the phone can. Keyed by the phone’s
base in either alphabet (ARPAbet upper case, IPA as written); a phone not
listed is 1.0. Values are art direction (cutan#157): a measurement, not a
sourced number.
