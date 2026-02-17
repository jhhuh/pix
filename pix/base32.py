"""Nix base32 encoding/decoding.

Nix uses a non-standard base32. Two differences from RFC 4648:

1. Alphabet: "0123456789abcdfghijklmnpqrsvwxyz" — 32 chars,
   omitting e, o, t, u (historically to avoid confusion with
   similar-looking characters).

2. Bit order: RFC 4648 extracts 5-bit groups left-to-right from the
   MSB. Nix extracts them from the *last* 5-bit position down to the
   first, effectively reversing the output. This means the same bytes
   produce completely different encodings, even ignoring the alphabet.

   See: nix/src/libutil/hash.cc — printHash32()

Output length: ceil(n*8/5) characters for n input bytes.
  20 bytes (store path hash) → 32 chars
  32 bytes (SHA-256 digest)  → 52 chars
"""

CHARS = "0123456789abcdfghijklmnpqrsvwxyz"
_DECODE_MAP = {c: i for i, c in enumerate(CHARS)}


def encode(data: bytes) -> str:
    """Encode bytes to Nix base32.

    Iterates from the highest 5-bit position down to 0. At each position i,
    extracts 5 bits starting at bit offset i*5, which may span two adjacent
    input bytes. This reversed iteration is what makes Nix base32 different
    from standard base32.
    """
    n = len(data)
    out_len = (n * 8 + 4) // 5  # ceil(n*8/5)
    result = []
    for i in range(out_len - 1, -1, -1):
        b = i * 5
        j = b // 8    # which input byte
        k = b % 8     # bit offset within that byte
        c = data[j] >> k
        if j + 1 < n:
            c |= data[j + 1] << (8 - k)  # grab remaining bits from next byte
        result.append(CHARS[c & 0x1F])
    return "".join(result)


def decode(s: str) -> bytes:
    """Decode Nix base32 string to bytes. Reverses the encode process."""
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
