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
pytest tests/ pixpkgs/tests/ -v               # 41 tests (28 pix + 13 pixpkgs)
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

1. `pixpkgs/drv.py` — `drv()` constructor (like `mkDerivation`): takes readable args, runs the 6-step derivation pipeline (blank outputs → hashDerivationModulo → make_output_path → fill → serialize → .drv store path). Returns a frozen `Package` dataclass with `out`, `__str__` (string interpolation context), and `override()` (like `pkg.override` in Nix).
2. `pixpkgs/package_set.py` — `PackageSet` base class with `call()`: auto-injects dependencies via `inspect.signature` + `getattr` (Python equivalent of Nix's `callPackage` pattern).
3. `pixpkgs/realize.py` — `realize()`: recursively registers `.drv` files in the store via `add_text_to_store`, then builds via `build_paths`. Handles the full dep tree.

Python idioms mapping to Nix:
- `callPackage` → `inspect.signature` + `getattr` (`PackageSet.call`)
- `override` → `dataclasses.replace` / re-call with merged kwargs
- String interpolation → `__str__` returning output path
- Lazy package attrs → `@cached_property` on PackageSet

## Key gotchas

- Type prefix has NO trailing colon when references list is empty (`text` not `text:`)
- Daemon handshake order: read nix version string (>= 1.33) BEFORE trusted status (>= 1.35)
- NAR directory entries must be sorted lexicographically
- XOR-fold is NOT truncation — every input byte contributes to every output byte
- `hashDerivationModulo` has two modes: `mask_outputs=True` (staticOutputHashes — blank own outputs to break circularity) vs `mask_outputs=False` (pathDerivationModulo — keep filled output paths for input derivation hashes)
- Nix build sandbox has no coreutils: use shell builtins (`echo`, `read`, `test`) not `cat`, `tr`, `cp`
