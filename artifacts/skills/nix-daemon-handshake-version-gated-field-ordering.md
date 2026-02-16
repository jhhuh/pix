# Nix Daemon Handshake: Version-Gated Field Ordering

## The Protocol

The Nix daemon handshake has strict field ordering that depends on protocol version thresholds:

1. Client sends magic: `0x6e697863` ("nixc")
2. Daemon sends magic: `0x6478696f` ("dxio")
3. Daemon sends protocol version (uint64)
4. Client sends protocol version (uint64)
5. If protocol >= 1.14: client sends CPU affinity (uint64, always 0)
6. If protocol >= 1.11: client sends reserve-space (uint64, always 0)
7. **If protocol >= 1.33: daemon sends version string** (e.g., `"2.28.5"`)
8. **If protocol >= 1.35: daemon sends trusted status** (uint64)

## The Bug

Steps 7 and 8 MUST happen in this exact order. If you skip step 7 and try to read the trusted status, you'll read the version string bytes as a uint64, getting garbage like `0x352e38322e32`.

## Debugging Tip

When a binary protocol returns unexpected numeric values, **convert hex to ASCII**. The value `0x352e38322e32` decodes to `"2.28.5"` — immediately revealing that a string is being misread as an integer.

## How It Was Discovered

All 5 daemon tests failed simultaneously. The error value `0x352e38322e32` was the smoking gun — its ASCII decoding pointed directly to a misaligned read in the handshake sequence.
