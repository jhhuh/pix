# Nix Daemon Protocol

The Nix daemon (`nix-daemon`) listens on a Unix domain socket and serves store operations to clients. pix implements a client for this protocol in pure Python.

## Connection

**Socket path:** `/nix/var/nix/daemon-socket/socket`

The socket is a `SOCK_STREAM` Unix domain socket. Each client gets a dedicated connection with sequential request/response exchanges.

## Wire format

All values on the wire use little-endian encoding, padded to 8-byte boundaries:

| Type | Encoding |
|------|----------|
| `uint64` | 8 bytes, little-endian |
| `bool` | uint64 (0 = false, nonzero = true) |
| `string` | uint64(length) + bytes + zero-pad to 8 |
| `string list` | uint64(count) + count × string |

This is the same string encoding used in the [NAR format](nar-format.md).

## Handshake

```
Client                                          Daemon
  │                                               │
  ├─── uint64(WORKER_MAGIC_1 = 0x6e697863) ─────>│
  │                                               │
  │<── uint64(WORKER_MAGIC_2 = 0x6478696f) ──────┤
  │<── uint64(daemon_protocol_version) ───────────┤
  │                                               │
  ├─── uint64(client_protocol_version) ──────────>│
  ├─── uint64(0)  [cpu affinity, obsolete] ──────>│
  ├─── uint64(0)  [reserve space, obsolete] ─────>│
  │                                               │
  │<── string(nix_version)  [if proto >= 1.33] ──┤
  │<── uint64(trusted)      [if proto >= 1.35] ──┤
  │                                               │
  │<── STDERR_LAST ──────────────────────────────┤
  │                                               │
```

**Magic numbers:**

| Constant | Value | ASCII |
|----------|-------|-------|
| `WORKER_MAGIC_1` | `0x6e697863` | `nixc` |
| `WORKER_MAGIC_2` | `0x6478696f` | `dxio` |

**Protocol version** is encoded as `(major << 8) | minor`. pix uses version `1.37` = `0x0125` = `293`.

**Trusted status** (protocol >= 1.35):

| Value | Meaning |
|-------|---------|
| 0 | Unknown |
| 1 | Trusted |
| 2 | Not trusted |

## Request/response pattern

After the handshake, each operation follows this pattern:

```
Client                                          Daemon
  │                                               │
  ├─── uint64(opcode) ──────────────────────────>│
  ├─── <operation-specific data> ───────────────>│
  │                                               │
  │<── stderr messages ──────────────────────────┤
  │<── STDERR_LAST ──────────────────────────────┤
  │<── <operation-specific response> ────────────┤
  │                                               │
```

## Stderr message stream

Between request and response, the daemon sends a stream of log messages. The client must drain these before reading the response.

Each message starts with a uint64 message type:

| Type | Value | Content |
|------|-------|---------|
| `STDERR_LAST` | `0x616c7473` | End of stream — read the response next |
| `STDERR_NEXT` | `0x6f6c6d67` | Log line: `string(message)` |
| `STDERR_ERROR` | `0x63787470` | Error: `string(type) uint64(level) string(name) string(msg) uint64(n_traces) {uint64(pos) string(trace)}*` |
| `STDERR_START_ACTIVITY` | `0x53545254` | Activity started: `uint64(id) uint64(level) uint64(type) string(text) fields uint64(parent)` |
| `STDERR_STOP_ACTIVITY` | `0x53544f50` | Activity stopped: `uint64(id)` |
| `STDERR_RESULT` | `0x52534c54` | Activity result: `uint64(id) uint64(type) fields` |

**Fields** (used by activity messages):

```
uint64(count)
{
  uint64(type)     0 = uint64 value, 1 = string value
  <value>
}*
```

!!! warning "Always drain stderr"
    You **must** read all stderr messages until `STDERR_LAST` before reading the operation response. Failing to do so will desynchronize the protocol.

## Operations

### `IsValidPath` (opcode 1)

Check if a store path is valid.

```
Request:  string(path)
Response: bool(valid)
```

### `AddTextToStore` (opcode 8)

Add a text file to the store.

```
Request:  string(name) string(content) string_list(references)
Response: string(store_path)
```

### `BuildPaths` (opcode 9)

Build one or more paths.

```
Request:  string_list(paths) uint64(build_mode)
Response: uint64(result)
```

Build modes: 0 = normal, 1 = repair, 2 = check.

Paths can be opaque store paths or `<drv-path>^<output>` for derivation outputs.

### `QueryPathInfo` (opcode 26)

Query metadata for a store path.

```
Request:  string(path)
Response: bool(valid)
          [if valid:]
          string(deriver)
          string(nar_hash)
          string_list(references)
          uint64(registration_time)
          uint64(nar_size)
          bool(ultimate)
          string_list(sigs)
          string(content_address)
```

### `QueryValidPaths` (opcode 31)

Batch validity check.

```
Request:  string_list(paths) bool(substitute)
Response: string_list(valid_paths)
```

## Protocol version history

| Version | Changes |
|---------|---------|
| 1.11 | Reserve space flag in handshake |
| 1.14 | CPU affinity in handshake |
| 1.16 | `ultimate` flag in path info |
| 1.17 | `QueryPathInfo` returns validity bool instead of throwing |
| 1.25 | Content address field in path info |
| 1.30 | DerivedPath serialization for `BuildPaths` |
| 1.33 | Daemon sends nix version string after handshake |
| 1.35 | Daemon sends trusted status after handshake |
| 1.37 | Current version used by pix |
