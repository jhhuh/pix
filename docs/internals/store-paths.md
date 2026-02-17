# Store Path Computation

A Nix store path is a string of the form:

```
/nix/store/<hash>-<name>
```

where `<hash>` is exactly 32 characters of Nix base32, encoding a 160-bit (20-byte) hash.

## Algorithm

```
                              ┌──────────┐
  content ──── sha256 ──────> │  inner   │
  (or NAR hash for source)    │  hash    │
                              │ (32 B)   │
                              └────┬─────┘
                                   │
                                   v
  ┌────────────────────────────────────────────────────┐
  │ fingerprint string:                                │
  │ "<type>:sha256:<hex(inner_hash)>:/nix/store:<name>"│
  └───────────────────────┬────────────────────────────┘
                          │
                      sha256
                          │
                          v
                    ┌──────────┐
                    │ 32 bytes │
                    └────┬─────┘
                         │
                  XOR-fold to 20 bytes
                         │
                         v
                    ┌──────────┐
                    │ 20 bytes │
                    └────┬─────┘
                         │
                  Nix base32 encode
                         │
                         v
      /nix/store/<32 chars>-<name>
```

## Type prefixes

The `<type>` in the fingerprint determines what kind of store object this path refers to.

### `text` — Text files

Used by `builtins.toFile` and `pkgs.writeText`. The inner hash is `sha256(content)`.

```
text:sha256:<hex>:/nix/store:<name>
```

With references (the text file depends on other store paths):

```
text:/nix/store/...-dep1:/nix/store/...-dep2:sha256:<hex>:/nix/store:<name>
```

References are sorted and appended with `:` separators. When there are no references, the type is just `text` — no trailing colon.

### `source` — Source paths

Used by `builtins.path`, `builtins.filterSource`, and bare path imports (`./foo`). The inner hash is the SHA-256 of the NAR serialization.

```
source:sha256:<hex>:/nix/store:<name>
```

Can also have references (self-references for paths that contain their own store path):

```
source:/nix/store/...-self:sha256:<hex>:/nix/store:<name>
```

### `output:<name>` — Derivation outputs

Used for the outputs of non-fixed-output derivations. The inner hash comes from `hashDerivationModulo`.

```
output:out:sha256:<hex>:/nix/store:<name>
```

For multi-output derivations:

```
output:lib:sha256:<hex>:/nix/store:<name>
output:dev:sha256:<hex>:/nix/store:<name>
```

### Fixed-output derivations

Fixed-output derivations (like `fetchurl`) use a two-step process:

1. Compute an intermediate descriptor: `fixed:out:<method><algo>:<hex>:`
2. Hash that descriptor: `inner_hash = sha256(descriptor)`
3. Use `output:out` as the type

**Exception:** `recursive` + `sha256` is treated as a source path directly (same as `make_source_store_path`).

## Name constraints

Store object names must:

- Not be empty
- Not start with `.`
- Contain only: `a-z A-Z 0-9 + - . _ ? =`
- Not exceed 211 characters

## Worked example

Computing the store path for `builtins.toFile "hello.txt" "hello"`:

```python
from pix.hash import sha256, compress_hash
from pix.base32 import encode

content = b"hello"

# Step 1: inner hash
inner = sha256(content)
# 2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824

# Step 2: fingerprint
fp = f"text:sha256:{inner.hex()}:/nix/store:hello.txt"
# text:sha256:2cf24dba...938b9824:/nix/store:hello.txt

# Step 3: hash the fingerprint
fp_hash = sha256(fp.encode())

# Step 4: compress
compressed = compress_hash(fp_hash, 20)

# Step 5: encode
encoded = encode(compressed)  # 32 chars

# Step 6: assemble
path = f"/nix/store/{encoded}-hello.txt"
```
