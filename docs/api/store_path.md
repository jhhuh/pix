# pix.store_path

Compute Nix store paths. A store path is `/nix/store/<hash>-<name>` where `<hash>` is 32 characters of Nix base32 encoding a 160-bit hash.

See [Internals: Store Paths](../internals/store-paths.md) for the full algorithm.

## Constants

### `STORE_DIR`

```python
STORE_DIR = "/nix/store"
```

### `HASH_BYTES`

```python
HASH_BYTES = 20  # 160 bits
```

## Functions

### `make_store_path(type_prefix: str, inner_hash: bytes, name: str) -> str`

Low-level store path computation. Most callers should use the typed helpers below.

Computes the fingerprint `<type>:sha256:<hex>:/nix/store:<name>`, hashes it with SHA-256, XOR-folds to 20 bytes, and encodes in Nix base32.

```python
from pix.store_path import make_store_path
from pix.hash import sha256

h = sha256(b"some content")
path = make_store_path("text", h, "example.txt")
```

---

### `make_text_store_path(name: str, content: bytes, references: list[str] | None = None) -> str`

Store path for a text file. Equivalent to `builtins.toFile` or `pkgs.writeText`.

The inner hash is `sha256(content)`. The type prefix is `text` with references appended.

```python
from pix.store_path import make_text_store_path

# Simple text file
path = make_text_store_path("hello.txt", b"hello world")
# '/nix/store/qbfcv31xi1wjisxwl4b2nk1a8jqxbcf5-hello.txt'

# Text file that references another store path
path = make_text_store_path(
    "script.sh",
    b"#!/bin/sh\nexec /nix/store/...-bash/bin/bash",
    references=["/nix/store/...-bash"]
)
```

---

### `make_source_store_path(name: str, nar_hash: bytes, references: list[str] | None = None) -> str`

Store path for a source directory or file. This is what happens when you use `builtins.path`, `filterSource`, or a bare path import in Nix.

The inner hash is the SHA-256 of the NAR serialization.

```python
from pix.store_path import make_source_store_path
from pix.nar import nar_hash

h = nar_hash("./my-project")
path = make_source_store_path("my-project", h)
```

---

### `make_fixed_output_path(name: str, hash_algo: str, content_hash: bytes, recursive: bool = False) -> str`

Store path for a fixed-output derivation result (like `fetchurl`, `fetchgit`).

```python
from pix.store_path import make_fixed_output_path

# Flat file (fetchurl with sha256)
path = make_fixed_output_path("source.tar.gz", "sha256", hash_bytes)

# Recursive (fetchgit, fetchFromGitHub)
path = make_fixed_output_path("source", "sha256", nar_hash_bytes, recursive=True)
```

!!! note
    For `recursive=True` with `sha256`, the path is computed as a source path directly (same as `make_source_store_path`). For other combinations, an intermediate hash is computed first.

---

### `make_output_path(drv_hash: bytes, output_name: str, name: str) -> str`

Store path for a derivation output, given the derivation's modular hash (from `hash_derivation_modulo`).

```python
from pix.store_path import make_output_path

path = make_output_path(drv_hash, "out", "hello-2.12.2")
```
