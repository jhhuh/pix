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

## How this was built

This project was also an experiment in agentic coding — the entire codebase
was written by an AI agent (Claude) from internalized knowledge of Nix, with
no reference implementation to copy from. The question: how much can agentic
coding achieve without a reference project?

**What worked from pure knowledge** (correct on first write):

- Base32 encoding with Nix's custom alphabet and reversed bit extraction
- XOR-fold hash compression
- NAR wire format (uint64-LE framing, 8-byte padding, sorted entries)
- Store path fingerprinting and computation
- ATerm `.drv` parsing and serialization
- `hashDerivationModulo` for breaking circular output-path dependencies
- 23 of 28 tests passed on the first run

**What required debugging against the real system:**

- **Daemon handshake field ordering** — the version string (protocol >= 1.33)
  must be read *before* the trusted status (>= 1.35). Got this backwards.
  Caught when `0x352e38322e32` showed up in an error — that's ASCII `"2.28.5"`,
  the daemon's version string being misread as a stderr message type.
- **Trailing colon in type prefix** — `"text:"` vs `"text"` when the references
  list is empty. One character difference, completely different store path.
  Caught only by end-to-end verification against the daemon's `add_text_to_store`.

Both bugs were in protocol-level details that are implicit in Nix's C++ source
but not documented anywhere. Algorithms and data formats were easy; protocol
sequencing and delimiter edge cases were not.

## Docs

Detailed walkthroughs of each algorithm:

```bash
mkdocs serve   # http://127.0.0.1:8000
```
