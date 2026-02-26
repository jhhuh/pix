# Overlay Pattern Comparison

Four Python patterns for implementing Nix's overlay/fixed-point semantics.
All four pass the same 9 tests — late binding, override propagation, caching.

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
experiments/a_class_inherit/   153 lines (pkgset.py + bootstrap.py)
```

```python
class Stage0(PackageSet):
    @cached_property
    def shell(self): ...
    @cached_property
    def tools(self): return drv(deps=[self.shell])   # self = final
    @cached_property
    def app(self):   return drv(deps=[self.shell, self.tools])

class Stage1(Stage0):
    @cached_property
    def _prev(self): return Stage0()                 # prev = separate instance
    @cached_property
    def tools(self): return drv(deps=[self._prev.shell])  # build dep from prev
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
- Naive `self`-only approach causes infinite recursion (see below).
- Each stage must manually define `_prev` with the correct parent class.
- Adding a stage between two existing stages requires editing the class that was previously "next".

**Infinite recursion pitfall**: The first attempt used `self.shell` everywhere (no `_prev`). This creates a cycle when Stage2.shell depends on `self.tools` and Stage1.tools depends on `self.shell` — both resolve via MRO to the most-derived override, chasing each other indefinitely. `super()` doesn't fix it because `self` stays bound to the most-derived instance. `@cached_property` doesn't break it because caching only works after computation, not during. Full analysis in `artifacts/skills/python-class-inheritance-infinite-recursion-in-overlay-pattern.md`.

---

## B: `__getattr__` Chain

```
experiments/b_getattr_chain/   198 lines (overlay.py + bootstrap.py)
```

```python
base = AttrSet({
    "shell": lambda final: drv(...),
    "tools": lambda final: drv(deps=[final.shell]),
    "app":   lambda final: drv(deps=[final.shell, final.tools]),
})
stage1 = Overlay(base, lambda final, prev: {
    "tools": lambda final: drv(deps=[prev.shell]),
})
stage2 = Overlay(stage1, lambda final, prev: {
    "shell": lambda final: drv(deps=[prev.tools]),
})
stage2._set_final(stage2)  # propagate final ref down the chain
```

**final**: `_final` reference propagated through the chain via `_set_final()`.
**prev**: The `_prev` link — each `Overlay` wraps the previous layer. `__getattr__` delegates to `_prev` for non-overridden attributes.

**Strengths**:
- Dynamic composition. Overlays can be added at runtime; no class hierarchy needed.
- Closest to how Nix overlays actually work conceptually.
- Both `final` and `prev` are explicit function arguments — no ambiguity.
- Natural for programmatically-generated overlay lists.

**Weaknesses**:
- Most code (198 lines). `object.__setattr__` / `object.__getattribute__` boilerplate everywhere to avoid `__getattr__` interception.
- No IDE completion for virtual attributes. `stage2.shell` is invisible to static analysis.
- Debugging is hard — `__getattr__` chains don't show in stack traces clearly.
- Must manually call `_set_final()` to wire up open recursion. Forgetting this breaks everything silently.
- Mutable `_final` reference: if you compose the same `AttrSet` into two different chains, the second `_set_final()` corrupts the first chain. Requires creating fresh objects per chain.

---

## C: Lazy Fix

```
experiments/c_lazy_fix/        169 lines (lazy.py + bootstrap.py)
```

```python
def base_overlay(final, prev):
    return {
        "shell": lambda: drv(...),
        "tools": lambda: drv(deps=[final.shell]),
        "app":   lambda: drv(deps=[final.shell, final.tools]),
    }

def stage1_overlay(final, prev):
    return {"tools": lambda: drv(deps=[prev["shell"]()])}

result = fix(compose_overlays([base_overlay, stage1_overlay, stage2_overlay]))
```

**final**: The `LazyAttrSet` passed to overlays by `fix()` — attribute access triggers thunk evaluation.
**prev**: A plain dict of thunks from previously-composed layers. Access via `prev["name"]()`.

**Strengths**:
- Direct translation of Nix's `lib.fix` and `lib.composeExtensions`. If you know Nix, you can read this immediately.
- Overlays are plain functions — no classes, no inheritance, no decorators.
- `_evaluating` set provides clear infinite-recursion detection with a diagnostic message.
- Composition is a pure fold: `compose_overlays` merges dicts left-to-right.
- Immutable by construction: each `fix()` call produces a new `LazyAttrSet`.

**Weaknesses**:
- Two APIs for the same thing: `final.shell` (attribute access) vs `prev["shell"]()` (dict + call). Easy to mix up.
- No type safety. Typos in string keys fail at runtime, not import time.
- No IDE support for attributes on `LazyAttrSet` or keys in `prev` dicts.
- Zero-arg thunks (`lambda: ...`) add noise. Every value is wrapped in an extra lambda compared to the other patterns.

