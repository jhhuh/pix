# Nix Base32 Encoding

Nix uses a custom base32 encoding that differs from both RFC 4648 and other common base32 variants.

## Alphabet

```
Standard (RFC 4648):  A B C D E F G H I J K L M N O P Q R S T U V W X Y Z 2 3 4 5 6 7
Nix:                  0 1 2 3 4 5 6 7 8 9 a b c d f g h i j k l m n p q r s v w x y z
```

The Nix alphabet has 32 characters: digits `0-9` and lowercase letters, but with `e`, `o`, `t`, `u` removed.

Why these four? They could be confused with other characters (`e`/`3`, `o`/`0`, `t`/`+`), though the exact rationale is historical.

## Bit extraction

This is where Nix base32 differs most significantly from RFC 4648. The bit extraction order is reversed.

### RFC 4648 approach

Standard base32 processes input left-to-right, taking 5-bit groups from the most significant bits first:

```
Input bytes:   [b0] [b1] [b2] ...
Bits:          76543210 76543210 76543210 ...
Groups:        |4444433333|22222|11111|00000|...
```

### Nix approach

Nix processes from the **last** 5-bit position down to the first, extracting bits across byte boundaries:

```python
for i in range(out_len - 1, -1, -1):   # high positions first
    b = i * 5
    j = b // 8                          # byte index
    k = b % 8                           # bit offset within byte
    c = (data[j] >> k)                  # bits from byte j
    if j + 1 < len(data):
        c |= data[j + 1] << (8 - k)    # bits from byte j+1
    output.append(CHARS[c & 0x1f])
```

This means:

- The **first** output character encodes the **highest** 5-bit group
- Bits are extracted from the input in little-endian byte order
- Cross-byte extraction: a 5-bit group can span two adjacent input bytes

### Consequence

The same input bytes produce completely different outputs between RFC 4648 and Nix base32, even if you swap the alphabets. The encoding is structurally different, not just an alphabet substitution.

## Output length

For `n` input bytes, the output is `ceil(n * 8 / 5)` characters:

| Input bytes | Output chars | Usage |
|------------|-------------|-------|
| 0 | 0 | — |
| 16 | 26 | MD5 (not used by Nix) |
| 20 | 32 | Store path hashes |
| 32 | 52 | SHA-256 hashes |
| 64 | 103 | SHA-512 hashes |

## Decoding

Decoding reverses the process: iterate over the input string in reverse, placing 5-bit groups into the output byte array at the appropriate positions.

```python
for i, ch in enumerate(reversed(s)):
    digit = ALPHABET.index(ch)
    b = i * 5
    j = b // 8
    k = b % 8
    result[j] |= (digit << k) & 0xFF
    carry = digit >> (8 - k)
    if carry and j + 1 < out_len:
        result[j + 1] |= carry
```

## Comparison table

| Property | RFC 4648 | Nix |
|----------|----------|-----|
| Alphabet | `A-Z2-7` | `0-9a-z` minus `eotu` |
| Padding | `=` pad to multiple of 8 chars | No padding |
| Bit order | MSB-first, left-to-right | LSB-first, right-to-left |
| Case | Case-insensitive | Lowercase only |
| Byte order | Big-endian grouping | Little-endian grouping |

## Example

SHA-256 of `"hello"`:

```
Hex:        2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824
Nix base32: 094qif9n4cq4fdg459qzbhg1c6wywawwaaivx0k0x8xhbyx4vwic
```

The same bytes in RFC 4648 base32 would produce a completely different (and longer, with padding) string.
