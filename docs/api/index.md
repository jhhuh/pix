# API Reference

Each module is a self-contained, readable implementation of one Nix concept. No external dependencies — stdlib only.

## Modules

| Module | Lines | What it implements |
|--------|-------|--------------------|
| [`pix.base32`](base32.md) | ~40 | The Nix base32 encoding — custom alphabet, reversed bit extraction |
| [`pix.hash`](hash.md) | ~20 | SHA-256 wrapper + XOR-fold compression |
| [`pix.nar`](nar.md) | ~80 | NAR archive serialization (files, dirs, symlinks) |
| [`pix.store_path`](store_path.md) | ~70 | Store path fingerprinting for text, source, fixed-output, and derivation outputs |
| [`pix.derivation`](derivation.md) | ~250 | ATerm parser/serializer + `hashDerivationModulo` |
| [`pix.daemon`](daemon.md) | ~270 | Unix socket client: handshake, stderr draining, store operations |

## Dependency graph

```
daemon  (standalone — wire protocol only)

store_path ─── hash
    │            │
    └── base32   │
                 │
nar ─────────────┘

derivation ─── hash
```

No circular dependencies. `daemon` is fully independent — it speaks the binary protocol directly without needing local hash computation.

## Reading the code

The modules are designed to be read top-to-bottom. Each file starts with a docstring explaining the format or protocol, then implements it in the most straightforward way possible.

If you want to understand _why_ the algorithms work the way they do, see the [Internals](../internals/index.md) section. If you want to see _how_ they're implemented, read the source — it's all in `pix/`.
