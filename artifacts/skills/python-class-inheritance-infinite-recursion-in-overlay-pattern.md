# Infinite Recursion in Class Inheritance Overlay Pattern

## The Problem

When implementing Nix overlays via Python class inheritance, the naive approach
causes infinite recursion. This is a fundamental mismatch between Nix's overlay
semantics (which have **two** arguments: `final` and `prev`) and Python's
method override (which only has **one** implicit argument: `self`).

## The Naive (Broken) Approach

The first attempt mapped the overlay chain directly to class inheritance:

```python
class Stage0(PackageSet):
    @cached_property
    def shell(self):
        return drv(name="shell", builder="/bin/sh",
                   args=["-c", "echo shell-v0 > $out"])

    @cached_property
    def tools(self):
        return drv(name="tools", builder="/bin/sh",
                   args=["-c", f"echo tools-v0-with-{self.shell.name} > $out"],
                   deps=[self.shell])

    @cached_property
    def app(self):
        return drv(name="app", builder="/bin/sh",
                   args=["-c", f"echo app-with-{self.shell.name}-{self.tools.name} > $out"],
                   deps=[self.shell, self.tools])


class Stage1(Stage0):
    @cached_property
    def tools(self):
        # Override: rebuild tools with stage0's shell
        # WRONG: uses self.shell — but self is late-bound!
        return drv(name="tools-v1", builder="/bin/sh",
                   args=["-c", f"echo tools-v1-rebuilt-with-{self.shell.name} > $out"],
                   deps=[self.shell])


class Stage2(Stage1):
    @cached_property
    def shell(self):
        # Override: rebuild shell with stage1's tools
        # WRONG: uses self.tools — but self is late-bound!
        return drv(name="shell-v1", builder="/bin/sh",
                   args=["-c", f"echo shell-v1-rebuilt-with-{self.tools.name} > $out"],
                   deps=[self.tools])
```

## The Recursion Trace

When you instantiate `Stage2()` and access `.app`:

```
Stage2().app
  → self.shell  (MRO resolves to Stage2.shell)
    → Stage2.shell accesses self.tools  (MRO resolves to Stage1.tools)
      → Stage1.tools accesses self.shell  (MRO resolves to Stage2.shell)
        → Stage2.shell accesses self.tools  (MRO resolves to Stage1.tools)
          → ... RecursionError!
```

The cycle: **Stage2.shell needs self.tools → Stage1.tools needs self.shell → Stage2.shell needs self.tools → ...**

This is NOT a bug in the logic — it's a fundamental property. In the real Nix
bootstrap:
- Stage2 rebuilds `shell` using tools from the **previous** stage (stage1)
- Stage1 rebuilds `tools` using shell from the **previous** stage (stage0)

But with a single `self`, there's no distinction between "previous stage's
value" and "current stage's value". `self.tools` in Stage2 always resolves to
the most-derived override (Stage1.tools), and `self.shell` in Stage1 always
resolves to the most-derived override (Stage2.shell). The cycle is inherent
in using `self` for both roles.

## Why `super()` Doesn't Help

You might think `super()` solves this — after all, `super().shell` in Stage2
should give Stage1's shell (which is just Stage0.shell). But `super()` in
Python cooperates with the MRO and still binds `self` to the current instance:

```python
class Stage2(Stage1):
    @cached_property
    def shell(self):
        # super().tools → Stage1.tools.__get__(self, Stage2)
        # But Stage1.tools still uses self.shell, which is Stage2.shell!
        return drv(name="shell-v1", deps=[super().tools])  # Still recurses!
```

`super()` changes **which class** the method is looked up on, but `self`
remains the Stage2 instance. So `Stage1.tools` still sees `self.shell` →
`Stage2.shell` → `self.tools` → cycle.

## Why `cached_property` Doesn't Break the Cycle

Python's `@cached_property` stores the result in the instance's `__dict__` on
first access. If the value is already cached, it returns immediately. But the
recursion happens **during the first computation** — before any value is cached:

