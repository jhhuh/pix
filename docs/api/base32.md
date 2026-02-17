# pix.base32

Nix-specific base32 encoding and decoding.

!!! warning
    This is **not** RFC 4648 base32. Nix uses a different alphabet and a different bit-extraction order. See [Internals: Base32](../internals/base32.md) for the full comparison.

## Constants

### `CHARS`

```python
CHARS = "0123456789abcdfghijklmnpqrsvwxyz"
```

The 32-character Nix base32 alphabet. Notable omissions: `e`, `o`, `t`, `u`.

## Functions

### `encode(data: bytes) -> str`

Encode bytes to a Nix base32 string.

**Output length:** `ceil(n * 8 / 5)` characters for `n` input bytes.

| Input size | Output size | Used for |
|-----------|-------------|----------|
| 20 bytes | 32 chars | Store path hashes |
| 32 bytes | 52 chars | SHA-256 digests |

```python
from pix.base32 import encode

encode(b"\x00" * 20)
# '00000000000000000000000000000000'

import hashlib
digest = hashlib.sha256(b"hello").digest()
encode(digest)
# '094qif9n4cq4fdg459qzbhg1c6wywawwaaivx0k0x8xhbyx4vwic'
```

### `decode(s: str) -> bytes`

Decode a Nix base32 string back to bytes.

**Raises:** `ValueError` if the string contains characters not in the Nix base32 alphabet.

```python
from pix.base32 import decode

decode("094qif9n4cq4fdg459qzbhg1c6wywawwaaivx0k0x8xhbyx4vwic")
# b',\xf2M\xba_\xb0\xa3\x0e&\xe8;*\xc5\xb9\xe2\x9e\x1b\x16\x1e\\\x1f\xa7B^s\x043b\x93\x8b\x98$'

decode("00000000000000000000000000000000")
# b'\x00' * 20
```

### Roundtrip

Encode and decode are inverse operations:

```python
from pix.base32 import encode, decode

data = b"any bytes here"
assert decode(encode(data)) == data
```
