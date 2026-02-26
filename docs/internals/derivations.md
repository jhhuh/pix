# Derivations

A derivation is Nix's unit of build. It describes how to produce one or more store paths from inputs, a builder, and environment variables. Derivations are stored in the Nix store as `.drv` files in ATerm format.

## ATerm format

A `.drv` file is a single ATerm expression:

```
Derive(
  [("out","/nix/store/...-hello","",""), ...],       # outputs
  [("/nix/store/...-dep.drv",["out"]), ...],         # input derivations
  ["/nix/store/...-source", ...],                    # input sources
  "x86_64-linux",                                    # platform
  "/nix/store/...-bash/bin/bash",                    # builder
  ["--", "-e", "..."],                               # arguments
  [("key","value"), ...]                             # environment
)
```

### Fields

| # | Field | Type | Description |
|---|-------|------|-------------|
| 1 | outputs | `[(name, path, hashAlgo, hash)]` | Output name-to-path mapping |
| 2 | inputDrvs | `[(drvPath, [outputNames])]` | Derivation dependencies |
| 3 | inputSrcs | `[path]` | Source file dependencies |
| 4 | platform | `string` | Build platform (e.g. `x86_64-linux`) |
| 5 | builder | `string` | Path to the builder executable |
| 6 | args | `[string]` | Builder command-line arguments |
| 7 | env | `[(key, value)]` | Environment variables for the builder |

### Outputs

Each output is a 4-tuple:

```
("name", "path", "hashAlgo", "hash")
```

| Field | Normal output | Fixed-output |
|-------|--------------|--------------|
| `name` | `"out"`, `"lib"`, `"dev"`, etc. | `"out"` |
| `path` | `/nix/store/...-name` | `/nix/store/...-name` |
| `hashAlgo` | `""` | `"sha256"`, `"r:sha256"`, etc. |
| `hash` | `""` | hex hash of expected content |

The `r:` prefix in `hashAlgo` means recursive (NAR hash). Without it, the hash is of the flat file content.

### String escaping

Strings in ATerm use these escape sequences:

| Escape | Character |
|--------|-----------|
| `\\` | Backslash |
| `\"` | Double quote |
| `\n` | Newline |
| `\r` | Carriage return |
| `\t` | Tab |

### Ordering

In the canonical serialization:

- Outputs are sorted by output name
- Input derivations are sorted by `.drv` path
- Input sources are sorted
- Environment variables are sorted by key
- Arguments preserve their original order

## `hashDerivationModulo`

This is the algorithm Nix uses to compute the hash that determines output paths. It exists to break circular dependencies — an output path depends on the derivation hash, but the derivation contains its own output paths.

### Fixed-output derivations

For derivations with a single output `"out"` that has a `hashAlgo` set:

```
hash = sha256("fixed:out:<hashAlgo>:<hashValue>:<outputPath>")
```

The output path is computed from the content hash via `make_fixed_output_path` and included in the fingerprint. Since the output path is itself deterministic from the content hash, this doesn't create circularity — it just makes the fingerprint more explicit. Fixed-output derivations have stable hashes that don't change when their build dependencies change — only the expected output hash matters.

### Regular derivations

For all other derivations:

1. **Optionally blank output paths**: Replace output paths with `""` in both `.outputs` and `.env` (see [two modes](#two-modes-maskoutputs) below)
2. **Replace input drv paths**: For each input derivation, replace the `.drv` path with the hex-encoded `hashDerivationModulo` of that input
3. **Serialize**: Convert the masked derivation back to ATerm
4. **Hash**: `sha256(serialized_masked_drv)`

```
┌─────────────────────────────────────────┐
│ Original .drv                           │
│                                         │
│ outputs: ("out", "/nix/store/abc-x")    │
│ inputDrvs: ("/nix/store/def.drv",["out"])│
│ ...                                     │
└──────────────────┬──────────────────────┘
                   │
            mask & replace
                   │
                   v
┌─────────────────────────────────────────┐
│ Masked .drv                             │
│                                         │
│ outputs: ("out", "")        ← blanked   │
│ inputDrvs: ("a1b2c3...",["out"]) ← hash │
│ ...                                     │
└──────────────────┬──────────────────────┘
                   │
            serialize to ATerm string
                   │
                   v
            sha256(aterm_string)
                   │
                   v
           derivation hash (32 bytes)
```

### Two modes: `maskOutputs`

`hashDerivationModulo` takes a `maskOutputs` parameter that controls whether output paths are blanked. Nix uses two different call sites:

| Call site | `maskOutputs` | Output paths | Used for |
|-----------|:------------:|:------------:|----------|
| `staticOutputHashes` | `true` | blanked (`""`) | Computing a derivation's **own** output paths |
| `pathDerivationModulo` | `false` | **kept** | Computing the hash of an **input** derivation |

This distinction matters: when derivation A depends on derivation B, Nix computes B's hash with `maskOutputs=false` — B's filled output paths are part of the hash used as A's `inputDrvs` key. Only A's own outputs are blanked (to break A's circularity).

```
Computing output path for consumer.drv:

  dep.drv (input)                consumer.drv (self)
  ─────────────                  ───────────────────
  maskOutputs = false            maskOutputs = true
  output paths KEPT              output paths BLANKED
         │                              │
         v                              v
    dep_hash (includes             consumer_hash
    dep's output path)                  │
         │                              v
         └──── used as ──────> inputDrvs key
                               in consumer's masked ATerm
```

!!! warning "Common pitfall"
    Using `maskOutputs=true` for input derivations produces the wrong hash — the input's output path is lost, changing the consumer's `inputDrvs` key and ultimately its output path. This is the difference between `staticOutputHashes` (for self) and `pathDerivationModulo` (for inputs).

### Computing output paths

Once you have the derivation hash from `hashDerivationModulo`:

```python
from pix.store_path import make_output_path

output_path = make_output_path(drv_hash, "out", "hello-2.12.2")
# /nix/store/<hash>-hello-2.12.2
```

The type prefix is `output:<output-name>`, so the fingerprint becomes:

```
output:out:sha256:<hex(drv_hash)>:/nix/store:hello-2.12.2
```

## Real-world example

A minimal derivation (`builtins.derivation { name = "hello"; builder = "/bin/sh"; args = ["-c" "echo hello > $out"]; system = "x86_64-linux"; }`):

```
Derive(
  [("out","/nix/store/...-hello","","")],
  [],
  [],
  "x86_64-linux",
  "/bin/sh",
  ["-c","echo hello > $out"],
  [("builder","/bin/sh"),
   ("name","hello"),
   ("out","/nix/store/...-hello"),
   ("system","x86_64-linux")]
)
```

Note that the environment contains both explicit env vars and automatic ones (`builder`, `out`, `system`, `name`).
