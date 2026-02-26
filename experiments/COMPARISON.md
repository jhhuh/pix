# Overlay Pattern Comparison

Four Python patterns for implementing Nix's overlay/fixed-point semantics.
All four express the full nixpkgs bootstrap chain (7 stages, 196 derivations → hello),
hash-perfect against real nixpkgs.

## The Problem

Nix overlays are functions `final: prev: { ... }` composed via a fixed-point.
Two arguments are essential:

- **`final`** — the completed result (open recursion). Non-overridden packages
  reference `final.gcc` and automatically see the latest override.
- **`prev`** — the previous layer. Overrides use `prev.shell` to get build
  dependencies without creating cycles.

Python has no built-in equivalent. `self` provides late binding (= `final`),
but there's no native `prev`. Each experiment solves this differently.

---

## A: Class Inheritance

```
experiments/a_class_inherit/   pkgset.py + bootstrap.py
```

```python
class Stage0(PackageSet):
    @cached_property
    def all_packages(self): ...  # 4 seed packages

class Stage1(Stage0):
    @cached_property
    def _prev(self): return Stage0()
    @cached_property
    def all_packages(self):
        return {**self._prev.all_packages, **self._own_packages}

# 8 classes: Stage0 → Stage1 → StageXgcc → Stage2 → Stage3 → Stage4 → Final → Pkgs
```

**final**: `self` — Python's MRO resolves to the most-derived override.
**prev**: `self._prev` — a `@cached_property` that creates a fresh instance of the parent class.

**Strengths**:
- Natural Python. IDE completion, type checking, go-to-definition all work.
- `@cached_property` provides laziness and memoization for free.
- Each stage is a real class with a docstring and explicit methods.
- `PackageSet.call()` enables `callPackage`-style auto-injection via `inspect.signature`.

**Weaknesses**:
- Static composition. Overlay list is fixed at class definition time.
- `_prev` creates separate instance per stage — 7-deep cascade for the full bootstrap (lazy, so cost is proportional to overrides actually accessed).
- Infinite recursion pitfall when an override uses `self.X` and X is overridden by a later stage. See `artifacts/skills/python-class-inheritance-infinite-recursion-in-overlay-pattern.md`.

---

## B: `__getattr__` Chain

```
experiments/b_getattr_chain/   overlay.py + bootstrap.py
```

```python
base = StageSet(stage_idx=0)          # 4 packages
s1   = OverlaySet(base, stage_idx=1)  # adds 8 packages
s2   = OverlaySet(s1, stage_idx=2)    # adds 6 packages
...
top  = OverlaySet(s6, stage_idx=7)    # adds hello
```

**final**: Shared via `_set_final()` propagation (not used in full bootstrap since packages are pre-computed).
**prev**: `_prev` link — each `OverlaySet` wraps the previous layer.

**Strengths**:
- Dynamic composition. Overlays can be added at runtime; no class hierarchy needed.
- Closest to how Nix overlays actually work conceptually.
- Both `final` and `prev` are explicit function arguments — no ambiguity.

**Weaknesses**:
- No IDE completion for virtual attributes.
- `_set_final()` is a mutable side-effect — corrupts if same overlay used in two chains.
- `object.__setattr__` / `object.__getattribute__` boilerplate everywhere.
- Debugging `__getattr__` chains is hard.

---

## C: Lazy Fix

```
experiments/c_lazy_fix/        lazy.py + bootstrap.py
```

```python
result = fix(compose_overlays([
    base_overlay,          # stage0: 4 packages
    stage1_overlay,        # +8
    stage_xgcc_overlay,    # +6
    stage2_overlay,        # +44
    stage3_overlay,        # +23
    stage4_overlay,        # +19
    final_overlay,         # +63
    hello_overlay,         # +29 = 196 total
]))
```

**final**: The `LazyAttrSet` passed to overlays by `fix()`.
**prev**: A plain dict of thunks from previously-composed layers.

