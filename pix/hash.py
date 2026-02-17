"""Hash utilities for Nix store path computation.

See: nix/src/libutil/hash.cc — compressHash()
"""

import hashlib


def compress_hash(hash_bytes: bytes, size: int) -> bytes:
    """XOR-fold a hash to the given size.

    Nix uses this to compress SHA-256 (32 bytes) to 160 bits (20 bytes)
    for store path hashes. Unlike simple truncation, every byte of the
    input contributes to the output — bytes beyond `size` are XOR'd back
    into the earlier positions:

        result[0]  = hash[0]  ^ hash[20]
        result[1]  = hash[1]  ^ hash[21]
        ...
        result[11] = hash[11] ^ hash[31]
        result[12] = hash[12]  (no folding needed for the last 8 bytes)
        ...
        result[19] = hash[19]

    This preserves more entropy than truncation.
    """
    result = bytearray(size)
    for i, b in enumerate(hash_bytes):
        result[i % size] ^= b
    return bytes(result)


def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
