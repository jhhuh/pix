# pix.nar

NAR (Nix Archive) serialization and hashing.

NAR is a deterministic archive format. Unlike tar, it produces identical output for identical filesystem content regardless of timestamps, ownership, or permissions (only the executable bit is preserved).

See [Internals: NAR Format](../internals/nar-format.md) for the wire format specification.

## Functions

### `nar_serialize(path: str | Path) -> bytes`

Serialize a filesystem path (file, directory, or symlink) to NAR bytes.

```python
from pix.nar import nar_serialize

# Serialize a single file
nar = nar_serialize("/tmp/hello.txt")

# Serialize a directory (entries sorted by name)
nar = nar_serialize("/path/to/my-source")
```

**Behavior:**

- **Regular files**: Serialized with contents and executable flag
- **Symlinks**: Serialized with symlink target (not resolved)
- **Directories**: Entries sorted lexicographically by name, recursed
- **Other types**: Raises `ValueError`

### `nar_hash(path: str | Path) -> bytes`

Compute the SHA-256 hash of the NAR serialization. Returns 32 raw bytes.

This is what `nix hash path` computes.

```python
from pix.nar import nar_hash

digest = nar_hash("./my-file.txt")  # 32 bytes
digest.hex()
# 'a1b2c3d4...'
```

### `nar_hash_hex(path: str | Path) -> str`

Same as `nar_hash` but returns hex string directly.

```python
from pix.nar import nar_hash_hex

nar_hash_hex("./my-file.txt")
# 'a1b2c3d4...'
```

## Combining with other modules

NAR hashing is the first step in computing store paths for source imports:

```python
from pix.nar import nar_hash
from pix.store_path import make_source_store_path

h = nar_hash("./my-project")
path = make_source_store_path("my-project", h)
# '/nix/store/abc123...-my-project'
```