**Strengths**:
- Direct translation of Nix's `lib.fix` and `lib.composeExtensions`.
- Overlays are plain functions — most composable, most modular.
- `_evaluating` set provides clear infinite-recursion detection.
- Immutable by construction: each `fix()` call produces a new `LazyAttrSet`.
- Single fixed-point object — no instance cascade.

**Weaknesses**:
- Two APIs: `final.attr` vs `prev["name"]()` — confusing.
- No type safety. No IDE support.
- Zero-arg thunks add noise everywhere.

---

## D: Class Decorator

```
experiments/d_decorator/       decorator.py + bootstrap.py
```

```python
class Stage0(PackageSet):
    @cached_property
    def all_packages(self): ...  # 4 seed packages

@stage_overlay(1)
class Stage1(Stage0): pass

@stage_overlay(2)
class StageXgcc(Stage1): pass

# ... through @stage_overlay(7) class Pkgs(Final): pass
```

**final**: `self` — same as A, MRO-based late binding.
**prev**: `self._prev` — injected automatically by the decorator.

**Strengths**:
- Least boilerplate per stage — decorator hides all wiring.
- Declarative: `@stage_overlay(n)` is the entire stage definition.
- Base class (Stage0) has full IDE support.

**Weaknesses**:
- `type(cls.__name__, (cls,), attrs)` creates dynamic classes — debugger sees generated classes.
- Same `_prev` cascade as A.
- Decorator internals are non-trivial.
- `isinstance` checks can surprise.

---

## Side-by-Side

|                          | A: Inheritance | B: `__getattr__` | C: Lazy Fix | D: Decorator |
|--------------------------|:-:|:-:|:-:|:-:|
| `final` mechanism        | `self` (MRO) | `_final` ref | `LazyAttrSet` proxy | `self` (MRO) |
| `prev` mechanism         | `self._prev` (manual) | `_prev` chain | `prev` dict | `self._prev` (auto) |
| IDE completion           | yes | no | no | partial |
| Type checking            | yes | no | no | partial |
| Dynamic composition      | no | yes | yes | no |
| Recursion safety         | pitfall (documented) | silent hang | detected + diagnostic | safe (decorator) |
| Nix fidelity             | low | medium | high | medium |
| Memory (7 stages)        | 7 instance trees | 1 chain | 1 fixed-point | 7 instance trees |

### Full bootstrap results

All four patterns compose the complete nixpkgs bootstrap chain:

| Stage | New packages | Cumulative | Key builds |
|-------|:---:|:---:|---|
| stage0 | 4 | 4 | busybox, tarball, bootstrap-tools, stage0-stdenv |
| stage1 | 8 | 12 | binutils-wrapper, gcc-wrapper, gnu-config |
| stage-xgcc | 6 | 18 | xgcc-14.3.0, gmp, mpfr, isl, libmpc |
| stage2 | 44 | 62 | glibc-2.40, binutils, bison, perl (libc transition) |
| stage3 | 23 | 85 | gcc-14.3.0, linux-headers (compiler transition) |
| stage4 | 19 | 104 | coreutils, bash rebuild (tools transition) |
| final | 63 | 167 | stdenv-linux, gcc-wrapper, coreutils, findutils... |
| hello | 29 | **196** | **hello-2.12.2**, curl, openssl, perl |

Every derivation is hash-perfect against real nixpkgs (verified by ATerm byte comparison).

### Recommendation for pixpkgs

**Pattern A (Class Inheritance)** is the recommended pattern for pixpkgs:

1. **IDE support at scale is non-negotiable.** With thousands of packages, developers need autocomplete, go-to-definition, and type checking.
2. **`callPackage` via `PackageSet.call()`** scales to any number of packages (each in a separate file).
3. **The bootstrap stages are fixed** — dynamic composition adds complexity without benefit.
4. **User-level customization** works through `Package.override()` (individual packages) or subclassing (set-level changes).
5. **"Static composition" is a feature** — it makes the bootstrap chain explicit and inspectable.

The canonical implementation lives in `pixpkgs/bootstrap.py`.
