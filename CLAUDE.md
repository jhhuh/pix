# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Experimental project exploring the Nix C API from both C++ and Python. Both implementations evaluate Nix expressions (e.g., `builtins.nixVersion`) via the libexpr C bindings.

## Development Environment

Enter the dev shell (provides pkg-config, Python 3 with ipython/pkgconfig, and Nix C headers):
```
nix develop
```

## Build & Run

**C++ (`c/`):**
```
cd c && make        # builds main from main.cc
./main              # runs the Nix expression evaluator
make clean          # removes the binary
```
Links against: `-lnixstorec -lnixutilc -lnixexprc`

**Python (`pix/`):**
```
python pix/main.py
```
Uses ctypes to load `libnixexprc.so` (located via `pkgconfig`).

## Architecture

- `c/main.cc` — C++ implementation using the Nix C API directly (nix_api_expr.h, nix_api_util.h, nix_api_value.h). Opens a Nix store, creates an eval state, evaluates a string expression, and prints the result.
- `pix/main.py` — Python equivalent using ctypes FFI against the same Nix C libraries. Mirrors the C++ flow but is less complete (no cleanup/free calls yet).
- `flake.nix` — Nix flake providing the dev shell. Pinned to nixos-24.11, x86_64-linux only.
