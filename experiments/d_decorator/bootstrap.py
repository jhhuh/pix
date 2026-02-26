"""3-stage bootstrap using class decorators.

The @overlay decorator dynamically creates subclasses with overridden
@cached_property methods. Combines inheritance's late binding with
the dynamic composability of overlays.

    Stage0: base class with shell, tools, app
    Stage1 = @overlay(tools=...)(Stage0)
    Stage2 = @overlay(shell=...)(Stage1)
"""

from functools import cached_property

from pixpkgs.drv import drv, Package
from experiments.d_decorator.decorator import overlay
from experiments.a_class_inherit.pkgset import PackageSet


class Stage0(PackageSet):
    """Bootstrap seed."""

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
        return drv(
            name="app",
            builder="/bin/sh",
            args=["-c", f"echo app-with-{self.shell.name}-{self.tools.name} > $out"],
            deps=[self.shell, self.tools],
        )


@overlay(
    tools=lambda self, prev: drv(
        name="tools-v1",
        builder="/bin/sh",
        args=["-c", f"echo tools-v1-rebuilt-with-{prev.shell.name} > $out"],
        deps=[prev.shell],
    ),
)
class Stage1(Stage0):
    """Stage 1: rebuild tools using prev's shell."""
    pass


@overlay(
    shell=lambda self, prev: drv(
        name="shell-v1",
        builder="/bin/sh",
        args=["-c", f"echo shell-v1-rebuilt-with-{prev.tools.name} > $out"],
        deps=[prev.tools],
    ),
)
class Stage2(Stage1):
    """Stage 2: rebuild shell using prev's tools."""
    pass
