# pix

Nix functionality implemented in Python with minimal FFI.

The C++ code in `c/` is a reference implementation using the [Nix C API](https://nix.dev/manual/nix/latest/c-api) directly. The Python code in `pix/` is the main project — the goal is to implement as much as possible in pure Python, only dropping into FFI where absolutely necessary.

## Setup

Requires Nix with flakes enabled.

```
nix develop
```

## Usage

```
python pix/main.py
```
