"""Tests for Nix base32 encoding/decoding."""

import hashlib
from pix.base32 import encode, decode


# sha256("hello") = 2cf24dba...
HELLO_SHA256 = bytes.fromhex(
    "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
)
# From: echo -n "hello" | nix hash file --base32 /dev/stdin
HELLO_NIX_B32 = "094qif9n4cq4fdg459qzbhg1c6wywawwaaivx0k0x8xhbyx4vwic"


def test_encode_hello_sha256():
    assert encode(HELLO_SHA256) == HELLO_NIX_B32


def test_decode_hello_sha256():
    assert decode(HELLO_NIX_B32) == HELLO_SHA256


def test_roundtrip():
    for data in [b"", b"\x00", b"\xff", b"\x00" * 20, b"\xff" * 32, HELLO_SHA256]:
        assert decode(encode(data)) == data


def test_encode_length():
    # Nix base32 output length = ceil(n*8/5)
    for n in range(0, 40):
        data = bytes(range(n))
        expected_len = (n * 8 + 4) // 5
        assert len(encode(data)) == expected_len


def test_known_20byte():
    """20-byte hash -> 32-char nix base32 (store path hash length)."""
    data = b"\x00" * 20
    assert len(encode(data)) == 32
    assert encode(data) == "0" * 32


def test_decode_invalid_char():
    import pytest
    with pytest.raises(ValueError, match="invalid nix base32 character"):
        decode("hello!")  # '!' not in alphabet
