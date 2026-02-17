# NAR Wire Format

NAR (Nix Archive) is a deterministic archive format used by Nix to serialize filesystem trees. Its key property is **reproducibility** — the same filesystem content always produces the same byte sequence, regardless of timestamps, ownership, inode numbers, or other metadata.

## Wire primitives

All data is framed using a single primitive:

### String/blob encoding

```
┌──────────────────┬────────────────────┬─────────────┐
│ uint64_le(len)   │ raw bytes (len)    │ zero padding│
│ (8 bytes)        │                    │ to 8-byte   │
│                  │                    │ boundary    │
└──────────────────┴────────────────────┴─────────────┘
```

- Length is always a **little-endian uint64** (8 bytes)
- Content follows immediately after the length
- Padding: `(8 - len % 8) % 8` zero bytes to reach 8-byte alignment
- Empty strings: length = 0, no content bytes, no padding

**Examples:**

| String | Length (hex LE) | Content | Padding | Total |
|--------|----------------|---------|---------|-------|
| `""` | `00 00 00 00 00 00 00 00` | (none) | (none) | 8 bytes |
| `"("` | `01 00 00 00 00 00 00 00` | `28` | 7 zeros | 16 bytes |
| `"type"` | `04 00 00 00 00 00 00 00` | `74 79 70 65` | 4 zeros | 16 bytes |
| `"regular"` | `07 00 00 00 00 00 00 00` | `72 65 67 75 6c 61 72` | 1 zero | 16 bytes |
| `"hello"` | `05 00 00 00 00 00 00 00` | `68 65 6c 6c 6f` | 3 zeros | 16 bytes |

Every token in NAR — keywords, names, content blobs — uses this same encoding.

## Grammar

```
nar         = str("nix-archive-1") node

node        = str("(") entry str(")")

entry       = str("type") (regular | symlink | directory)

regular     = str("regular") [str("executable") str("")]
              str("contents") str(<file-data>)

symlink     = str("symlink") str("target") str(<target-path>)

directory   = str("directory") { dir_entry }

dir_entry   = str("entry") str("(")
              str("name") str(<entry-name>)
              str("node") node
              str(")")
```

Where `str(x)` is the wire encoding described above.

## File types

### Regular file

```
str("(")
  str("type") str("regular")
  [str("executable") str("")]     ← only if executable bit is set
  str("contents") str(<data>)
str(")")
```

The executable flag is the **only** permission information preserved. Mode bits like `0644` vs `0755` are reduced to just executable-or-not.

### Symlink

```
str("(")
  str("type") str("symlink")
  str("target") str(<target>)
str(")")
```

The target is stored as-is (not resolved). Relative and absolute symlinks are both supported.

### Directory

```
str("(")
  str("type") str("directory")
  str("entry") str("(")
    str("name") str("a.txt")
    str("node") <recursive node for a.txt>
  str(")")
  str("entry") str("(")
    str("name") str("b.txt")
    str("node") <recursive node for b.txt>
  str(")")
str(")")
```

!!! warning "Entries must be sorted"
    Directory entries **must** be sorted lexicographically by name. This is critical for determinism.

## What NAR preserves

| Preserved | Not preserved |
|-----------|---------------|
| File contents | Timestamps (mtime, ctime, atime) |
| File type (regular, symlink, directory) | Ownership (uid, gid) |
| Executable bit | Permission mode (beyond +x) |
| Symlink targets | Inode numbers |
| Directory structure | Extended attributes |
| Entry names | Hard links (serialized as separate files) |

## Worked example

NAR serialization of a file containing `"hello"` (5 bytes, not executable):

```
Offset  Bytes                           Meaning
------  -----                           -------
0x00    0e 00 00 00 00 00 00 00         length of "nix-archive-1" = 14
0x08    6e 69 78 2d 61 72 63 68         "nix-arch"
0x10    69 76 65 2d 31 00 00 00         "ive-1" + 2 bytes padding
0x18    01 00 00 00 00 00 00 00         length of "(" = 1
0x20    28 00 00 00 00 00 00 00         "(" + 7 bytes padding
0x28    04 00 00 00 00 00 00 00         length of "type" = 4
0x30    74 79 70 65 00 00 00 00         "type" + 4 bytes padding
0x38    07 00 00 00 00 00 00 00         length of "regular" = 7
0x40    72 65 67 75 6c 61 72 00         "regular" + 1 byte padding
0x48    08 00 00 00 00 00 00 00         length of "contents" = 8
0x50    63 6f 6e 74 65 6e 74 73         "contents" (no padding needed)
0x58    05 00 00 00 00 00 00 00         length of content = 5
0x60    68 65 6c 6c 6f 00 00 00         "hello" + 3 bytes padding
0x68    01 00 00 00 00 00 00 00         length of ")" = 1
0x70    29 00 00 00 00 00 00 00         ")" + 7 bytes padding

Total: 120 bytes
SHA-256: 0a430879c266f8b57f4092a0f935cf3facd48bbccde5760d4748ca4051716969
```

This matches the output of `nix hash path` for a file containing `"hello"`.
