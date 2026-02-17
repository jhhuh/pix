# pix

Pure Python implementation of Nix store operations. No FFI — data formats
(base32, NAR, .drv, store paths) are computed natively, and store operations
talk to the Nix daemon over its Unix socket.

The C++ code in `c/` is a reference implementation using the
[Nix C API](https://nix.dev/manual/nix/latest/c-api) directly.

## Setup

Requires Nix with flakes enabled.

```
nix develop
```

This provides Python 3, pytest, and the Nix C headers (for the `c/` reference).

## CLI

Run via `python -m pix <command>`:

```
python -m pix hash-path <path> [--base32]     # NAR hash of a path
python -m pix hash-file <path> [--base32]     # flat SHA-256 of a file
python -m pix store-path <path> [--name NAME] # compute store path for a local path
python -m pix drv-show <drv-path>             # parse .drv file, print as JSON
python -m pix path-info <store-path>          # query path info from daemon
python -m pix is-valid <store-path>           # check if a store path is valid
python -m pix add-text <name> [content]       # add text to the store (- for stdin)
python -m pix build <path>...                 # build store paths via daemon
```

### Examples

```
$ python -m pix hash-path ./pix/base32.py --base32
sha256:1l1a9cfyhln3s40sb9b2w2h4z8p3566xkbs84vk819h3107ahkvl

$ python -m pix store-path ./mydir --name my-source
/nix/store/pagr3c3r57k8h9zqhb89cqihhc9sbz03-my-source

$ python -m pix add-text hello.txt "hello world"
/nix/store/qbfcv31xi1wjisxwl4b2nk1a8jqxbcf5-hello.txt

$ python -m pix drv-show /nix/store/...-hello-2.12.2.drv
{
  "outputs": {"out": {"path": "/nix/store/...", "hashAlgo": "", "hash": ""}},
  "inputDrvs": {...},
  ...
}
```

## Tests

```
pytest tests/ -v
```

All tests run offline except `tests/test_daemon.py`, which requires a running
Nix daemon and is automatically skipped if the daemon socket is unavailable.

## Architecture

```
pix/
  __init__.py
  __main__.py         # python -m pix entry point
  main.py             # CLI (argparse subcommands)
  base32.py           # Nix base32 encode/decode
  hash.py             # SHA-256 helpers, XOR-fold compression
  nar.py              # NAR serialization + hashing
  store_path.py       # Store path computation
  derivation.py       # .drv ATerm parse/serialize
  daemon.py           # Nix daemon Unix socket client
tests/
  test_base32.py
  test_nar.py
  test_store_path.py
  test_derivation.py
  test_daemon.py
c/
  main.cc             # C++ reference (Nix C API)
  Makefile
```

### Module details

#### `base32` — Nix base32

Nix uses a non-standard base32 encoding. It differs from RFC 4648 in both
the alphabet and the bit extraction order.

- **Alphabet**: `0123456789abcdfghijklmnpqrsvwxyz` (32 chars; omits `e`, `o`, `t`, `u`)
- **Bit order**: 5-bit chunks are extracted from high positions first, producing
  a different encoding than standard base32 even with the same alphabet
- **Output length**: `ceil(n * 8 / 5)` characters for `n` input bytes
  (20 bytes -> 32 chars, 32 bytes -> 52 chars)

```python
from pix.base32 import encode, decode

encode(b"\x00" * 20)             # "00000000000000000000000000000000" (32 chars)
decode("094qif9n4cq4fdg459q...")  # bytes (SHA-256 digest)
```

#### `hash` — Hash utilities

- **`sha256(data) -> bytes`** — SHA-256 digest
- **`compress_hash(hash_bytes, size) -> bytes`** — XOR-fold a hash to a
  shorter length. Nix uses this to compress SHA-256 (32 bytes) down to
  160 bits (20 bytes) for store path hashes. This is XOR folding, not
  truncation: `result[i % size] ^= hash_bytes[i]`

```python
from pix.hash import compress_hash, sha256

digest = sha256(b"hello")                # 32 bytes
compressed = compress_hash(digest, 20)   # 20 bytes (for store path)
```

#### `nar` — NAR archive format

Serialize a filesystem tree into the Nix Archive (NAR) format. NAR is a
deterministic archive format — unlike tar, it produces identical output for
identical filesystem content regardless of timestamps or metadata.

Wire format:
- Every string/blob is serialized as: `uint64_le(length) || data || zero_pad_to_8`
- Header: the string `"nix-archive-1"`
- Regular file: `( type regular [executable ""] contents <data> )`
- Symlink: `( type symlink target <path> )`
- Directory: `( type directory {entry ( name <n> node <obj> )}* )`
  - Directory entries are sorted lexicographically by name
  - Only the executable permission bit is preserved (not mode, owner, timestamps)

```python
from pix.nar import nar_serialize, nar_hash

nar_bytes = nar_serialize("/path/to/file-or-dir")
digest = nar_hash("/path/to/file-or-dir")  # SHA-256 of NAR bytes
```

#### `store_path` — Store path computation

A Nix store path is `/nix/store/<hash>-<name>` where `<hash>` is 32
characters of Nix base32 encoding a 160-bit (20-byte) hash.

The hash is computed as:

```
fingerprint = "<type>:sha256:<hex(inner_hash)>:/nix/store:<name>"
path_hash   = compress_hash(sha256(fingerprint), 20)
store_path  = "/nix/store/" + nix_base32(path_hash) + "-" + name
```

The `<type>` prefix determines the kind of store object:

| Type | Fingerprint prefix | Used for |
|------|-------------------|----------|
| Text | `text` | `builtins.toFile`, `writeText` |
| Source | `source` | `path` imports, `filterSource` |
| Output | `output:<name>` | Derivation outputs |
| Fixed output | via intermediate hash | Fixed-output derivations (fetchurl) |

References (other store paths this object depends on) are appended to the
type prefix with `:` separators.

```python
from pix.store_path import make_text_store_path, make_source_store_path

# Text file (like builtins.toFile)
path = make_text_store_path("hello.txt", b"hello world")
# -> /nix/store/qbfcv31xi1wjisxwl4b2nk1a8jqxbcf5-hello.txt

# Source directory (like a path import)
from pix.nar import nar_hash
h = nar_hash("./my-source")
path = make_source_store_path("my-source", h)
```

#### `derivation` — ATerm .drv files

Parse and serialize Nix derivation files. Derivations are stored in the Nix
store as `.drv` files in ATerm format:

```
Derive(
  [("out","/nix/store/...-hello","",""), ...],   # outputs
  [("/nix/store/...-dep.drv",["out"]), ...],     # input derivations
  ["/nix/store/...-source", ...],                # input sources
  "x86_64-linux",                                # platform
  "/nix/store/...-bash/bin/bash",                # builder
  ["--", "-e", "..."],                           # args
  [("key","value"), ...]                         # environment
)
```

The `Derivation` dataclass:

```python
@dataclass
class Derivation:
    outputs: dict[str, DerivationOutput]       # name -> (path, hash_algo, hash_value)
    input_drvs: dict[str, list[str]]           # drv_path -> [output_names]
    input_srcs: list[str]                      # source store paths
    platform: str                              # e.g. "x86_64-linux"
    builder: str                               # e.g. "/nix/store/...-bash/bin/bash"
    args: list[str]                            # builder arguments
    env: dict[str, str]                        # environment variables
```

Functions:

- **`parse(drv_text) -> Derivation`** — Parse ATerm `.drv` text
- **`serialize(drv) -> str`** — Serialize back to ATerm (sorted keys, escaped strings)
- **`hash_derivation_modulo(drv, drv_hashes) -> bytes`** — Compute the
  modular hash used for output path computation. Fixed-output derivations
  hash to `sha256("fixed:out:<algo>:<hash>:")`. Regular derivations mask
  output paths and replace input `.drv` paths with their modular hashes,
  then hash the resulting ATerm.

```python
from pix.derivation import parse, serialize, hash_derivation_modulo

drv = parse(open("/nix/store/...-hello.drv").read())
print(drv.platform)    # "x86_64-linux"
print(drv.builder)     # "/nix/store/...-bash/bin/bash"

text = serialize(drv)  # roundtrip back to ATerm
```

#### `daemon` — Nix daemon client

Communicates with the Nix daemon over its Unix socket using the worker
protocol. All values on the wire are little-endian uint64; strings are
length-prefixed and padded to 8-byte boundaries.

Connection lifecycle:

1. Connect to `/nix/var/nix/daemon-socket/socket`
2. Handshake: exchange magic numbers (`0x6e697863` / `0x6478696f`) and
   protocol versions
3. Send operations, drain stderr log messages between each request/response

Available operations:

| Method | Description |
|--------|-------------|
| `is_valid_path(path)` | Check if a store path exists and is valid |
| `query_valid_paths(paths)` | Batch validity check, returns set of valid paths |
| `query_path_info(path)` | Get deriver, NAR hash, references, size, signatures |
| `add_text_to_store(name, content)` | Add a text file to the store, returns store path |
| `build_paths(paths)` | Build derivations or substitute paths |

```python
from pix.daemon import DaemonConnection

with DaemonConnection() as conn:
    # Add content to store
    path = conn.add_text_to_store("greeting.txt", "hello")
    print(path)  # /nix/store/...-greeting.txt

    # Query it back
    assert conn.is_valid_path(path)
    info = conn.query_path_info(path)
    print(info.nar_size)       # 128
    print(info.references)     # []

    # Build a derivation
    conn.build_paths(["/nix/store/...-hello.drv^out"])
```

## How Nix store paths work

A condensed explanation of the path computation that pix implements:

```
                            +-----------+
  content ------sha256----> | inner     |
  (or NAR hash)             | hash      |
                            +-----+-----+
                                  |
                                  v
  "<type>:sha256:<hex>:/nix/store:<name>"    (fingerprint string)
                                  |
                              sha256
                                  |
                                  v
                          +-------+-------+
                          | 32-byte hash  |
                          +-------+-------+
                                  |
                          XOR-fold to 20 bytes
                                  |
                                  v
                          +-------+-------+
                          | 20-byte hash  |
                          +-------+-------+
                                  |
                          Nix base32 encode
                                  |
                                  v
            /nix/store/<32 chars>-<name>
```

## Nix version compatibility

Tested against:
- Nix 2.28.5 (daemon protocol 1.37)
- NixOS 24.11 (nixpkgs)

The daemon client negotiates protocol version 1.37 and handles the version
string and trusted-status fields added in protocol 1.33 and 1.35.
