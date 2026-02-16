# Hex-to-ASCII Debugging for Binary Protocol Errors

## The Technique

When a binary protocol returns unexpected numeric values, convert the hex representation to ASCII. Misaligned reads often produce integers whose bytes are actually part of a string.

## Example

```
Received uint64: 0x352e38322e32
Convert to ASCII: "2.28.5"  (a Nix daemon version string)
```

This immediately reveals that the code is reading a string field as an integer — pointing to a missing `recv_string()` call before the `recv_uint64()`.

## When to Use

- Unexpected large integers from a binary protocol
- Protocol desync errors (reading the wrong type at the wrong offset)
- Debugging handshake sequences with version-gated fields

## Quick Python Check

```python
value = 0x352e38322e32
value.to_bytes(8, 'little').rstrip(b'\x00').decode('ascii', errors='replace')
# → '2.28.5'
```

## How It Was Discovered

All 5 Nix daemon tests failed with the error value `0x352e38322e32`. Converting to ASCII immediately identified it as the daemon version string being misinterpreted, leading directly to the handshake field ordering fix.
