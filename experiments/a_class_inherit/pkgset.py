"""Overlay pattern via class inheritance.

The insight: Python's `self` IS the fixed point. Method override IS
the overlay mechanism. `super()` IS `prev`. This is the simplest
mapping of Nix's overlay/bootstrap pattern to Python.

    class Stage0(PackageSet):
        @cached_property
        def gcc(self): return bootstrap_gcc

        @cached_property
        def hello(self):
            # self.gcc is late-bound — resolved on the ACTUAL instance
            return mk("hello", deps=[self.gcc])

    class Stage1(Stage0):
        @cached_property
        def gcc(self):
            # Rebuild gcc. super() = prev stage, self = final stage.
            return mk("gcc-v1", deps=[super().binutils])

    # Stage1().hello uses Stage1.gcc, not Stage0.gcc.
    # This is open recursion via Python's MRO.
"""

import inspect
from functools import cached_property


class PackageSet:
    """Base class for lazy, overridable package sets.

    Subclass and define packages as @cached_property methods.
    Use self.call(fn) for auto-dependency injection (callPackage).
    """

    def call(self, fn):
        """Resolve fn's parameter names from this package set.

        Like Nix's callPackage: inspects fn's signature, looks up each
        parameter name as an attribute of self, and calls fn with them.
        """
        sig = inspect.signature(fn)
        kwargs = {}
        for name in sig.parameters:
            if name == "self":
                continue
            kwargs[name] = getattr(self, name)
        return fn(**kwargs)
