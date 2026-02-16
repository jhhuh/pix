# pix

Exploring the [Nix C API](https://nix.dev/manual/nix/latest/c-api) from C++ and Python.

## Setup

Requires Nix with flakes enabled.

```
nix develop
```

## Usage

### C++

```
cd c
make
./main
```

### Python

```
python pix/main.py
```

Both programs open a Nix store, evaluate `builtins.nixVersion`, and print the result.
