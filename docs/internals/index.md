# Internals

How Nix actually works — the formats, protocols, and algorithms, explained through the Python code that reimplements them.

Each page pairs an explanation of the concept with pointers to the pix source that implements it. Read the page, then read the code — it should click.

## Start here

| Page | The question it answers |
|------|------------------------|
| [Store Paths](store-paths.md) | How does Nix compute `/nix/store/<hash>-<name>`? Why 32 characters? |
| [NAR Format](nar-format.md) | What's inside a NAR archive? Why not tar? |
| [Daemon Protocol](daemon-protocol.md) | How do `nix build` and `nix-store` talk to the daemon? |
| [Derivations](derivations.md) | What's in a `.drv` file? How does `hashDerivationModulo` break the circular dependency? |
| [Base32 Encoding](base32.md) | Why doesn't Nix use standard base32? What's different? |
| [Overlays & Bootstrap](overlays.md) | How do overlays compose via fixed-point? How does stdenv bootstrap GCC from scratch? |

## The big picture

When you write `nix build nixpkgs#hello`, here's what happens at the level pix operates:

```
1. Nix evaluates the expression → produces a Derivation

2. The derivation is serialized to ATerm and written as a .drv file
   (derivation.py can parse this back)

3. Output paths in the .drv are computed via hashDerivationModulo:
   - Hash the .drv with output paths blanked out
   - Use that hash as the fingerprint for make_store_path
   (derivation.py + store_path.py)

4. The .drv is sent to the daemon via the Unix socket protocol
   (daemon.py speaks this protocol)

5. The daemon builds it:
   - Realizes input sources (their store paths were computed
     the same way, using NAR hashes — nar.py + store_path.py)
   - Runs the builder
   - Registers the output in the store database

6. You can query the result via the daemon:
   - is_valid_path, query_path_info
   - The NAR hash and references are recorded
```

Each step has a corresponding pix module. The code is short enough that you can trace the entire flow.
