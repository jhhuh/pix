# Nix placeholder() Mechanism in Derivations

## What It Is

`builtins.placeholder "out"` returns a deterministic string that acts as a marker
for the output path during derivation construction. The actual output path isn't
known yet (it depends on `hashDerivationModulo` which depends on env contents —
circular!), so Nix uses a placeholder.

## How It Works

```
placeholder("out") = "/" + nix_base32(sha256("nix-output:out"))
                   = /1rz4g4znpzjwh1xymhjpm42vipw92pr73vdgl6xs1hycac8kf2n9
```

Implementation: `nix/src/libstore/store-api.cc` — `hashPlaceholder()`

## Critical Detail: Placeholders Survive Into .drv Files

Placeholders are **NOT** replaced during derivation construction. They remain as
literal strings in the `.drv` file. Replacement happens at **BUILD TIME** by
stdenv's `setup.sh`, which substitutes placeholder strings with actual output paths.

This means:
- `env.NIX_CFLAGS_COMPILE` in the .drv contains `/1rz4g4znpz...`, not the real path
- `env.configureFlags` with `-Dprefix=${placeholder "out"}` keeps the placeholder
- Only the output-named env vars (`out`, `dev`, `man`, etc.) get actual paths

## When It's Used

- `configureFlags` with `--prefix=` or `-Dprefix=`
- `NIX_CFLAGS_COMPILE` with path-containing defines (e.g. `-DDEFAULT_LOADABLE_BUILTINS_PATH`)
- Any env var that needs to reference `$out` at eval time rather than build time

## Python Implementation

```python
# pix/store_path.py
def placeholder(output_name: str) -> str:
    inner = sha256(f"nix-output:{output_name}".encode())
    return "/" + b32encode(inner)
```

## Gotcha: Don't Replace Placeholders in drv()

An early mistake was adding a "step 4b" to `drv()` that replaced placeholder
strings with actual output paths in all env vars. This is WRONG — the real .drv
keeps placeholder strings. Only the output-named env vars (`out`, `dev`, etc.)
get actual paths in step 4.
