# Overlays and the Bootstrap Fixed-Point

Nix's overlay system is how nixpkgs composes 100,000+ packages into a single attribute set — and how the stdenv bootstrap rebuilds the toolchain from scratch. The core mechanism is **fixed-point evaluation**: overlays reference the final result before it exists, and laziness makes it work.

This page explores the theory through four Python implementations, each revealing different aspects of how the pattern works — and different ways it can break.

## The Nix overlay model

An overlay is a function of two arguments:

```nix
overlay = final: prev: {
  tools = mkTools { shell = prev.shell; };
};
```

| Argument | Meaning | Used for |
|----------|---------|----------|
| `final` | The completed result (after all overlays) | Late binding: `final.gcc` gets the most-derived version |
| `prev` | The previous layer (before this overlay) | Build deps: `prev.shell` gets the version before this override |

Overlays are composed into a single function via `lib.composeExtensions`, then evaluated via `lib.fix`:

```nix
fix = f: let x = f x; in x;
```

The result `x` is passed to `f` as its own argument — a circular definition that works because Nix is lazy. Attribute access triggers evaluation on demand.

### Why two arguments?

A single argument isn't enough. Consider a 3-stage bootstrap:

```
Stage 0:  shell-v0, tools-v0, app (uses shell + tools)
Stage 1:  tools-v1 (rebuilt with stage0's shell)
Stage 2:  shell-v1 (rebuilt with stage1's tools)
```

