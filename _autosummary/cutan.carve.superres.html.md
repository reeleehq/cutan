# cutan.carve.superres

Super-resolution strategies: more pixels for a part carved from a low-resolution frame (cutan#110).

When the only copy of a frame is small (a 360p scan), a thin part such as a
sabre’s blade is 3-5 px wide. `carve(upscale=k)` mattes at `k``x and comes
back to the source's resolution, so the part stays 3-5 px wide. A \*\*super
resolution strategy** is applied to the crop *before* the matte, and the part
**keeps its resolution**: ``carve(frame, superres="realesr-animevideov3")`
returns a part 4x the source’s size whose `offset`/`scale` (`to_part`)
still map source pixels into it, so recipes, pivots and landmarks stay in the
source’s pixels.

A strategy is any callable `rgb -> rgb` that returns the `HxWx3` `uint8`
image a whole factor larger on both sides; the shipped ones are classes with a
`factor`, a `name` and a `recipe()` (what provenance records, and what
[`as_superres()`](#cutan.carve.superres.as_superres) builds the same strategy back from).

| name                   | what it does                                                                                         | needs                                                                   |
|------------------------|------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------|
| `resample`             | interpolation (no new detail): the matte’s<br/>resolution is kept instead of thrown away             | OpenCV (`cutan[carve]`)                                                 |
| `realesr-animevideov3` | Real-ESRGAN for anime/cartoon video (BSD-3), x4,<br/>in overlapping tiles: clean on flat cartoon art | `onnxruntime` (`cutan[superres]`);<br/>the 2.5 MB model is fetched once |
```pycon
>>> import numpy as np
>>> rgb = np.zeros((10, 12, 3), np.uint8); rgb[2:8, 3:9] = 200
>>> sr = as_superres({"superres": "resample", "factor": 2})
>>> sr(rgb).shape, sr.recipe()
((20, 24, 3), {'superres': 'resample', 'factor': 2, 'method': 'cubic'})
```

### Module Attributes

| [`MODELS_DIR_ENV`](#cutan.carve.superres.MODELS_DIR_ENV)   | The environment variable that moves the model cache (default `~/.cache/cutan/models`).   |
|-------------------------------------------------------------------|------------------------------------------------------------------------------------------|
| [`MODELS`](#cutan.carve.superres.MODELS)           | The models the shipped strategies know, by name.                                         |
| [`SUPERRES`](#cutan.carve.superres.SUPERRES)         | `{name: (factory, accepted settings)}`.                                                  |

### Functions

| [`as_superres`](#cutan.carve.superres.as_superres)(spec)                | A strategy from its name, its recipe, a [`SuperRes`](#cutan.carve.superres.SuperRes), or any `rgb -> rgb` callable; `None` stays `None` (no super resolution).   |
|-----------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`factor_of`](#cutan.carve.superres.factor_of)(before, after)         | The whole factor an image grew by, or a `ValueError` saying why it is not one.                                                                                                |
| [`models_dir`](#cutan.carve.superres.models_dir)()                     | Where downloaded models are kept: `$CUTAN_MODELS_DIR`, else `~/.cache/cutan/models`.                                                                                          |
| [`register_superres`](#cutan.carve.superres.register_superres)(name, factory) | Make `factory(**settings)` the strategy `name` (what its recipes replay by).                                                                                                  |

### Classes

| [`ModelFile`](#cutan.carve.superres.ModelFile)(url, sha256, factor, tile, license)    | A model file a strategy downloads once and checks by hash.                                                                  |
|---------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------|
| [`RealESRGAN`](#cutan.carve.superres.RealESRGAN)([model, path, overlap, session, ...]) | Real-ESRGAN through ONNX Runtime, run in overlapping tiles.                                                                 |
| [`Resample`](#cutan.carve.superres.Resample)([factor, method])                       | Interpolate `factor``x (``cubic`, `linear` or `lanczos`): no new detail, but the matte's resolution is what the part keeps. |
| [`SuperRes`](#cutan.carve.superres.SuperRes)()                                       | Base of the shipped strategies: a `name`, a whole `factor` and a `recipe()`.                                                |
| [`SuperResLike`](#cutan.carve.superres.SuperResLike)(\*args, \*\*kwargs)                 | Anything that super-resolves: `rgb -> rgb`, a whole factor larger.                                                          |

### cutan.carve.superres.MODELS *: [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [ModelFile](#cutan.carve.superres.ModelFile)]* *= {'realesr-animevideov3': ModelFile(url='https://huggingface.co/Tomoali/realesr-animevideov3-onnx/resolve/903f497f80951d432ca187d50d4df7ccddf822bb/animevideov3_nchw_256x256_fp32.onnx', sha256='139f166bd2b955c7d4cd31ca2616eb97dacc4365c1c315d880735ce72a0663d9', factor=4, tile=256, license='BSD-3-Clause (Real-ESRGAN, xinntao)')}*

The models the shipped strategies know, by name. A revision-pinned URL and a
hash: a model never changes under a recipe that names it.

### cutan.carve.superres.MODELS_DIR_ENV *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'CUTAN_MODELS_DIR'*

The environment variable that moves the model cache (default `~/.cache/cutan/models`).

### *class* cutan.carve.superres.ModelFile(url, sha256, factor, tile, license)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A model file a strategy downloads once and checks by hash.

#### tile *: [int](https://docs.python.org/3/builtins/functions.html#int) | [None](https://docs.python.org/3/builtins/constants.html#None)*

The fixed input size the graph was exported with (square), or `None`.

### *class* cutan.carve.superres.RealESRGAN(model='realesr-animevideov3', , path=None, overlap=16, session=None, providers=('CPUExecutionProvider',), download=True, sha256=None)

Bases: [`SuperRes`](#cutan.carve.superres.SuperRes)

Real-ESRGAN through ONNX Runtime, run in overlapping tiles.

model: a name in [`MODELS`](#cutan.carve.superres.MODELS) (its file is downloaded once into
: [`models_dir()`](#cutan.carve.superres.models_dir) and checked by hash); `path`: a local copy of that
  same file (checked by hash too; never written to the recipe)

overlap: source px each tile shares with its neighbours (each side)
session: an already-built `onnxruntime.InferenceSession` (or anything

> with its `run(names, feeds)`), instead of loading the model; the
> recipe then says the pixels came from an injected session, not the
> pinned model, and cannot be replayed

providers: ONNX Runtime’s execution providers (a GPU’s first)
download: fetch the model when it is not in the cache
sha256: the model’s hash a recipe recorded: refused unless it is the one

> [`MODELS`](#cutan.carve.superres.MODELS) pins for `model` (a replay never runs another model)

The model sees `[0, 1]` RGB in `NCHW` and returns the same 

```
``
```

factor\`\`x.
The image is mirrored at its border, so the edge tiles see context too.

#### model_file()

The model’s local file (downloading it if allowed and missing), hash-checked.

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

#### recipe()

The name, the settings and the model’s hash (what made these pixels).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### *class* cutan.carve.superres.Resample(factor=2, , method='cubic')

Bases: [`SuperRes`](#cutan.carve.superres.SuperRes)

Interpolate `factor``x (``cubic`, `linear` or `lanczos`): no new
detail, but the matte’s resolution is what the part keeps.

```pycon
>>> Resample(3)(np.zeros((4, 5, 3), np.uint8)).shape
(12, 15, 3)
```

### cutan.carve.superres.SUPERRES *: [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[..., [SuperRes](#cutan.carve.superres.SuperRes)]]* *= {'realesr-animevideov3': <function <lambda>>, 'resample': <class 'cutan.carve.superres.Resample'>}*

`{name: (factory, accepted settings)}`. A model name
is a strategy of its own (`"realesr-animevideov3"`), so a recipe stays one word.

* **Type:**
  The strategies by name

### *class* cutan.carve.superres.SuperRes

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Base of the shipped strategies: a `name`, a whole `factor` and a `recipe()`.

#### recipe()

The strategy’s name under `"superres"` and its settings, plain JSON.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### *class* cutan.carve.superres.SuperResLike(\*args, \*\*kwargs)

Bases: [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol)

Anything that super-resolves: `rgb -> rgb`, a whole factor larger.

### cutan.carve.superres.as_superres(spec)

A strategy from its name, its recipe, a [`SuperRes`](#cutan.carve.superres.SuperRes), or any `rgb -> rgb`
callable; `None` stays `None` (no super resolution).

```pycon
>>> as_superres("resample").factor, as_superres(None) is None
(2, True)
>>> as_superres("magic")
Traceback (most recent call last):
  ...
ValueError: no super-resolution strategy 'magic'; the strategies are: realesr-animevideov3, resample...
```

* **Return type:**
  [`SuperRes`](#cutan.carve.superres.SuperRes) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### cutan.carve.superres.factor_of(before, after)

The whole factor an image grew by, or a `ValueError` saying why it is not one.

```pycon
>>> factor_of((10, 12, 3), (40, 48, 3))
4
>>> factor_of((10, 12, 3), (40, 47, 3))
Traceback (most recent call last):
  ...
ValueError: a super-resolution strategy returned (40, 47, 3) for (10, 12, 3): not one whole factor on both sides
```

* **Return type:**
  [`int`](https://docs.python.org/3/builtins/functions.html#int)

### cutan.carve.superres.models_dir()

Where downloaded models are kept: `$CUTAN_MODELS_DIR`, else `~/.cache/cutan/models`.

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

### cutan.carve.superres.register_superres(name, factory)

Make `factory(**settings)` the strategy `name` (what its recipes replay by).

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)
