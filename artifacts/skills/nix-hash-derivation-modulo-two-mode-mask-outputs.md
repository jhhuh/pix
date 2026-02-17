# hashDerivationModulo: Two-Mode mask_outputs Distinction

## The Problem

`hashDerivationModulo` has two calling modes that produce different hashes:

1. **`staticOutputHashes` (`mask_outputs=True`)**: Used to compute a derivation's OWN output paths. Blanks output paths in both `.outputs` AND `.env` to break the circular dependency (derivation refers to its own output paths which depend on the derivation hash).

2. **`pathDerivationModulo` (`mask_outputs=False`)**: Used to compute the hash of an INPUT derivation. Keeps filled output paths — the input's hash incorporates its known output paths.

## Why It Matters

If you always use `mask_outputs=True` (as we initially did), trivial derivations (no deps) work fine because their input hashes are empty. But derivations WITH dependencies produce wrong output paths because the dependency hashes are computed incorrectly.

## The Fix

```python
def hash_derivation_modulo(drv, drv_hashes, mask_outputs=True):
    # mask_outputs=True  → staticOutputHashes (for OWN outputs)
    # mask_outputs=False → pathDerivationModulo (for INPUT derivation hashes)
```

In the package constructor:
```python
def _collect_input_hashes(deps, drv_hashes):
    for dep in deps:
        # Recursive: input derivation hashes use mask_outputs=False
        h = hash_derivation_modulo(dep.drv, drv_hashes, mask_outputs=False)
        drv_hashes[dep.drv_path] = h
```

## How It Was Discovered

This was the hardest bug in the project. Byte-by-byte .drv comparison and SHA-256 traces didn't immediately reveal it. The fix came from reading the Nix 2.24.14 C++ source (`src/libstore/derivations.cc`, lines 798-800), where `pathDerivationModulo` explicitly passes `maskOutputs=false`.

## Key Lesson

When reimplementing a system with subtle internal state, **read the upstream source** as a last resort. The two-mode distinction is not documented anywhere and is only visible in the C++ code.
