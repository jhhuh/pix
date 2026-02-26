"""3-stage bootstrap using class inheritance.

Key insight: Nix overlays take both `final` and `prev`:
    overlay = final: prev: { tools = mkTools { shell = prev.shell; }; };

In class inheritance:
    self      = final  (late-bound, sees current stage's overrides)
    self._prev = prev   (previous stage, breaks cycles)

Overridden packages use `self._prev.attr` for BUILD dependencies
(to avoid circular deps). Non-overridden packages use `self.attr`
and automatically pick up the current stage's overrides (open recursion).

    Stage0  →  Stage1 (override tools, build with prev.shell)
            →  Stage2 (override shell, build with prev.tools)
"""

from functools import cached_property

from pixpkgs.drv import drv, Package
from experiments.a_class_inherit.pkgset import PackageSet


class Stage0(PackageSet):
    """Bootstrap seed. All packages are built from scratch with /bin/sh."""

    @cached_property
    def shell(self) -> Package:
        return drv(
            name="shell",
            builder="/bin/sh",
            args=["-c", "echo shell-v0 > $out"],
        )

    @cached_property
    def tools(self) -> Package:
        return drv(
            name="tools",
            builder="/bin/sh",
            args=["-c", f"echo tools-v0-with-{self.shell.name} > $out"],
            deps=[self.shell],
        )

    @cached_property
    def app(self) -> Package:
        """Application that depends on shell and tools.

        Uses self.shell and self.tools (late-bound). When a subclass
        overrides shell or tools, this method automatically picks up
        the new versions — open recursion via Python's MRO.
        """
        return drv(
            name="app",
            builder="/bin/sh",
            args=["-c", f"echo app-with-{self.shell.name}-{self.tools.name} > $out"],
            deps=[self.shell, self.tools],
        )


class Stage1(Stage0):
    """Rebuild tools using stage0's shell.

    self._prev = Stage0 instance (the previous stage).
    Overridden tools uses self._prev.shell to avoid the cycle
    that would occur if it used self.shell (which may be overridden
    in a later stage that depends on self.tools).
    """

    @cached_property
    def _prev(self) -> Stage0:
        return Stage0()

    @cached_property
    def tools(self) -> Package:
        # Build with prev's shell — mirrors Nix overlay pattern
        return drv(
            name="tools-v1",
            builder="/bin/sh",
            args=["-c", f"echo tools-v1-rebuilt-with-{self._prev.shell.name} > $out"],
            deps=[self._prev.shell],
        )


class Stage2(Stage1):
    """Rebuild shell using stage1's tools.

    self._prev = Stage1 instance.
    Overridden shell uses self._prev.tools to avoid cycles.
    tools is inherited from Stage1 — NOT rebuilt.
    """

    @cached_property
    def _prev(self) -> Stage1:
        return Stage1()

    @cached_property
    def shell(self) -> Package:
        # Build with prev's tools — mirrors Nix overlay pattern
        return drv(
            name="shell-v1",
            builder="/bin/sh",
            args=["-c", f"echo shell-v1-rebuilt-with-{self._prev.tools.name} > $out"],
            deps=[self._prev.tools],
        )
