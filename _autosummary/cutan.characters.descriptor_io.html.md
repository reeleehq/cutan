# cutan.characters.descriptor_io

Read, check and write a character’s `character.json` (cutan#129).

Every edit of a character folder is the same cycle: read `character.json`,
`migrate()` it to the current schema, validate it as a
[`CharacterDescriptor`](cutan.characters.schema.html.md#cutan.characters.schema.CharacterDescriptor), change it, write it back.
It was copied about ten times; each copy decided for itself whether the document
was valid BEFORE it wrote any file, and a few did not (a part’s picture copied
beside a descriptor that then failed to validate). This is that cycle once:

- [`load_descriptor()`](#cutan.characters.descriptor_io.load_descriptor) reads and validates; [`write_descriptor()`](#cutan.characters.descriptor_io.write_descriptor) writes;
- [`save_raw()`](#cutan.characters.descriptor_io.save_raw) is the same for an edit made on the raw JSON: it validates
  the document first and writes only a valid one ([`validate_raw()`](#cutan.characters.descriptor_io.validate_raw) alone,
  for a caller that has files to write between the check and the write).

```pycon
>>> import tempfile, pathlib
>>> from cutan.characters import new_character
>>> with tempfile.TemporaryDirectory() as d:
...     char = new_character(d, name='nobody', use_dicebear=False).parent
...     desc = load_descriptor(char)
...     desc.display_name = 'Nobody'
...     write_descriptor(char, desc).name, load_descriptor(char).display_name
('character.json', 'Nobody')
```

### Module Attributes

| [`DESCRIPTOR_FILE`](#cutan.characters.descriptor_io.DESCRIPTOR_FILE)   | The descriptor's file name in a character folder.   |
|--------------------------------------------------------------------|-----------------------------------------------------|

### Functions

| [`descriptor_path`](#cutan.characters.descriptor_io.descriptor_path)(char_dir)        | Where the descriptor of the character folder `char_dir` is.                                                                  |
|-----------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------|
| [`load_descriptor`](#cutan.characters.descriptor_io.load_descriptor)(char_dir)        | The character's descriptor, migrated and validated.                                                                          |
| [`read_raw`](#cutan.characters.descriptor_io.read_raw)(char_dir)               | The descriptor as the JSON document on disk (not migrated, not validated).                                                   |
| [`save_raw`](#cutan.characters.descriptor_io.save_raw)(char_dir, raw)          | Validate `raw` (an edited document), THEN write it; return the descriptor.                                                   |
| [`validate_raw`](#cutan.characters.descriptor_io.validate_raw)(raw)                | `raw` migrated to the current schema and validated: a `CharacterDescriptor` (`pydantic.ValidationError` when it is not one). |
| [`write_descriptor`](#cutan.characters.descriptor_io.write_descriptor)(char_dir, desc) | Write `desc` as the character's `character.json`; return its path.                                                           |

### cutan.characters.descriptor_io.DESCRIPTOR_FILE *= 'character.json'*

The descriptor’s file name in a character folder.

### cutan.characters.descriptor_io.descriptor_path(char_dir)

Where the descriptor of the character folder `char_dir` is.

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

### cutan.characters.descriptor_io.load_descriptor(char_dir)

The character’s descriptor, migrated and validated.

### cutan.characters.descriptor_io.read_raw(char_dir)

The descriptor as the JSON document on disk (not migrated, not validated).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### cutan.characters.descriptor_io.save_raw(char_dir, raw)

Validate `raw` (an edited document), THEN write it; return the descriptor.
Nothing is written when it does not validate.

### cutan.characters.descriptor_io.validate_raw(raw)

`raw` migrated to the current schema and validated: a `CharacterDescriptor`
(`pydantic.ValidationError` when it is not one).

### cutan.characters.descriptor_io.write_descriptor(char_dir, desc)

Write `desc` as the character’s `character.json`; return its path.
A model changed in place is validated again first (the schema does not
validate assignments), so an invalid edit writes nothing.

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)
