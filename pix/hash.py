"""Hash utilities for Nix store path computation."""

import hashlib


def compress_hash(hash_bytes: bytes, size: int) -> bytes:
    """XOR-fold a hash to the given size."""
    result = bytearray(size)
    for i, b in enumerate(hash_bytes):
        result[i % size] ^= b
    return bytes(result)


def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
