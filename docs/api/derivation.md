# pix.derivation

Parse and serialize Nix `.drv` files (ATerm format), and compute derivation hashes for output path calculation.

See [Internals: Derivations](../internals/derivations.md) for the ATerm format specification.

## Data classes

### `DerivationOutput`

```python
@dataclass
class DerivationOutput:
    path: str        # output store path (empty for content-addressed)
    hash_algo: str   # "" for normal outputs, "sha256" etc. for fixed-output
    hash_value: str  # "" for normal outputs, hex hash for fixed-output
```

### `Derivation`

```python
@dataclass
class Derivation:
    outputs: dict[str, DerivationOutput]     # "out" -> DerivationOutput(...)
    input_drvs: dict[str, list[str]]         # drv_path -> ["out", ...]
    input_srcs: list[str]                    # source store paths
    platform: str                            # "x86_64-linux"
    builder: str                             # "/nix/store/...-bash/bin/bash"
    args: list[str]                          # builder arguments
    env: dict[str, str]                      # environment variables
```

## Functions

### `parse(drv_text: str) -> Derivation`

Parse an ATerm `.drv` file into a `Derivation`.

```python
from pix.derivation import parse

drv = parse(open("/nix/store/...-hello-2.12.2.drv").read())

drv.platform       # 'x86_64-linux'
drv.builder         # '/nix/store/...-bash/bin/bash'
drv.outputs.keys()  # dict_keys(['out'])
drv.env['name']     # 'hello'
```

Handles escape sequences in strings: `\\`, `\"`, `\n`, `\r`, `\t`.

---

### `serialize(drv: Derivation) -> str`

Serialize a `Derivation` back to ATerm `.drv` format.

Output is deterministic:

- Outputs sorted by name
- Input derivations sorted by path
- Input sources sorted
- Environment variables sorted by key
- Strings properly escaped

```python
from pix.derivation import parse, serialize

text = open("/nix/store/...-hello.drv").read()
drv = parse(text)
assert parse(serialize(drv)) == drv  # roundtrip
```

---

### `hash_derivation_modulo(drv: Derivation, drv_hashes: dict[str, bytes] | None = None) -> bytes`

Compute the modular hash of a derivation, used for output path computation.

**Fixed-output derivations** (single output `"out"` with `hash_algo` set):

```
sha256("fixed:out:<hash_algo>:<hash_value>:<output_path>")
```

**Regular derivations**: Creates a masked copy where output paths are blanked and input derivation paths are replaced by their modular hashes, then hashes the resulting ATerm.

```python
from pix.derivation import parse, hash_derivation_modulo

drv = parse(open("some.drv").read())

# For fixed-output:
h = hash_derivation_modulo(drv)

# For regular derivations, provide input drv hashes:
h = hash_derivation_modulo(drv, drv_hashes={
    "/nix/store/...-dep.drv": dep_hash,
})
```

!!! warning
    For regular (non-fixed-output) derivations, you must provide the modular hashes of all input derivations via the `drv_hashes` parameter. Missing hashes raise `ValueError`.

## Example: Full derivation inspection

```python
from pix.derivation import parse
import json

drv = parse(open("/nix/store/...-hello-2.12.2.drv").read())

print(f"Package: {drv.env.get('pname', drv.env.get('name', '?'))}")
print(f"Version: {drv.env.get('version', '?')}")
print(f"System:  {drv.platform}")
print(f"Builder: {drv.builder}")
print(f"Outputs: {list(drv.outputs.keys())}")
print(f"Dependencies: {len(drv.input_drvs)} derivations, {len(drv.input_srcs)} sources")
```
