# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Pure Python implementation of Nix store operations. No FFI — data formats (base32, NAR, .drv, store paths) are computed natively, and store operations talk to the Nix daemon over its Unix socket. The C++ code in `c/` is a reference implementation against the Nix C API.

## Development Environment

Enter the dev shell (provides Python 3 with ipython/pkgconfig/pytest, pkg-config, and Nix C headers):
```
nix develop
```

## Build & Run

**Python (`pix/`):**
```
python -m pix hash-path <path> [--base32]     # NAR hash
python -m pix store-path <path> [--name NAME] # compute store path
python -m pix drv-show <drv-path>             # parse .drv as JSON
python -m pix path-info <store-path>          # query daemon
python -m pix is-valid <store-path>           # check path validity
python -m pix add-text <name> [content]       # add text to store
python -m pix build <path>...                 # build via daemon
```

**C++ reference (`c/`):**
```
cd c && make && ./main && make clean
```
Links against: `-lnixstorec -lnixutilc -lnixexprc`

## Testing

```
pytest tests/ -v
```
Daemon tests (`test_daemon.py`) auto-skip if the daemon socket is unavailable.

## Architecture

- `pix/base32.py` — Nix base32 encode/decode (custom alphabet `0123456789abcdfghijklmnpqrsvwxyz`, custom bit order)
- `pix/hash.py` — SHA-256 helpers, XOR-fold compression (32 -> 20 bytes)
- `pix/nar.py` — NAR archive serialization + hashing (uint64-le framed, 8-byte padded, sorted dirs)
- `pix/store_path.py` — Store path computation: `make_text_store_path`, `make_source_store_path`, `make_fixed_output_path`, `make_output_path`
- `pix/derivation.py` — ATerm `.drv` parser/serializer, `Derivation` dataclass, `hash_derivation_modulo`
- `pix/daemon.py` — Nix daemon Unix socket client (protocol 1.37): `is_valid_path`, `query_path_info`, `add_text_to_store`, `build_paths`
- `pix/main.py` — CLI entry point (argparse subcommands)
- `c/` — C++ reference using Nix C API directly
- `flake.nix` — Dev shell. Pinned to nixos-24.11, x86_64-linux only.

## Key implementation notes

- Store path fingerprint format: `<type>:sha256:<hex(inner_hash)>:/nix/store:<name>`
- Type prefix has NO trailing colon when references list is empty (e.g. `text` not `text:`)
- NAR preserves only executable bit, not full mode/owner/timestamps
- Daemon handshake: must read nix version string (>= 1.33) before trusted status (>= 1.35)
- All daemon wire values are uint64 little-endian; strings are length-prefixed + zero-padded to 8 bytes