---

## D: Class Decorator

```
experiments/d_decorator/       130 lines (decorator.py + bootstrap.py)
```

```python
class Stage0(PackageSet):
    @cached_property
    def shell(self): ...
    @cached_property
    def tools(self): return drv(deps=[self.shell])
    @cached_property
    def app(self):   return drv(deps=[self.shell, self.tools])

@overlay(
    tools=lambda self, prev: drv(deps=[prev.shell]),
)
class Stage1(Stage0):
    pass
```

**final**: `self` — same as Experiment A, MRO-based late binding.
**prev**: `self._prev` — injected automatically by the `@overlay` decorator.

**Strengths**:
- Least code (130 lines). Decorator hides all the `_prev` / `cached_property` wiring.
- Overlay body is declarative: `@overlay(tools=lambda self, prev: ...)`.
- Combines inheritance's late binding with dynamic overlay specification.
- Stage classes are empty (`pass`) — the decorator does all the work.
- Base class (Stage0) is identical to Experiment A — same IDE support, same type annotations.

**Weaknesses**:
- `type(cls.__name__, (cls,), attrs)` dynamically creates classes. Debugger and IDE see generated classes, not the source.
- `isinstance` checks can be surprising: the decorated `Stage1` is not the class written in source — it's a dynamically-created subclass.
- Decorator internals are non-trivial (closure over `make_prop`, `_b=base` default-arg capture).
- Same static-composition limitation as A: can't add overlays at runtime without creating new classes.

---

## Side-by-Side

|                          | A: Inheritance | B: `__getattr__` | C: Lazy Fix | D: Decorator |
|--------------------------|:-:|:-:|:-:|:-:|
| Lines (infra + bootstrap) | 153 | 198 | 169 | 130 |
| `final` mechanism        | `self` (MRO) | `_final` ref | `LazyAttrSet` proxy | `self` (MRO) |
| `prev` mechanism         | `self._prev` (manual) | `_prev` chain | `prev` dict | `self._prev` (auto) |
| IDE completion           | yes | no | no | partial |
| Type checking            | yes | no | no | partial |
| Dynamic composition      | no | yes | yes | no |
| Recursion safety         | pitfall (see above) | silent hang | detected + diagnostic | safe (decorator handles it) |
| Nix fidelity             | low | medium | high | medium |
| Boilerplate per overlay  | ~10 lines | ~5 lines | ~5 lines | ~3 lines |

### Nix fidelity

How closely does each pattern mirror Nix's actual mechanism?

- **C** is a direct translation: `fix`, `compose_overlays`, `(final, prev) -> dict` are line-for-line equivalents of `lib.fix`, `lib.composeExtensions`, `final: prev: { ... }`.
- **B** captures the same semantics dynamically but wraps them in Python objects rather than plain functions.
- **D** maps Nix overlays to decorators — same semantics, different surface syntax.
- **A** maps overlays to class inheritance — the furthest departure. The fixed-point is implicit in `self`, and `prev` requires manual plumbing.

### When to use which

- **A (Inheritance)**: When the stage chain is known at definition time and you want full IDE support. Good for small, well-understood bootstrap sequences.
- **B (`__getattr__`)**: When overlays must be composed dynamically (e.g., user-provided plugin overlays). Pays for flexibility with debugging difficulty.
- **C (Lazy Fix)**: When faithfully modeling Nix semantics matters more than Python ergonomics. Best for educational purposes or when porting Nix code 1:1.
- **D (Decorator)**: Best overall balance for Python projects. Minimal boilerplate, clear separation of base and overlay, IDE-friendly base classes. Use when the overlay chain is known at definition time but you want cleaner syntax than raw inheritance.

---

## Open Question: Scale

Nix's nixpkgs has ~100,000 packages in a single attribute set. In Python:

- **A and D** (class-based): Each package is a `@cached_property`. Defining 100K methods on a class is unusual but technically works — `cached_property` stores values in `instance.__dict__`, which is just a dict. Memory: one dict entry per evaluated package.
- **B and C** (dict-based): Thunks are entries in a plain dict. 100K entries is trivial. Memory: same — one entry per evaluated thunk.

The real concern is not storage but **definition ergonomics**. 100K `@cached_property` methods in a single class file is absurd. Nix solves this with `callPackage` — each package is a separate file, auto-imported. The Python equivalent is `PackageSet.call()` (Experiment A's `pkgset.py`) or a registry pattern that dynamically adds attributes.

All four patterns are compatible with a `callPackage`-like auto-import mechanism. The choice of overlay pattern is orthogonal to how packages are defined and loaded.