```
Stage2().shell  [not cached yet, start computing]
  → self.tools  [not cached yet, start computing]
    → self.shell [not cached yet — STILL COMPUTING, no cached value exists]
      → RecursionError
```

The cache can only break cycles for values that have **already been computed**.
It cannot break cycles during initial computation.

## The Root Cause: Nix Has Two Arguments, Python Has One

Nix overlays receive both `final` (the fixed-point result) and `prev` (the
previous layer):

```nix
overlay = final: prev: {
  tools = mkTools { shell = prev.shell; };  # BUILD dep from prev
  app = mkApp { inherit (final) shell tools; };  # RUNTIME deps from final
};
```

The distinction is critical:
- **`prev`**: "what the previous stage produced" — used for BUILD dependencies
  to avoid cycles (you build new tools with the old shell, not the new shell
  you haven't built yet)
- **`final`**: "what the current stage will produce" — used for late-bound
  references so non-overridden packages pick up overrides from this stage

Python's `self` conflates both into one reference. There's no built-in way to
say "give me the previous stage's version of this attribute."

## The Fix: Explicit `_prev`

Add a `_prev` cached property that creates a separate instance of the parent
class:

```python
class Stage1(Stage0):
    @cached_property
    def _prev(self) -> Stage0:
        return Stage0()  # separate instance = previous stage

    @cached_property
    def tools(self):
        # self._prev.shell = Stage0's shell (no cycle)
        # self = final (Stage2 if accessed through Stage2)
        return drv(name="tools-v1",
                   deps=[self._prev.shell])  # BUILD dep from prev


class Stage2(Stage1):
    @cached_property
    def _prev(self) -> Stage1:
        return Stage1()  # separate instance = previous stage

    @cached_property
    def shell(self):
        # self._prev.tools = Stage1's tools (no cycle)
        return drv(name="shell-v1",
                   deps=[self._prev.tools])  # BUILD dep from prev
```

Now the resolution trace:

```
Stage2().app
  → self.shell  (Stage2.shell)
    → self._prev.tools  (Stage1()._prev.shell → Stage0().shell → OK!)
  → self.tools  (Stage1.tools via MRO)
    → self._prev.shell  (but self is Stage2, so _prev = Stage1())
      → Stage1()._prev.shell → Stage0().shell → OK!
```

No cycle. Each `_prev` creates a fresh instance of the parent class, which
has its own `_prev` (or none, in Stage0's case).

## Key Rules

1. **Overridden methods**: Use `self._prev.X` for inputs that come from the
   previous stage (BUILD dependencies). This is the `prev` argument in Nix.

2. **Non-overridden methods** (inherited via MRO): Use `self.X`, which gives
   late binding. The inherited `app` method uses `self.shell` and `self.tools`,
   automatically picking up the current stage's overrides. This is the `final`
   argument in Nix.

3. **Never use `self.X` in an override if X might be overridden by a later stage
   that depends on the attribute you're computing.** That's the cycle.

## Comparison with Other Patterns

The other overlay patterns (B, C, D) don't have this issue because they
explicitly separate `final` and `prev`:

- **B (`__getattr__` chain)**: `overlay_fn(final, prev)` — two explicit args
- **C (lazy fix)**: `overlay(final, prev)` — two explicit args, prev is a dict
- **D (decorator)**: `fn(self, self._prev)` — self = final, _prev = prev

Only the class inheritance pattern (A) required discovering this problem,
because only in OOP is the fixed-point (`self`) an implicit, invisible argument.

## Analogy

Think of it like building a house:
- **prev** = "the tools I have right now" (from the previous stage)
- **final** = "the house I'm building" (the end result)

You can't use the house's plumbing (final.tools) to build the house's
plumbing (final.tools) — that's circular. But you CAN use the old tools
(prev.tools) to build new tools (final.tools), and then the house (final.app)
uses whatever tools ended up in the final result.
