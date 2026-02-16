# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Nix functionality implemented in Python with minimal FFI. The goal is to implement as much as possible in pure Python, only using C FFI where absolutely necessary. The C++ code in `c/` serves as a reference implementation against the Nix C API.

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

- `pix/` — Main project. Python implementation of Nix functionality, minimizing FFI usage.
- `c/` — Reference implementation using the Nix C API directly (nix_api_expr.h, nix_api_util.h, nix_api_value.h). Useful for understanding the C API behavior before reimplementing in Python.
- `flake.nix` — Nix flake providing the dev shell. Pinned to nixos-24.11, x86_64-linux only.
