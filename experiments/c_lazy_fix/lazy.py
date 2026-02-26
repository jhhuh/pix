"""Overlay pattern via lazy fixed-point computation.

Direct translation of Nix's lib.fix and lib.composeExtensions:

    Nix:    fix (self: { a = 1; b = self.a + 1; })
    Python: fix(lambda self: {"a": lambda: 1, "b": lambda: self.a + 1})

    Nix:    lib.composeExtensions overlay1 overlay2
    Python: compose_overlays([overlay1, overlay2])

The LazyAttrSet is the fixed-point value. Attribute access triggers
lazy evaluation (thunk forcing) with memoization. The `self` argument
to overlay functions IS the fixed-point (final result), enabling
open recursion.

Overlays are functions: (final, prev) -> dict of thunks
    final: the completed fixed-point set (LazyAttrSet)
    prev:  dict of thunks from previous layers
"""


class LazyAttrSet:
    """Lazy attribute set with memoized thunk evaluation.

    Each attribute is a thunk (zero-arg callable). On first access,
    the thunk is called and the result cached.
    """

    def __init__(self):
        object.__setattr__(self, '_thunks', {})
        object.__setattr__(self, '_cache', {})
        object.__setattr__(self, '_evaluating', set())

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        cache = object.__getattribute__(self, '_cache')
        if name in cache:
            return cache[name]
        thunks = object.__getattribute__(self, '_thunks')
        if name not in thunks:
            raise AttributeError(f"no package '{name}'")
        evaluating = object.__getattribute__(self, '_evaluating')
        if name in evaluating:
            raise RecursionError(
                f"infinite recursion evaluating '{name}' "
                f"(currently evaluating: {evaluating})"
            )
        evaluating.add(name)
        try:
            result = thunks[name]()
            cache[name] = result
            return result
        finally:
            evaluating.discard(name)


def fix(f):
    """Compute the fixed point of f.

    f is a function that takes the final result (LazyAttrSet) and
    returns a dict of thunks (name -> zero-arg callable).

    This mirrors Nix's lib.fix:
        fix = f: let x = f x; in x

    The LazyAttrSet `result` is passed to `f` before any thunks
    are evaluated. When a thunk accesses result.attr, it triggers
    lazy evaluation of that attr's thunk — which may in turn access
    other attrs. This is open recursion.
    """
    result = LazyAttrSet()
    thunks = f(result)
    object.__setattr__(result, '_thunks', thunks)
    return result


def compose_overlays(overlays):
    """Compose a list of overlay functions into a single function for fix().

    Each overlay is: (final, prev) -> dict of thunks
    The composed function folds left: each overlay sees all previous
    layers merged as `prev`.

    Mirrors Nix's lib.composeExtensions (for a list of overlays).
    """
    def composed(final):
        prev = {}
        for overlay in overlays:
            layer = overlay(final, prev)
            prev = {**prev, **layer}
        return prev
    return composed
