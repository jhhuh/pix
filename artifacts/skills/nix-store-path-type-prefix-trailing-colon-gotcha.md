# Nix Store Path Type Prefix: Trailing Colon Gotcha

## The Problem

When computing Nix store paths, the fingerprint type prefix (`text`, `source`) has **NO trailing colon** when the references list is empty.

```
Correct:   "text"           (empty refs)
Correct:   "text:ref1:ref2" (with refs)
Wrong:     "text:"          (empty refs — one extra character, completely different hash)
```

## Why It Happens

A naive implementation:
```python
type_str = "text:" + ":".join(refs)   # BUG: produces "text:" when refs is []
```

Nix's C++ builds the string by appending `:ref` for each reference, so an empty list naturally produces no colon.

## The Fix

```python
def _make_type(base: str, refs: list[str]) -> str:
    t = base
    for r in sorted(refs):
        t += ":" + r
    return t
```

## How It Was Discovered

Unit tests with synthetic data didn't catch this — the bug only appeared in end-to-end verification against the real Nix daemon's `add_text_to_store`. The computed store path silently differed from the daemon's result.

## Key Lesson

For any reimplementation project: **always verify end-to-end against the reference implementation**, not just unit tests with hand-crafted vectors. The delimiter edge case is invisible to pure reasoning.
