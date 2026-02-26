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

We implemented the same 3-stage bootstrap in four different ways. All four pass identical tests — same late-binding behavior, same override semantics. But each has different failure modes.

Source: [`experiments/`](https://github.com/jhhuh/pix/tree/master/experiments) — each subfolder is self-contained with a bootstrap and test file.

### A: Class inheritance

```python
class Stage0(PackageSet):
    @cached_property
    def shell(self):
        return drv(name="shell", builder="/bin/sh", ...)

    @cached_property
    def tools(self):
        return drv(name="tools", deps=[self.shell], ...)  # self = final

    @cached_property
    def app(self):
        return drv(name="app", deps=[self.shell, self.tools], ...)

class Stage1(Stage0):
    @cached_property
    def _prev(self):
        return Stage0()  # prev = separate instance

    @cached_property
    def tools(self):
        return drv(name="tools-v1", deps=[self._prev.shell], ...)
```

**`final`** = `self`. Python's MRO resolves `self.shell` to the most-derived override — exactly like Nix's `final.shell`.

**`prev`** = `self._prev`. A `@cached_property` that creates a fresh instance of the parent class.

**Lesson learned:** The first attempt used only `self` and no `_prev` — see [The infinite recursion trap](#the-infinite-recursion-trap) below.

### B: `__getattr__` chain

```python
base = AttrSet({
    "shell": lambda final: drv(name="shell", ...),
    "tools": lambda final: drv(name="tools", deps=[final.shell], ...),
    "app":   lambda final: drv(name="app", deps=[final.shell, final.tools], ...),
})

stage1 = Overlay(base, lambda final, prev: {
    "tools": lambda final: drv(name="tools-v1", deps=[prev.shell], ...),
})
stage1._set_final(stage1)
```

**`final`** = a `_final` reference propagated down the chain. Every node in the chain points to the outermost `Overlay`.

**`prev`** = the `_prev` link. `__getattr__` delegates to `_prev` for attributes not overridden in the current layer.

**Lesson learned:** The `_final` reference is mutable shared state. If you compose the same `AttrSet` into two different chains, the second `_set_final()` corrupts the first.

### C: Lazy fixed-point

```python
def base_overlay(final, prev):
    return {
        "shell": lambda: drv(name="shell", ...),
        "tools": lambda: drv(name="tools", deps=[final.shell], ...),
        "app":   lambda: drv(name="app", deps=[final.shell, final.tools], ...),
    }

def stage1_overlay(final, prev):
    return {"tools": lambda: drv(name="tools-v1", deps=[prev["shell"]()], ...)}

result = fix(compose_overlays([base_overlay, stage1_overlay]))
```

**`final`** = the `LazyAttrSet` passed to overlay functions by `fix()`. Attribute access triggers thunk evaluation.

**`prev`** = a plain dict of thunks from previous layers. Access: `prev["name"]()`.

**Lesson learned:** Two different APIs for the same concept: `final.shell` (attribute access) vs `prev["shell"]()` (dict lookup + call). This is a usability gap — typos in string keys fail at runtime, not import time.

### D: Class decorator

```python
class Stage0(PackageSet):
    @cached_property
    def shell(self): return drv(name="shell", ...)
    @cached_property
    def tools(self): return drv(name="tools", deps=[self.shell], ...)
    @cached_property
    def app(self):   return drv(name="app", deps=[self.shell, self.tools], ...)

@overlay(tools=lambda self, prev: drv(name="tools-v1", deps=[prev.shell], ...))
class Stage1(Stage0): pass
```

**`final`** = `self` — same MRO-based late binding as Experiment A.

**`prev`** = `self._prev` — injected by the `@overlay` decorator automatically.

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

|                           | A: Inheritance | B: `__getattr__` | C: Lazy Fix | D: Decorator |
|---------------------------|:-:|:-:|:-:|:-:|
| Lines (infra + bootstrap) | 153 | 198 | 169 | 130 |
| `final` mechanism         | `self` (MRO) | `_final` ref | `LazyAttrSet` proxy | `self` (MRO) |
| `prev` mechanism          | `self._prev` (manual) | `_prev` chain | `prev` dict | `self._prev` (auto) |
| IDE completion            | yes | no | no | partial |
| Type checking             | yes | no | no | partial |
| Dynamic composition       | no | yes | yes | no |
| Recursion detection       | none (hangs) | none (hangs) | yes (diagnostic) | none (hangs) |
| Nix fidelity              | low | medium | high | medium |
| Boilerplate per overlay   | ~10 lines | ~5 lines | ~5 lines | ~3 lines |

### Nix fidelity

- **C** is a line-for-line translation of `lib.fix` and `lib.composeExtensions`.
- **B** captures the same semantics dynamically but wraps them in Python objects.
- **D** maps overlays to decorators — same semantics, different syntax.
- **A** maps overlays to class inheritance — the furthest departure. The fixed-point is implicit in `self`, and `prev` requires manual plumbing.

### Static vs dynamic composition

In **A** and **D**, the overlay chain is fixed at class definition time. You can't add a new stage between Stage1 and Stage2 without editing source.

In **B** and **C**, overlays are plain functions composed at runtime. You can programmatically build overlay lists — which is exactly what nixpkgs does with `config.nixpkgs.overlays`.

### Mutability hazards

Python objects are mutable. Each pattern has different exposure:

- **A**: `self._prev` creates fresh instances, so stages don't share mutable state. But if two codepaths instantiate `Stage2()` independently, they get independent `_prev` chains — correct but potentially wasteful.
- **B**: The `_final` reference is mutable shared state on the chain. Composing the same `AttrSet` into two chains causes the second `_set_final()` to overwrite the first.
- **C**: Each `fix()` call creates a new `LazyAttrSet` with its own cache. But `prev` is a shared dict — if an overlay mutates it (instead of merging), earlier layers get corrupted.
- **D**: Same as A internally — the decorator creates `_prev` the same way.

### When to use which

- **A** — when the chain is small, static, and you want full IDE support.
- **B** — when overlays must be composed dynamically (plugin systems).
- **C** — when faithfully modeling Nix semantics (educational use, porting Nix code).
- **D** — best balance for Python projects: minimal boilerplate, IDE-friendly base classes, declarative overlay syntax.

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

All 38 input derivations of the final stdenv trace back, through the overlay chain, to the single bootstrap-tools tarball.
