# cutan.carve.generate

Generated art: a prompt in, a keyed, fitted, provenance-carrying plate or part out (cutan#100).

An image model draws a plate (a landscape, a car’s cabin) or a part; where the
art must be see-through (a car’s windows) the prompt asks for a flat key colour,
and that colour is keyed to alpha by [`cutan.carve`](cutan.carve.html.md#module-cutan.carve)’s own matte (the
`chroma` strategy), its rim de-spilled, then the image is cover-fitted to the
stage canvas and written as a PNG beside a record of where it came from.

```pycon
>>> from PIL import Image
>>> def painter(prompt, *, size, background, quality=None, model=None):
...     im = Image.new("RGB", (64, 48), (246, 3, 242))      # the magenta key
...     im.paste((40, 110, 200), (16, 12, 48, 36))          # the subject
...     return im
>>> painter.provider, painter.model, painter.license = "test", "toy", "cc0-1.0"
>>> import tempfile
>>> made = generate_art({"box": {"prompt": "a blue box", "key": "magenta", "fit": [32, 24]}},
...                     out_dir=tempfile.mkdtemp(), generator=painter)
>>> made[0].path.name, made[0].size, made[0].source.license
('box.png', (32, 24), 'cc0-1.0')
```

- **The spec** ([`art_specs()`](#cutan.carve.generate.art_specs)): `{name: {prompt, size, background, key,
  fit, model, quality}}`, a mapping or a JSON file. `background`:
  `"opaque"` or `"transparent"` (the model’s own alpha, where it has one);
  `key`: a named key colour ([`KEYS`](#cutan.carve.generate.KEYS), `"magenta"`) or any matte recipe
  [`as_matte()`](cutan.carve.mattes.html.md#cutan.carve.mattes.as_matte) reads; `fit`: `[w, h]`, scale to
  > cover and centre-crop; `prop`: carve the image into a prop folder
  > (`<name>/prop.json` + `parts/`, through [`carve()`](cutan.carve.html.md#cutan.carve.carve) and

  [`write_prop()`](cutan.carve.html.md#cutan.carve.write_prop), with its quality warnings) instead of a plate.
- **The generator** is the seam: `generator(prompt, *, size, background,
  quality, model) -> PIL image` (or a [`Generated`](#cutan.carve.generate.Generated): the image and facts
  about making it, such as the provider’s revised prompt), carrying
  `provider`, `model` and `license` for the provenance. The default, [`AixGenerator`](#cutan.carve.generate.AixGenerator), calls
  the fleet’s `aix.generate_image()` (OpenAI’s `gpt-image` models by
  default; `pip install "cutan[generate]"`).
- **The record**: each image’s `AssetSource` (provider,
  model, prompt, licence) goes into `art_sources.json` beside the PNGs, to be
  set as the plane’s or the prop’s `source` so `an credits` can say where
  the picture came from.

Needs OpenCV for the key (`cutan[carve]`) and `aix` for the default
generator; nothing here is imported by `import cutan`.

### Module Attributes

| [`DEFAULT_MODEL`](#cutan.carve.generate.DEFAULT_MODEL)         | The model [`AixGenerator`](#cutan.carve.generate.AixGenerator) asks for when the spec names none.                                                                                                                                          |
|------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`DEFAULT_QUALITY`](#cutan.carve.generate.DEFAULT_QUALITY)       | the provider's own default quality (`"high"` is the dearest tier, and not every model has it).                                                                                                                                                      |
| [`OPENAI_OUTPUT_LICENSE`](#cutan.carve.generate.OPENAI_OUTPUT_LICENSE) | The licence code of OpenAI's image output, which its terms assign to the user.                                                                                                                                                                      |
| [`AI_DISCLOSURE`](#cutan.carve.generate.AI_DISCLOSURE)         | The attribution sentence recorded with a generated image (cutan#183): `{provider}` is the provider's display name ([`PROVIDER_NAMES`](#cutan.carve.generate.PROVIDER_NAMES)), `{model}` the model that made it.                              |
| [`PROVIDER_NAMES`](#cutan.carve.generate.PROVIDER_NAMES)        | How a provider id reads in a sentence; any other reads as written.                                                                                                                                                                                  |
| [`SOURCES_FILE`](#cutan.carve.generate.SOURCES_FILE)          | Where each generated image's provenance is written, beside the images.                                                                                                                                                                              |
| [`KEYS`](#cutan.carve.generate.KEYS)                  | a hue band in degrees, and only saturated, bright pixels in it.                                                                                                                                                                                     |
| [`ImageGenerator`](#cutan.carve.generate.ImageGenerator)        | `generator(prompt, *, size, background, quality, model) -> PIL image` (or a [`Generated`](#cutan.carve.generate.Generated): the image and facts about making it), with `provider`, `model` and `license` attributes for the provenance. |
| [`OPENAI_IMAGE_MODELS`](#cutan.carve.generate.OPENAI_IMAGE_MODELS)   | Bare model names (no `provider/` prefix) that LiteLLM routes to OpenAI.                                                                                                                                                                             |
| [`PROVIDER_LICENSES`](#cutan.carve.generate.PROVIDER_LICENSES)     | The licence code of each provider's terms for its image output, by the provider `aix` infers from the model.                                                                                                                                        |

### Functions

| [`art_source`](#cutan.carve.generate.art_source)(spec, generator[, facts, disclosure])   | The provenance of `spec`'s image as `generator` made it; `facts` are what the provider said about this image ([`Generated`](#cutan.carve.generate.Generated)): the model it resolved to wins over the one asked for, and a `revised_prompt` is kept.   |
|-----------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`art_specs`](#cutan.carve.generate.art_specs)(spec)                                    | The [`ArtSpec`](#cutan.carve.generate.ArtSpec) list of a spec mapping or a JSON file of one.                                                                                                                                                         |
| [`cover_fit`](#cutan.carve.generate.cover_fit)(image, size)                             | Scale `image` to cover `size` (w, h), then centre-crop to it.                                                                                                                                                                                                      |
| [`generate_art`](#cutan.carve.generate.generate_art)(spec, \*, out_dir[, generator, ...])  | Generate, key, fit and write each image of `spec` into `out_dir`.                                                                                                                                                                                                  |
| [`key_backdrop`](#cutan.carve.generate.key_backdrop)(image, key)                           | `image` with its key colour keyed to alpha and the rim de-spilled, by [`cutan.carve`](cutan.carve.html.md#module-cutan.carve)'s matte (`key`: a [`KEYS`](#cutan.carve.generate.KEYS) name or a matte recipe).             |
| [`provider_of`](#cutan.carve.generate.provider_of)(model)                                 | The provider of a LiteLLM model name, by LiteLLM's own convention (a `provider/` prefix; OpenAI's image models go bare), without the network lookup LiteLLM's resolver makes; `None` when the name does not say.                                                   |

### Classes

| [`AixGenerator`](#cutan.carve.generate.AixGenerator)([model, quality, licenses])       | The default generator: `aix.generate_image()`, whose model names its provider (OpenAI's `gpt-image` by default).                                                                                                                                                                       |
|-------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`ArtSpec`](#cutan.carve.generate.ArtSpec)(name, prompt[, size, background, ...]) | One image to generate.                                                                                                                                                                                                                                                                 |
| [`Generated`](#cutan.carve.generate.Generated)(image[, facts])                      | What a generator may return instead of a bare image: the image, and facts about making it (`model`: the model the request was resolved to, e.g. aix substituting a configured alias; `revised_prompt`: the prompt the provider says it actually drew), recorded in the image's source. |
| [`GeneratedArt`](#cutan.carve.generate.GeneratedArt)(name, path, source[, size, ...])  | One image of the spec: its path and provenance; `kept` when it was already there and not made again (its provenance read from the record).                                                                                                                                             |

### cutan.carve.generate.AI_DISCLOSURE *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'Images generated with {provider} {model}'*

The attribution sentence recorded with a generated image (cutan#183):
`{provider}` is the provider’s display name ([`PROVIDER_NAMES`](#cutan.carve.generate.PROVIDER_NAMES)),
`{model}` the model that made it. Harmless where a provider’s licence needs
none (it is only read where the licence class asks for an attribution).

### *class* cutan.carve.generate.AixGenerator(model='gpt-image-2', quality=None, licenses=<factory>)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

The default generator: `aix.generate_image()`, whose model names its
provider (OpenAI’s `gpt-image` by default). [`describe()`](#cutan.carve.generate.AixGenerator.describe) says which
provider made an image and under what licence ([`PROVIDER_LICENSES`](#cutan.carve.generate.PROVIDER_LICENSES)).

#### describe(model=None)

`{"provider", "license"}` of an image made with `model`.

```pycon
>>> AixGenerator().describe("gpt-image-2")
{'provider': 'openai', 'license': 'openai-output-owned'}
>>> AixGenerator().describe("gemini/imagen-4.0-generate-001")
{'provider': 'gemini', 'license': None}
```

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### *class* cutan.carve.generate.ArtSpec(name, prompt, size='1536x1024', background='opaque', key=None, fit=None, model=None, quality=None, prop=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

One image to generate. `key`: a [`KEYS`](#cutan.carve.generate.KEYS) name or a matte recipe.

#### prop *: [Optional](https://docs.python.org/3/library/typing.html#typing.Optional)[[Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)]]* *= None*

the image is carved
([`cutan.carve.carve()`](cutan.carve.html.md#cutan.carve.carve), its matte the `key`, else carve’s flat-colour
default) and written as `<name>/prop.json` + `parts/` (`write_prop`),
the source in the descriptor. Keys: `PROP_KEYS`.

* **Type:**
  Make a prop, not a plate (cutan#162)

### cutan.carve.generate.DEFAULT_MODEL *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'gpt-image-2'*

The model [`AixGenerator`](#cutan.carve.generate.AixGenerator) asks for when the spec names none.

### cutan.carve.generate.DEFAULT_QUALITY *: [Optional](https://docs.python.org/3/library/typing.html#typing.Optional)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)]* *= None*

the provider’s own default quality (`"high"` is the dearest tier,
and not every model has it).

* **Type:**
  `None`

### *class* cutan.carve.generate.Generated(image, facts=dict())

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

What a generator may return instead of a bare image: the image, and facts
about making it (`model`: the model the request was resolved to, e.g. aix
substituting a configured alias; `revised_prompt`: the prompt the provider
says it actually drew), recorded in the image’s source.

### *class* cutan.carve.generate.GeneratedArt(name, path, source, size=(0, 0), kept=False, warnings=())

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

One image of the spec: its path and provenance; `kept` when it was
already there and not made again (its provenance read from the record).

#### warnings *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), ...]* *= ()*

A carved prop’s quality warnings ([`cutan.carve.CarveQuality`](cutan.carve.html.md#cutan.carve.CarveQuality)).

### cutan.carve.generate.ImageGenerator

`generator(prompt, *, size, background, quality, model) -> PIL image` (or a
[`Generated`](#cutan.carve.generate.Generated): the image and facts about making it), with
`provider`, `model` and `license` attributes for the provenance.

alias of [`Callable`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[…], `Image`]

### cutan.carve.generate.KEYS *: [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)]]* *= {'green': {'hue': [90.0, 150.0], 'matte': 'chroma', 'min_sat': 0.5, 'min_val': 0.4}, 'magenta': {'hue': [280.0, 322.0], 'matte': 'chroma', 'min_sat': 0.5, 'min_val': 0.4}}*

a hue band in degrees,
and only saturated, bright pixels in it. Magenta survives gpt-image’s
anti-aliasing as roughly (246, 3, 242), hue 301; the band is narrow and the
floors high so orchid, lavender, deep pink and violet in the subject stay.
A subject in strong purple or magenta itself is keyed: keep those colours
out of art that uses the key (or key `"green"`).

* **Type:**
  Named key colours, as the `chroma` matte’s recipe

### cutan.carve.generate.OPENAI_IMAGE_MODELS *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), ...]* *= ('gpt-image', 'dall-e')*

Bare model names (no `provider/` prefix) that LiteLLM routes to OpenAI.

### cutan.carve.generate.OPENAI_OUTPUT_LICENSE *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'openai-output-owned'*

The licence code of OpenAI’s image output, which its terms assign to the user.
`an`’s licence classes treat it as an ATTRIBUTION (reeleehq/an#728: the terms
ask that shared content say it is AI-generated), so `an credits` lists the
asset under “must be displayed” with the sentence [`AI_DISCLOSURE`](#cutan.carve.generate.AI_DISCLOSURE) fills.

### cutan.carve.generate.PROVIDER_LICENSES *: [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [str](https://docs.python.org/3/builtins/stdtypes.html#str)]* *= {'openai': 'openai-output-owned'}*

The licence code of each provider’s terms for its image output, by the
provider `aix` infers from the model. A provider not listed is recorded
with no licence: unknown, which `an credits` says aloud.

### cutan.carve.generate.PROVIDER_NAMES *: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [str](https://docs.python.org/3/builtins/stdtypes.html#str)]* *= {'openai': 'OpenAI'}*

How a provider id reads in a sentence; any other reads as written.

### cutan.carve.generate.SOURCES_FILE *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'art_sources.json'*

Where each generated image’s provenance is written, beside the images.

### cutan.carve.generate.art_source(spec, generator, facts=None, , disclosure='Images generated with {provider} {model}')

The provenance of `spec`’s image as `generator` made it; `facts` are
what the provider said about this image ([`Generated`](#cutan.carve.generate.Generated)): the model it
resolved to wins over the one asked for, and a `revised_prompt` is kept.

```pycon
>>> g = AixGenerator()
>>> s = art_source(ArtSpec(name="road", prompt="a road"), g)
>>> s.provider, s.id, s.license, s.extra["prompt"]
('openai', 'gpt-image-2', 'openai-output-owned', 'a road')
>>> s.attribution
'Images generated with OpenAI gpt-image-2'
>>> art_source(ArtSpec(name="road", prompt="a road"), g, disclosure=None).attribution is None
True
>>> s.extra["image_model"]
'gpt-image-2'
```

* **Return type:**
  `AssetSource`

### cutan.carve.generate.art_specs(spec)

The [`ArtSpec`](#cutan.carve.generate.ArtSpec) list of a spec mapping or a JSON file of one.

`key_magenta: true` (the spec shape the first production wrote) means
`key: "magenta"`.

```pycon
>>> [(s.name, s.key, s.fit) for s in art_specs(
...     {"road": {"prompt": "a road", "fit": [1280, 720]},
...      "cabin": {"prompt": "a cabin", "key_magenta": True}})]
[('road', None, (1280, 720)), ('cabin', 'magenta', None)]
```

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`ArtSpec`](#cutan.carve.generate.ArtSpec)]

### cutan.carve.generate.cover_fit(image, size)

Scale `image` to cover `size` (w, h), then centre-crop to it.

```pycon
>>> cover_fit(Image.new("RGB", (300, 100)), (100, 100)).size
(100, 100)
```

* **Return type:**
  `Image`

### cutan.carve.generate.generate_art(spec, , out_dir, generator=None, only=None, keep_raw=False, overwrite=False)

Generate, key, fit and write each image of `spec` into `out_dir`.

Each image is `<name>.png`; `art_sources.json` ([`SOURCES_FILE`](#cutan.carve.generate.SOURCES_FILE))
maps each file to its provenance (with the PNG’s sha256), merged with what
the folder holds and written after every image. `only`: the names to make
(default all). An existing `<name>.png` is kept, not paid for again,
unless `overwrite`, so a batch that failed half way is resumed by running
it again. The model’s own image is written first as `<name>.raw.png`, with
its record, and removed once the PNG and its record are written, unless
`keep_raw`: a key or fit that fails leaves the paid-for image, and the
next run keys that image instead of paying for a new one. Every file is
written whole or not at all (a prop’s files by `write_prop`, in place: a
`prop.json` a crash cut off is not taken as made, and is made again).

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`GeneratedArt`](#cutan.carve.generate.GeneratedArt)]

### cutan.carve.generate.key_backdrop(image, key)

`image` with its key colour keyed to alpha and the rim de-spilled, by
[`cutan.carve`](cutan.carve.html.md#module-cutan.carve)’s matte (`key`: a [`KEYS`](#cutan.carve.generate.KEYS) name or a matte recipe).
An alpha the image already has is kept where it is lower.

* **Return type:**
  `Image`

### cutan.carve.generate.provider_of(model)

The provider of a LiteLLM model name, by LiteLLM’s own convention (a
`provider/` prefix; OpenAI’s image models go bare), without the network
lookup LiteLLM’s resolver makes; `None` when the name does not say.

```pycon
>>> provider_of("gpt-image-2"), provider_of("gemini/imagen-4"), provider_of("flux")
('openai', 'gemini', None)
```

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]
