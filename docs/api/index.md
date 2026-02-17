# API Reference

pix is a pure Python library with no external dependencies. All modules use only the Python standard library.

## Modules

| Module | Purpose |
|--------|---------|
| [`pix.base32`](base32.md) | Nix base32 encode/decode |
| [`pix.hash`](hash.md) | SHA-256 digest, XOR-fold compression |
| [`pix.nar`](nar.md) | NAR archive serialization and hashing |
| [`pix.store_path`](store_path.md) | Store path computation |
| [`pix.derivation`](derivation.md) | `.drv` ATerm file parsing and serialization |
| [`pix.daemon`](daemon.md) | Nix daemon Unix socket client |

## Import patterns

```python
# Individual functions
from pix.base32 import encode, decode
from pix.hash import sha256, compress_hash
from pix.nar import nar_serialize, nar_hash
from pix.store_path import make_text_store_path, make_source_store_path
from pix.derivation import parse, serialize, Derivation
from pix.daemon import DaemonConnection

# Or import modules
from pix import base32, nar, store_path, derivation, daemon
```

## Dependency graph

The modules form a clean dependency chain:

```
daemon  (standalone — socket protocol only)
  │
main ─── store_path ─── hash
  │         │             │
  │         └── base32    │
  │                       │
  ├── nar ────────────────┘
  │
  └── derivation ─── hash
```

No circular dependencies. `daemon` is fully independent of the other modules — it speaks the wire protocol directly without needing local hash computation.
