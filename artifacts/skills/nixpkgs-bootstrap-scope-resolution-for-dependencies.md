# Nixpkgs Bootstrap: Scope Resolution for Package Dependencies

## The Problem

When a package like bash is built with stage1's stdenv, which stage's
`updateAutotoolsGnuConfigScriptsHook` does it use? The answer is NOT obvious.

## How It Works

In nixpkgs, each bootstrap stage is an overlay scope. When bash/5.nix declares:
```nix
{ updateAutotoolsGnuConfigScriptsHook, bison, ... }:
```

These dependencies are resolved via `callPackage` from the **current scope**,
not from the stdenv's stage. The scope determines which package versions are used.

## Concrete Example: bash in stage2

bash uses:
- **stdenv**: stage1's stdenv (`w0yz7fjn...`)
- **updateAutotoolsGnuConfigScriptsHook**: stage-xgcc's hook (`9lid25cvr...`)

Even though bash is built with stage1's stdenv, its `nativeBuildInputs` references
stage-xgcc's update_autotools_hook because bash lives in the stage2 overlay scope
where `callPackage` resolves dependencies through stage-xgcc's package set.

Stage1's own update_autotools_hook (`ivs0ximaj...`) is a DIFFERENT derivation —
it was built with stage0's stdenv and stage1's gnu-config.

## Why This Matters for Hash-Perfect Derivation Construction

When building a package Python-side, the caller must pass the correct dependencies
from the right scope. A `make_bash()` function should accept `update_autotools_hook`
as a parameter, and the caller determines which stage's hook to pass:

```python
bash = make_bash(
    ...,
    update_autotools_hook=stage_xgcc.update_autotools_hook,  # NOT stage1's!
    ...
)
```

## General Rule

**The stdenv determines HOW the package is compiled (compiler, linker, hooks).**
**The scope determines WHICH dependencies are resolved (via callPackage).**

These are often from different stages in the bootstrap chain. The scope is usually
one stage ahead of the stdenv.
