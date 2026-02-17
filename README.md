# pix

Explore Nix internals through readable Python.

Nix's core algorithms — store path hashing, NAR serialization, derivation
parsing, the daemon wire protocol — are buried in C++ across dozens of files.
pix re-derives them in ~600 lines of Python so you can read, modify, and
single-step through the logic.

Every module produces output identical to the real `nix` CLI, verified by
the test suite. The code is the documentation.

## Setup

```
nix develop
```

## Read the code

Start here, in dependency order:

| File | What you'll learn |
|------|-------------------|
| [`pix/base32.py`](pix/base32.py) | Why Nix base32 isn't RFC 4648 — different alphabet, reversed bit extraction |
| [`pix/hash.py`](pix/hash.py) | XOR-fold: how Nix compresses SHA-256 (32 B) to 160 bits (20 B) without truncating |
| [`pix/nar.py`](pix/nar.py) | NAR: Nix's deterministic archive format — no timestamps, no permissions, just content |
| [`pix/store_path.py`](pix/store_path.py) | How `/nix/store/<hash>-<name>` is actually computed from a fingerprint string |
| [`pix/derivation.py`](pix/derivation.py) | ATerm `.drv` format, and `hashDerivationModulo` — the trick that breaks circular output-path dependencies |
| [`pix/daemon.py`](pix/daemon.py) | The Unix socket protocol: magic numbers, uint64-LE framing, stderr log draining |

## Try it

```bash
# Compute the same hash as nix hash path
python -m pix hash-path ./some-file --base32

# See what store path a directory would get
python -m pix store-path ./my-source

# Parse a real .drv file into readable JSON
python -m pix drv-show /nix/store/...-hello-2.12.2.drv

# Talk to the daemon directly
python -m pix add-text hello.txt "hello world"
python -m pix path-info /nix/store/...-hello.txt
```

## Verify against Nix

```bash
pytest tests/ -v
```

The tests compare pix output against `nix hash path`, `nix path-info`, and the daemon's own store path computation.

## Docs

Detailed walkthroughs of each algorithm:

```bash
mkdocs serve   # http://127.0.0.1:8000
```
