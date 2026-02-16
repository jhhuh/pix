"""Nix-specific base32 encoding/decoding.

Nix uses a non-standard base32 with alphabet 0123456789abcdfghijklmnpqrsvwxyz
and a custom bit-extraction order (not RFC 4648).
"""

CHARS = "0123456789abcdfghijklmnpqrsvwxyz"
_DECODE_MAP = {c: i for i, c in enumerate(CHARS)}


def encode(data: bytes) -> str:
    """Encode bytes to Nix base32."""
    n = len(data)
    out_len = (n * 8 + 4) // 5  # ceil(n*8/5)
    result = []
    for i in range(out_len - 1, -1, -1):
        b = i * 5
        j = b // 8
        k = b % 8
        c = data[j] >> k
        if j + 1 < n:
            c |= data[j + 1] << (8 - k)
        result.append(CHARS[c & 0x1F])
    return "".join(result)


def decode(s: str) -> bytes:
    """Decode Nix base32 string to bytes."""
    out_len = len(s) * 5 // 8
    result = bytearray(out_len)
    for i, ch in enumerate(reversed(s)):
        digit = _DECODE_MAP.get(ch)
        if digit is None:
            raise ValueError(f"invalid nix base32 character: {ch!r}")
        b = i * 5
        j = b // 8
        k = b % 8
        result[j] |= (digit << k) & 0xFF
        carry = digit >> (8 - k)
        if carry and j + 1 < out_len:
            result[j + 1] |= carry
    return bytes(result)
