# Test-Against-Real-System Verification Pattern

## The Pattern

When reimplementing a system (protocol, format, algorithm), use two layers of testing:

1. **Unit tests with known vectors** — gets you ~80% correct. Generate vectors by running the real system's CLI commands and hardcoding the expected outputs.

2. **End-to-end verification against the live system** — catches the remaining ~20%. Run your implementation alongside the real system and compare outputs byte-for-byte.

## Why Unit Tests Aren't Enough

In the pix project, unit tests with synthetic data passed (23/28 on first run), but three critical bugs were only caught by E2E verification:

- **Trailing colon in type prefix** — computed store path silently differed from daemon's `add_text_to_store` result
- **Daemon handshake field ordering** — only visible when actually connecting to the daemon
- **`hashDerivationModulo` two-mode distinction** — only visible when building derivations with dependencies through the real daemon

## Implementation

```python
# Generate test vectors from the real system:
# nix hash path --type sha256 --base32 ./test-file
# nix derivation show /nix/store/xxx.drv
# nix path-info --json /nix/store/xxx

# Then in E2E tests:
def test_store_path_matches_daemon():
    with DaemonConnection() as conn:
        daemon_path = conn.add_text_to_store("test", b"hello", [])
    computed_path = make_text_store_path("test", b"hello", [])
    assert computed_path == daemon_path
```

## Broader Applicability

This pattern applies to any reimplementation work: protocol parsers, file format writers, cryptographic implementations, API clients. The real system is the ultimate oracle — pure reasoning misses edge cases that are implicit in the reference implementation.