Stage 2 overrides `shell` and builds it using `prev.tools` (= stage 1's tools). But stage 1's `tools` override was built using `prev.shell` (= stage 0's shell). If stage 1 used `final.shell` instead of `prev.shell`, it would see stage 2's override — which depends on stage 1's tools — creating a cycle.

```
                    ┌──────────── cycle! ────────────┐
                    │                                │
                    v                                │
final.shell ──> stage2.shell(final.tools)           │
                    │                                │
                    v                                │
            final.tools ──> stage1.tools(final.shell)┘
```

The `prev` argument breaks the cycle: each override builds with the *previous* stage's value, not the final one. The `final` argument provides open recursion: non-overridden packages like `app` reference `final.shell` and `final.tools`, automatically picking up the latest overrides.

---

## Four Python implementations

All four patterns implement the **complete 7-stage nixpkgs bootstrap** — 196 derivations from bootstrap seed through to `hello-2.12.2`, every one **hash-perfect** against real nixpkgs.

Source: [`experiments/`](https://github.com/jhhuh/pix/tree/master/experiments) — each subfolder is self-contained with a bootstrap and test file.

### Hash-perfect verification

The experiments reconstruct all 196 derivations from real `.drv` files in the Nix store:

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

Every derivation is **byte-identical** to real nixpkgs — every `.drv` path and output path matches exactly. This is not about reproducing nixpkgs; it is a **verification strategy**. Because Nix derivation hashes are computed purely from their inputs, we can verify the entire hash pipeline (ATerm serialization, `hashDerivationModulo`, `make_output_path`, `make_text_store_path`) by comparing output paths — without ever building anything.

### A: Class inheritance

```python
class Stage0(PackageSet):
    @cached_property
    def _own_packages(self) -> dict[str, Package]:
        return {dp: packages[dp] for dp in stages[0]}

    @cached_property
    def all_packages(self) -> dict[str, Package]:
        return dict(self._own_packages)

class Stage1(Stage0):
    @cached_property
    def _prev(self) -> Stage0:
        return Stage0()  # prev = separate instance

    @cached_property
    def _own_packages(self) -> dict[str, Package]:
        return {dp: packages[dp] for dp in stages[1]}

    @cached_property
    def all_packages(self) -> dict[str, Package]:
        return {**self._prev.all_packages, **self._own_packages}

# 8 classes: Stage0 → Stage1 → StageXgcc → Stage2 → Stage3 → Stage4 → Final → Pkgs
```

**`final`** = `self`. Python's MRO resolves to the most-derived override — exactly like Nix's `final`.

**`prev`** = `self._prev`. A `@cached_property` that creates a fresh instance of the parent class.

**Lesson learned:** The first attempt used only `self` and no `_prev` — see [The infinite recursion trap](#the-infinite-recursion-trap) below.

### B: `__getattr__` chain

```python
base = StageSet(stage_idx=0)          # 4 packages
s1   = OverlaySet(base, stage_idx=1)  # adds 8 packages
s2   = OverlaySet(s1, stage_idx=2)    # adds 6 packages
...
top  = OverlaySet(s6, stage_idx=7)    # adds hello
```

**`final`** = shared via `_set_final()` propagation down the chain.

**`prev`** = the `_prev` link. Each `OverlaySet` wraps the previous layer.

**Lesson learned:** The `_final` reference is mutable shared state. If you compose the same `AttrSet` into two different chains, the second `_set_final()` corrupts the first.

### C: Lazy fixed-point

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

**`final`** = the `LazyAttrSet` passed to overlay functions by `fix()`. Attribute access triggers thunk evaluation.

**`prev`** = a plain dict of thunks from previous layers. Access: `prev["name"]()`.

**Lesson learned:** Two different APIs for the same concept: `final.attr` (attribute access) vs `prev["name"]()` (dict lookup + call). Typos in string keys fail at runtime, not import time.

### D: Class decorator

```python
class Stage0(PackageSet):
    @cached_property
    def _own_packages(self): ...
    @cached_property
    def all_packages(self): return dict(self._own_packages)

@stage_overlay(1)
class Stage1(Stage0): pass

@stage_overlay(2)
class StageXgcc(Stage1): pass

# ... through @stage_overlay(7) class Pkgs(Final): pass
```

**`final`** = `self` — same MRO-based late binding as Pattern A.

**`prev`** = `self._prev` — injected by the `@stage_overlay` decorator automatically.

**Lesson learned:** The decorator hides all plumbing (creating `_prev`, wrapping as `@cached_property`), but `type(cls.__name__, (cls,), attrs)` creates a dynamic class. The decorated `Stage1` is not the class you wrote — it's a generated subclass.

---

## The infinite recursion trap

The most instructive failure came from Experiment A. The first attempt used `self` for everything:

```python
class Stage1(Stage0):
    @cached_property
    def tools(self):
        return drv(name="tools-v1", deps=[self.shell], ...)  # ← self.shell

class Stage2(Stage1):
    @cached_property
    def shell(self):
        return drv(name="shell-v1", deps=[self.tools], ...)  # ← self.tools
```

This looks natural — but produces `RecursionError`.

### The cycle

When you access `Stage2().app`:

```
Stage2().app
  → self.shell                  (MRO → Stage2.shell)
    → self.tools                (MRO → Stage1.tools)
      → self.shell              (MRO → Stage2.shell)
        → self.tools            (MRO → Stage1.tools)
          → ...                 RecursionError!
```

Stage2.shell needs `self.tools`. Stage1.tools needs `self.shell`. Both resolve via MRO to the most-derived override. The cycle is fundamental — not a bug in the code, but a consequence of conflating `final` and `prev` into a single reference.

### Why `super()` doesn't help

Python's `super()` changes which class the method is looked up on, but `self` remains the most-derived instance:

```python
class Stage2(Stage1):
    @cached_property
    def shell(self):
        # super().tools → Stage1.tools.__get__(self, Stage2)
        # But Stage1.tools uses self.shell → Stage2.shell → cycle!
        return drv(deps=[super().tools])
```

### Why `@cached_property` doesn't help

`@cached_property` stores the result in `instance.__dict__` on first access. But the recursion happens *during* the first computation — before any value is cached:

```
self.shell  [start computing — not cached yet]
  → self.tools  [start computing — not cached yet]
    → self.shell  [STILL computing — nothing cached to return]
      → RecursionError
```

The cache only breaks cycles for values that have *already been computed*. It cannot break cycles during initial computation.

### The root cause

Nix overlays have two arguments. Python's `self` is one. The fix: add `self._prev` as the second.

```python
class Stage2(Stage1):
    @cached_property
    def _prev(self):
        return Stage1()  # ← separate instance of previous stage

    @cached_property
    def shell(self):
        return drv(deps=[self._prev.tools])  # ← prev, not final
```

Now `self._prev.tools` creates a `Stage1()` instance, which resolves `tools` on itself (not on the Stage2 instance), breaking the cycle.

!!! note "Rule of thumb"
    **Overridden methods** use `self._prev.X` for build dependencies (previous stage's values).
    **Inherited methods** use `self.X` — late binding gives open recursion for free.

    The same rule applies in Nix: overlays use `prev.X` for inputs they're rebuilding against, and `final.X` for attributes they want the final version of.

---

## Comparison

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

### Recommendation for pixpkgs

**Pattern A (Class Inheritance)** is the recommended pattern for pixpkgs. The canonical implementation lives in `pixpkgs/bootstrap.py`.

1. **IDE support at scale is non-negotiable.** With thousands of packages, developers need autocomplete, go-to-definition, and type checking.
2. **`callPackage` via `PackageSet.call()`** scales to any number of packages (each in a separate file).
3. **The bootstrap stages are fixed** — dynamic composition adds complexity without benefit.
4. **User-level customization** works through `Package.override()` (individual packages) or subclassing (set-level changes).
5. **"Static composition" is a feature** — it makes the bootstrap chain explicit and inspectable.

### When to use which

- **A** — recommended for production package sets. Full IDE support, type checking, `callPackage` scales to massive package counts.
- **B** — when overlays must be composed dynamically (plugin systems).
- **C** — when faithfully modeling Nix semantics (educational use, porting Nix code).
- **D** — minimal boilerplate variant of A, but dynamic class generation complicates debugging.

---

## Appendix: The nixpkgs stdenv bootstrap

The real nixpkgs stdenv bootstrap is a chain of 7 stages, each a specialized overlay. It solves a chicken-and-egg problem: to build GCC you need glibc, but to build glibc you need GCC.

### The seed

Everything starts from a single prebuilt tarball: `bootstrap-tools`. It contains 125 binaries (GCC, coreutils, binutils, bash, etc.) plus glibc and support libraries. This is the only external binary dependency — every other package is rebuilt from source.

### The stages

| Stage | What it overrides | Key build |
|-------|-------------------|-----------|
| **0** | nothing (seed) | Dummy stdenv with bootstrap-tools as compiler |
| **1** | gcc-wrapper, fetchurl | Binutils from source, perl (for later stages) |
| **xgcc** | gcc (first rebuild) | GCC compiled from source (but linked against bootstrap glibc) |
| **2** | **glibc** | Real glibc-2.40 compiled with xgcc (the libc transition) |
| **3** | **gcc** (final) | Final GCC compiled with the real glibc (the compiler transition) |
| **4** | coreutils, bash, sed, grep, ... | All standard tools from source (the tools transition) |
| **final** | assembles everything | Production stdenv — zero references to bootstrap-tools |

### Three transitions

The bootstrap solves the circular dependency through progressive replacement:

```
bootstrap-tools (prebuilt)
        │
   ┌────┴────┐
   │ Stage 1 │  binutils from source
   └────┬────┘
   ┌────┴────┐
   │  xgcc   │  GCC from source (but links against bootstrap glibc)
   └────┬────┘
   ┌────┴─────────────────────────────┐
   │ Stage 2: THE LIBC TRANSITION     │  xgcc compiles real glibc
   └────┬─────────────────────────────┘
   ┌────┴─────────────────────────────┐
   │ Stage 3: THE COMPILER TRANSITION │  real glibc compiles final GCC
   └────┬─────────────────────────────┘
   ┌────┴─────────────────────────────┐
   │ Stage 4: THE TOOLS TRANSITION    │  final GCC rebuilds coreutils, bash, ...
   └────┬─────────────────────────────┘
   ┌────┴────┐
   │  final  │  all components from source, no bootstrap refs
   └─────────┘
```

**Stage xgcc** is the subtlest. The xgcc binary itself is linked against junk from bootstrap-tools — but that doesn't matter. What matters is the *code xgcc emits*. That code will run against the real glibc built in stage 2.

### The overlay pattern in action

Each stage is an overlay: it overrides some packages and inherits the rest from the previous stage. Stage 2 overrides glibc but inherits xgcc from the xgcc stage. Stage 3 overrides gcc but inherits glibc from stage 2.

This is exactly the pattern our experiments demonstrate:

- `prev.tools` → "use the compiler from the previous stage to build glibc"
- `final.gcc` → "when hello uses gcc, it gets the most-derived version"

The final stdenv enforces completeness with `disallowedRequisites`: any reference to bootstrap-tools in the final output is a build failure. This guarantees the bootstrap is complete — every component has been rebuilt from source.

### The hello package

The canonical test: can the bootstrap produce a working `hello`?

```
hello-2.12.2.drv
  builder: bash-5.3p3     (rebuilt in stage 4)
  stdenv:  stdenv-linux    (the final stdenv)
  source:  hello-2.12.2.tar.gz (fetched via fetchurl)
```

All 196 derivations in the closure — from the bootstrap seed through to hello — trace back, through the overlay chain, to the single bootstrap-tools tarball. Our four experiments and the canonical `pixpkgs/bootstrap.py` reconstruct the full chain, hash-perfect against real nixpkgs.
