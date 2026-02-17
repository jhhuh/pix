# CLI Reference

Run pix as a Python module:

```bash
python -m pix <command> [options]
```

## Commands

### `hash-path` — NAR hash of a path

Compute the SHA-256 hash of the NAR serialization of a file or directory. Equivalent to `nix hash path`.

```bash
python -m pix hash-path <path> [--base32]
```

| Flag | Description |
|------|-------------|
| `--base32` | Output in Nix base32 instead of hex |

**Examples:**

```bash
$ python -m pix hash-path ./pix/base32.py
sha256:0a43087...

$ python -m pix hash-path ./pix/base32.py --base32
sha256:1l1a9cfyhln3s40sb9b2w2h4z8p3566xkbs84vk819h3107ahkvl

$ python -m pix hash-path ./my-directory --base32
sha256:1vrbglcwc4gpln263rg69jq6vgq8p3ibspdg7lzyxcyc0ryg5wn2
```

!!! note
    `hash-path` hashes the **NAR serialization**, not the raw file bytes. This includes file type metadata and, for directories, sorted entry names. Use `hash-file` for raw content hashing.

---

### `hash-file` — Flat SHA-256 of a file

Hash the raw bytes of a file (no NAR wrapping). Equivalent to `nix hash file`.

```bash
python -m pix hash-file <path> [--base32]
```

**Examples:**

```bash
$ echo -n "hello" > /tmp/hello.txt
$ python -m pix hash-file /tmp/hello.txt --base32
sha256:094qif9n4cq4fdg459qzbhg1c6wywawwaaivx0k0x8xhbyx4vwic
```

---

### `store-path` — Compute store path

Compute the Nix store path for a local file or directory, as if it were added via `builtins.path` or `filterSource`.

```bash
python -m pix store-path <path> [--name NAME]
```

| Flag | Description |
|------|-------------|
| `--name` | Override the store object name (default: basename of path) |

**Examples:**

```bash
$ python -m pix store-path ./my-source
/nix/store/pagr3c3r57k8h9zqhb89cqihhc9sbz03-my-source

$ python -m pix store-path ./my-source --name custom-name
/nix/store/abc123...-custom-name
```

---

### `drv-show` — Parse `.drv` as JSON

Parse a `.drv` file from the Nix store and display it as formatted JSON. Equivalent to `nix derivation show`.

```bash
python -m pix drv-show <drv-path>
```

**Example:**

```bash
$ python -m pix drv-show /nix/store/...-hello-2.12.2.drv
{
  "outputs": {
    "out": {
      "path": "/nix/store/...-hello-2.12.2",
      "hashAlgo": "",
      "hash": ""
    }
  },
  "inputDrvs": {
    "/nix/store/...-bash.drv": ["out"],
    "/nix/store/...-stdenv.drv": ["out"]
  },
  "inputSrcs": ["/nix/store/...-default-builder.sh"],
  "platform": "x86_64-linux",
  "builder": "/nix/store/...-bash/bin/bash",
  "args": ["-e", "/nix/store/...-default-builder.sh"],
  "env": {"name": "hello", "version": "2.12.2", ...}
}
```

---

### `path-info` — Query store path info

Query metadata for a store path from the Nix daemon. Requires a running daemon.

```bash
python -m pix path-info <store-path>
```

**Example:**

```bash
$ python -m pix path-info /nix/store/...-hello-2.12.2
deriver: /nix/store/...-hello-2.12.2.drv
nar-hash: sha256:1abc...
nar-size: 53856
references: /nix/store/...-glibc /nix/store/...-hello-2.12.2
sigs: cache.nixos.org-1:abc123...
```

---

### `is-valid` — Check store path validity

Check whether a store path exists and is valid. Exits 0 if valid, 1 if not.

```bash
python -m pix is-valid <store-path>
```

**Example:**

```bash
$ python -m pix is-valid /nix/store/...-hello-2.12.2
valid

$ python -m pix is-valid /nix/store/aaaa...-nonexistent
invalid
```

---

### `add-text` — Add text to the store

Add a text string to the Nix store, like `builtins.toFile`. Reads from stdin if content is `-` or omitted.

```bash
python -m pix add-text <name> [content]
```

**Examples:**

```bash
$ python -m pix add-text hello.txt "hello world"
/nix/store/qbfcv31xi1wjisxwl4b2nk1a8jqxbcf5-hello.txt

$ echo "from stdin" | python -m pix add-text piped.txt
/nix/store/...-piped.txt
```

---

### `build` — Build store paths

Build one or more derivation outputs via the Nix daemon.

```bash
python -m pix build <path>...
```

**Example:**

```bash
$ python -m pix build /nix/store/...-hello-2.12.2.drv^out
build succeeded
```
