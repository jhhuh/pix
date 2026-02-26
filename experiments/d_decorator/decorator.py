"""Overlay pattern via class decorators.

Direct translation of Nix's overlay chain: each overlay is a decorator
that wraps a PackageSet class, adding or replacing @cached_property
methods. The decorator dynamically creates a subclass.

    @overlay(tools=lambda self, prev: mk("tools-v1", deps=[prev.shell]))
    class Stage1(Stage0): pass

This is equivalent to:
    overlay = final: prev: { tools = mkTools { shell = prev.shell; }; };

The decorator pattern combines the readability of class inheritance
with the dynamic composability of the __getattr__ approach.
"""

from functools import cached_property


def overlay(**overrides):
    """Class decorator that applies an overlay to a PackageSet class.

    Each keyword argument is a function(self, prev) -> Package, where:
        self = the instance (final — late-bound via Python's MRO)
        prev = a separate instance of the base class (previous stage)

    The decorator creates a new subclass with @cached_property for
    each override, plus a _prev cached_property for the base class.

    Usage:
        @overlay(
            tools=lambda self, prev: mk("tools-v1", deps=[prev.shell]),
        )
        class Stage1(Stage0): pass
    """
    def decorator(cls):
        # Build a dict of new class attributes
        attrs = {}

        # Add _prev that instantiates the base class
        base = cls.__bases__[0] if cls.__bases__ else cls
        attrs['_prev'] = cached_property(lambda self, _b=base: _b())

        # Add each override as a @cached_property
        for name, fn in overrides.items():
            # fn(self, prev) -> Package
            # We wrap it to call fn(self, self._prev)
            def make_prop(f):
                def prop(self):
                    return f(self, self._prev)
                prop.__name__ = name
                return cached_property(prop)
            attrs[name] = make_prop(fn)

        # Create a new class that inherits from cls with the overrides
        return type(cls.__name__, (cls,), attrs)

    return decorator
