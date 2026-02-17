# pix.hash

Hash utilities for Nix store path computation.

## Functions

### `sha256(data: bytes) -> bytes`

Compute SHA-256 digest. Thin wrapper around `hashlib.sha256`.

```python
from pix.hash import sha256

sha256(b"hello")
# b',\xf2M\xba_\xb0\xa3\x0e...' (32 bytes)
```

### `sha256_hex(data: bytes) -> str`

Compute SHA-256 digest as a hex string.

```python
from pix.hash import sha256_hex

sha256_hex(b"hello")
# '2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824'
```

### `compress_hash(hash_bytes: bytes, size: int) -> bytes`

XOR-fold a hash to a shorter length.

This is how Nix truncates SHA-256 (32 bytes) to 160 bits (20 bytes) for store path hashes. It is **not** simple truncation — every byte of the input contributes to the output via XOR.

**Algorithm:**

```python
result = bytearray(size)       # zero-initialized
for i, b in enumerate(hash_bytes):
    result[i % size] ^= b      # XOR each byte into position
```

**Example:**

```python
from pix.hash import compress_hash, sha256

digest = sha256(b"hello")           # 32 bytes
compressed = compress_hash(digest, 20)  # 20 bytes

# Bytes 0..19 of the digest are XOR'd with bytes 20..31
# compressed[0] = digest[0] ^ digest[20]
# compressed[1] = digest[1] ^ digest[21]
# ...
# compressed[11] = digest[11] ^ digest[31]
# compressed[12..19] = digest[12..19]  (no folding needed)
```

!!! info
    XOR-fold preserves more entropy than truncation. Every bit of the original hash affects the compressed output.
