"""Lazy package set with auto-injection.

Python replacement for Nix's callPackage pattern. Define packages as
@cached_property methods on a PackageSet subclass — dependencies are
resolved by parameter name via inspect.signature.

    class MyPkgs(PackageSet):
        @cached_property
        def hello(self):
            return self.call(lambda bash: drv(
                name="hello",
                builder=f"{bash}/bin/bash",
                args=["-c", "echo hello > $out"],
            ))

Each package is computed at most once (@cached_property), matching
Nix's lazy evaluation of attribute sets.
"""

import inspect
from functools import cached_property  # noqa: F401 — re-export for convenience


class PackageSet:
    """Base class for a lazily-evaluated package set.

    Subclass this and define packages as @cached_property methods.
    Use self.call(fn) to auto-inject dependencies by parameter name.
    """

    def call(self, fn):
        """Resolve fn's parameters from this package set and call it.

        Like Nix's callPackage: inspects the function signature and
        looks up each parameter name as an attribute on self.

            self.call(lambda bash, coreutils: drv(...))
            # equivalent to: fn(bash=self.bash, coreutils=self.coreutils)
        """
        sig = inspect.signature(fn)
        kwargs = {}
        for name in sig.parameters:
            if name == "self":
                continue
            if not hasattr(self, name):
                raise AttributeError(
                    f"package set has no attribute {name!r} "
                    f"(required by {fn.__qualname__})"
                )
            kwargs[name] = getattr(self, name)
        return fn(**kwargs)
