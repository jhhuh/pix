# pix.daemon

Nix daemon Unix socket client. Communicates using the Nix worker protocol over `/nix/var/nix/daemon-socket/socket`.

See [Internals: Daemon Protocol](../internals/daemon-protocol.md) for protocol details.

## Classes

### `DaemonConnection`

Context manager for a connection to the Nix daemon.

```python
from pix.daemon import DaemonConnection

with DaemonConnection() as conn:
    # use conn...
    pass

# Or with a custom socket path:
with DaemonConnection("/custom/socket/path") as conn:
    pass
```

**Constructor:**

```python
DaemonConnection(socket_path: str | None = None)
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `socket_path` | `/nix/var/nix/daemon-socket/socket` | Unix socket path |

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `daemon_version` | `int` | Protocol version after handshake (e.g. `293` = 1.37) |

---

## Operations

### `is_valid_path(path: str) -> bool`

Check if a store path exists and is valid in the Nix store.

```python
with DaemonConnection() as conn:
    conn.is_valid_path("/nix/store/...-hello-2.12.2")  # True
    conn.is_valid_path("/nix/store/aaaa...-nope")       # False
```

---

### `query_valid_paths(paths: list[str], substitute: bool = False) -> set[str]`

Batch validity check. Returns the subset of paths that are valid.

```python
with DaemonConnection() as conn:
    valid = conn.query_valid_paths([
        "/nix/store/...-hello",
        "/nix/store/...-nonexistent",
    ])
    # {'/nix/store/...-hello'}
```

| Parameter | Description |
|-----------|-------------|
| `substitute` | If `True`, attempt to substitute missing paths |

---

### `query_path_info(path: str) -> PathInfo`

Query metadata for a valid store path.

**Raises:** `NixDaemonError` if the path is not valid.

```python
with DaemonConnection() as conn:
    info = conn.query_path_info("/nix/store/...-hello-2.12.2")
    info.deriver       # '/nix/store/...-hello-2.12.2.drv'
    info.nar_hash       # 'sha256:1abc...'
    info.nar_size       # 53856
    info.references     # ['/nix/store/...-glibc', ...]
    info.sigs           # ['cache.nixos.org-1:abc...']
```

---

### `add_text_to_store(name: str, content: str, references: list[str] | None = None) -> str`

Add a text string to the Nix store. Returns the store path.

Like `builtins.toFile` — creates a regular file with the given content.

```python
with DaemonConnection() as conn:
    path = conn.add_text_to_store("hello.txt", "hello world")
    # '/nix/store/qbfcv31xi1wjisxwl4b2nk1a8jqxbcf5-hello.txt'

    # With references (the text depends on another store path):
    path = conn.add_text_to_store(
        "wrapper.sh",
        "#!/bin/sh\nexec /nix/store/...-program/bin/prog",
        references=["/nix/store/...-program"]
    )
```

---

### `build_paths(paths: list[str], build_mode: int = 0) -> None`

Build one or more store paths. For derivations, use the `<drv-path>^<output>` syntax.

**Raises:** `NixDaemonError` on build failure.

```python
with DaemonConnection() as conn:
    # Build a derivation output
    conn.build_paths(["/nix/store/...-hello.drv^out"])

    # Substitute/build multiple paths
    conn.build_paths([
        "/nix/store/...-hello.drv^out",
        "/nix/store/...-world.drv^out",
    ])
```

| `build_mode` | Meaning |
|---|---|
| `0` | Normal (build or substitute) |
| `1` | Repair |
| `2` | Check |

---

## Data classes

### `PathInfo`

Returned by `query_path_info`.

```python
@dataclass
class PathInfo:
    deriver: str            # .drv path that produced this, or ""
    nar_hash: str           # NAR hash as string
    references: list[str]   # store paths this depends on
    registration_time: int  # unix timestamp
    nar_size: int           # size of NAR serialization in bytes
    sigs: list[str]         # signatures
```

## Exceptions

### `NixDaemonError`

Raised on protocol errors, invalid paths, build failures, etc.

```python
from pix.daemon import DaemonConnection, NixDaemonError

with DaemonConnection() as conn:
    try:
        conn.query_path_info("/nix/store/invalid-path")
    except NixDaemonError as e:
        print(f"Daemon error: {e}")
```
