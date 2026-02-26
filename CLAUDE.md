# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Educational project: explore and understand Nix internals through readable Python. Each module reimplements one Nix concept (base32, NAR, store paths, derivations, daemon protocol) in straightforward Python, verified against the real `nix` CLI.

**Priority: readability over performance.** Comments should explain *why* Nix does things a certain way, not just what the code does. When modifying code, preserve or improve the educational value.

## Development Environment

```
nix develop   # Python 3, pytest, mkdocs, Nix C headers
```

## Run & Test

```
python -m pix hash-path <path> [--base32]     # NAR hash
python -m pix store-path <path> [--name NAME] # compute store path
python -m pix drv-show <drv-path>             # parse .drv as JSON
python -m pix path-info <store-path>          # query daemon
python -m pix is-valid <store-path>           # check path validity
python -m pix add-text <name> [content]       # add text to store
python -m pix build <path>...                 # build via daemon
pytest tests/ pixpkgs/tests/ -v               # ~92 tests
mkdocs serve                                  # docs at localhost:8000
```

## Architecture

### pix — Nix internals (reading order):

1. `pix/base32.py` — Nix base32: custom alphabet, reversed bit extraction vs RFC 4648
2. `pix/hash.py` — XOR-fold compression (32→20 bytes), not truncation
3. `pix/nar.py` — NAR: deterministic archive, no timestamps/uid, only executable bit
4. `pix/store_path.py` — Fingerprint: `<type>:sha256:<hex>:/nix/store:<name>` → compress → base32
5. `pix/derivation.py` — ATerm `.drv` parser + `hashDerivationModulo` (breaks circular output-path deps)
6. `pix/daemon.py` — Unix socket protocol: magic handshake, uint64-LE framing, stderr log draining

Also: `pix/main.py` (CLI), `docs/` (MkDocs site)

### pixpkgs — nixpkgs-like package set (uses pix as dependency):

Separate subdirectory that builds on pix's low-level primitives to provide a high-level package construction API, mapping Nix patterns to Python idioms.

1. `pixpkgs/drv.py` — `drv()` constructor (raw derivation primitive): takes readable args, runs the 6-step derivation pipeline (blank outputs → hashDerivationModulo → make_output_path → fill → serialize → .drv store path). Returns a frozen `Package` dataclass with `out`, `__str__` (string interpolation context), and `override()` (like `pkg.override` in Nix).
2. `pixpkgs/fetchurl.py` — `fetchurl()`: Python equivalent of `<nix/fetchurl.nix>`. Uses `builtin:fetchurl` builder for fixed-output downloads.
3. `pixpkgs/mk_derivation.py` — `mk_derivation()`: Python equivalent of `stdenv.mkDerivation`. Wraps `drv()` with standard env vars, source-stdenv.sh/default-builder.sh pattern.
4. `pixpkgs/package_set.py` — `PackageSet` base class with `call()`: auto-injects dependencies via `inspect.signature` + `getattr` (Python equivalent of Nix's `callPackage` pattern).
5. `pixpkgs/bootstrap/` — Bootstrap chain stages (Stage0 → Stage1 → StageXgcc → ...). Hand-written package definitions in `pixpkgs/pkgs/` for key packages, hash-perfect against real nixpkgs.
6. `pixpkgs/bootstrap/closure.py` — `load_hello_closure()`: auto-builds ALL 196 derivations in `nixpkgs#hello` closure from .drv files. One `package_from_drv()` function handles all types (fetchurl, compiled, hooks, stdenvs). No per-package Python files needed for stage variants.
7. `pixpkgs/realize.py` — `realize()`: recursively registers `.drv` files in the store via `add_text_to_store`, then builds via `build_paths`. Handles the full dep tree.

Python idioms mapping to Nix:
- `callPackage` → `inspect.signature` + `getattr` (`PackageSet.call`)
- `override` → `dataclasses.replace` / re-call with merged kwargs
- String interpolation → `__str__` returning output path
- Lazy package attrs → `@cached_property` on PackageSet

## pixpkgs development rules

- **Do NOT inspect .drv files** when implementing bootstrap stages. Never use `nix derivation show` to extract env vars — implement from source understanding.
- **Read nixpkgs .nix source files** (`pkgs/stdenv/linux/default.nix` and relevant package `.nix` files) to understand the logic. The nixpkgs source is accessible at the flake input path (find with `nix eval .#inputs.nixpkgs.outPath` or browse `pkgs/` in the store).
- **The reference nixpkgs** is pinned in `flake.lock` (nixos-24.11 branch). All expected hashes are relative to this revision.
- **Use pix library for hash computation** — the repo has all machinery to compute derivation hashes from scratch (drv.py, store_path.py, hash.py). Verify by computing in Python, not by querying nix-store.
- Understand WHY each env var and dependency exists, don't mechanically copy.
- **Bootstrap closure structure**: 196 drvs in `nixpkgs#hello` closure, only 147 unique pnames. 31 packages are rebuilt across stages (bash 5x, gnu-config 6x). 58 are fetchurl sources, 13 are stdenvs, 16 are setup hooks. Don't write per-stage Python files for each rebuild — `closure.py` auto-handles all 196 from .drv files. Hand-write `pixpkgs/pkgs/*.py` only for key packages where understanding the logic matters.
- **`placeholder("out")`** survives into .drv files unchanged. Replaced at build time by setup.sh, NOT during derivation construction. See `pix/store_path.py:placeholder()`.
- **Nix null-key pattern**: `{ ${null} = "value"; }` == `{}`. Used in make-derivation.nix for conditional env vars.
- **outputs env var order**: "out" first, rest preserves Nix source order (NOT alphabetical). ATerm outputs section IS alphabetical.

## Key gotchas

- Type prefix has NO trailing colon when references list is empty (`text` not `text:`)
- Daemon handshake order: read nix version string (>= 1.33) BEFORE trusted status (>= 1.35)
- NAR directory entries must be sorted lexicographically
- XOR-fold is NOT truncation — every input byte contributes to every output byte
- `hashDerivationModulo` has two modes: `mask_outputs=True` (staticOutputHashes — blank own outputs to break circularity) vs `mask_outputs=False` (pathDerivationModulo — keep filled output paths for input derivation hashes)
- Fixed-output derivation hash (Nix 2.28+): `sha256("fixed:out:<hashAlgo>:<hashValue>:<outputPath>")` — includes the output path, not just a trailing colon
- Nix build sandbox has no coreutils: use shell builtins (`echo`, `read`, `test`) not `cat`, `tr`, `cp`
