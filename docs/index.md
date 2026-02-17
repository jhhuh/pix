# pix

**Pure Python implementation of Nix store operations.**

No FFI. Data formats (base32, NAR, `.drv`, store paths) are computed natively in Python. Store operations talk to the Nix daemon over its Unix socket.

## What pix does

| Capability | How |
|---|---|
| Hash files and directories | NAR serialization + SHA-256, matching `nix hash path` |
| Compute store paths | Fingerprint hashing, matching Nix exactly |
| Parse `.drv` files | ATerm parser/serializer with full roundtrip |
| Talk to the Nix daemon | Unix socket protocol client (no CLI wrapping) |
| Add content to the store | Via daemon `add_text_to_store` |
| Build derivations | Via daemon `build_paths` |

## Quick start

```bash
# Enter dev environment
nix develop

# Hash a file (same as nix hash path)
python -m pix hash-path ./myfile.txt --base32

# Compute store path for a directory
python -m pix store-path ./my-source --name my-source

# Add text to the Nix store
python -m pix add-text hello.txt "hello world"

# Query store path info from daemon
python -m pix path-info /nix/store/...-hello.txt
```

## Use as a library

```python
from pix.store_path import make_text_store_path
from pix.nar import nar_hash
from pix.daemon import DaemonConnection

# Compute a store path locally
path = make_text_store_path("greeting.txt", b"hello world")

# Or talk to the daemon
with DaemonConnection() as conn:
    path = conn.add_text_to_store("greeting.txt", "hello world")
    info = conn.query_path_info(path)
```

## Project structure

```
pix/
  base32.py           Nix base32 encode/decode
  hash.py             SHA-256, XOR-fold compression
  nar.py              NAR serialization + hashing
  store_path.py       Store path computation
  derivation.py       .drv ATerm parse/serialize
  daemon.py           Nix daemon socket client
  main.py             CLI
tests/
  test_base32.py      6 tests
  test_nar.py         6 tests
  test_store_path.py  5 tests
  test_derivation.py  6 tests
  test_daemon.py      5 tests (need running daemon)
c/
  main.cc             C++ reference (Nix C API)
```

## Requirements

- Nix with flakes enabled
- Python 3.12+
- Running Nix daemon (for `daemon.py` and daemon CLI commands)
- No pip dependencies — stdlib only
