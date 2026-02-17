# Internals

How Nix works under the hood — the formats, protocols, and algorithms that pix reimplements in Python.

These pages document the specifications that pix is built against. They're useful as standalone references for anyone working with Nix internals, not just pix users.

## Topics

| Page | What it covers |
|------|---------------|
| [Store Paths](store-paths.md) | How `/nix/store/<hash>-<name>` is computed |
| [NAR Format](nar-format.md) | The Nix Archive wire format |
| [Daemon Protocol](daemon-protocol.md) | Unix socket protocol between client and `nix-daemon` |
| [Derivations](derivations.md) | ATerm `.drv` file format and `hashDerivationModulo` |
| [Base32 Encoding](base32.md) | Nix base32 vs RFC 4648 |

## Data flow

How the pieces fit together when Nix evaluates `builtins.toFile "hello.txt" "hello world"`:

```
1. Content: "hello world" (11 bytes)

2. Inner hash: sha256("hello world")
   = b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9

3. Fingerprint: "text:sha256:b94d27b9...:/nix/store:hello.txt"

4. Fingerprint hash: sha256(fingerprint)
   = <32 bytes>

5. Compressed: XOR-fold to 20 bytes

6. Encoded: Nix base32 (32 chars)

7. Store path: /nix/store/<32 chars>-hello.txt
```

And when the content is actually stored:

```
8. NAR: serialize "hello world" as a regular file in NAR format

9. Daemon: send AddTextToStore(name="hello.txt", content="hello world")
   over Unix socket to nix-daemon

10. Daemon computes the same store path, writes NAR to store,
    registers path info in the database
```
