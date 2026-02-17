# pix

**Explore Nix internals through readable Python.**

Nix's core algorithms — store path hashing, NAR serialization, derivation parsing, the daemon wire protocol — are buried in C++ across dozens of source files. pix re-derives each one in straightforward Python so you can read, modify, and single-step through the logic.

Every module produces output identical to the real `nix` CLI, verified by the test suite. The code is the documentation; these pages are the commentary.

## What's inside Nix

When you run `nix build`, a lot happens under the hood. pix breaks it into pieces you can understand one at a time:

| Concept | What Nix does | pix module | Docs |
|---------|--------------|------------|------|
| **Base32** | Custom encoding for store path hashes — not RFC 4648 | [`base32.py`](api/base32.md) | [How it differs](internals/base32.md) |
| **Hash compression** | XOR-folds SHA-256 (32 B) down to 160 bits (20 B) | [`hash.py`](api/hash.md) | [In store path computation](internals/store-paths.md) |
| **NAR** | Deterministic archive format — no timestamps, no uid, just content | [`nar.py`](api/nar.md) | [Wire format spec](internals/nar-format.md) |
| **Store paths** | `/nix/store/<hash>-<name>` computed from a fingerprint string | [`store_path.py`](api/store_path.md) | [Full algorithm](internals/store-paths.md) |
| **Derivations** | `.drv` files in ATerm format; `hashDerivationModulo` breaks circular deps | [`derivation.py`](api/derivation.md) | [Format + hashing](internals/derivations.md) |
| **Daemon protocol** | Unix socket with uint64-LE framing, stderr log stream, operation opcodes | [`daemon.py`](api/daemon.md) | [Protocol spec](internals/daemon-protocol.md) |

## pixpkgs — building on pix

Once you understand the internals, pixpkgs shows how to build a nixpkgs-like package set on top of them, mapping Nix patterns to Python idioms:

| Nix pattern | Python idiom | pixpkgs module |
|-------------|-------------|----------------|
| `mkDerivation` | `drv()` function → `Package` dataclass | [`drv.py`](api/pixpkgs.md#drv) |
| `callPackage` | `inspect.signature` + `getattr` | [`package_set.py`](api/pixpkgs.md#packageset) |
| String interpolation (`${pkg}`) | `__str__` returning output path | [`drv.py`](api/pixpkgs.md#package) |
| `pkg.override` | Re-call `drv()` with merged kwargs | [`drv.py`](api/pixpkgs.md#packageoverride) |
| `nix-store --realize` | `realize()` → daemon `add_text_to_store` + `build_paths` | [`realize.py`](api/pixpkgs.md#realize) |

See the [pixpkgs API reference](api/pixpkgs.md) for details.

## Reading order

The modules build on each other. Start from the bottom:

```
pix (Nix internals):
  1. base32.py        ← simplest: just an encoding
  2. hash.py          ← one function: XOR-fold
  3. nar.py           ← serialization format, uses hash
  4. store_path.py    ← the core algorithm, uses base32 + hash
  5. derivation.py    ← parsing + the hashDerivationModulo trick
  6. daemon.py        ← standalone: wire protocol over Unix socket

pixpkgs (package set layer, uses pix):
  7. drv.py           ← drv() + Package: the mkDerivation equivalent
  8. package_set.py   ← PackageSet.call(): the callPackage equivalent
  9. realize.py       ← write .drv to store + build via daemon
```

Each pix file is self-contained and under 150 lines. You can read the entire codebase in one sitting.

## Try it yourself

```bash
nix develop

# See that pix computes the exact same hash as nix
python -m pix hash-path ./pix/base32.py --base32
nix hash path ./pix/base32.py --type sha256 --base32
# same output

# Compute a store path, then verify via the daemon
python -m pix store-path ./pix --name pix-source
python -m pix add-text hello.txt "hello world"
python -m pix drv-show /nix/store/...-hello.drv
```

## Verify

```bash
pytest tests/ pixpkgs/tests/ -v   # 41 tests, all comparing against real nix
```

## How to use these docs

- **[Internals](internals/index.md)** — Start here. Explains _how Nix works_ with diagrams, hex dumps, and protocol traces.
- **[API Reference](api/index.md)** — Function signatures and usage examples for each module.
- **[CLI Reference](cli.md)** — The `python -m pix` commands for quick experimentation.
