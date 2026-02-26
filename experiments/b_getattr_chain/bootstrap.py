"""3-stage bootstrap using __getattr__ overlay chain.

Each overlay is a function(final, prev) -> dict of thunks.
Thunks are callable(final) -> Package, evaluated lazily.

    base:   shell, tools(shell), app(shell, tools)
    stage1: tools = rebuilt with prev.shell
    stage2: shell = rebuilt with prev.tools
"""

from pixpkgs.drv import drv, Package
from experiments.b_getattr_chain.overlay import AttrSet, Overlay


def make_base() -> AttrSet:
    """Stage 0: bootstrap seed."""
    return AttrSet({
        "shell": lambda final: drv(
            name="shell",
            builder="/bin/sh",
            args=["-c", "echo shell-v0 > $out"],
        ),
        "tools": lambda final: drv(
            name="tools",
            builder="/bin/sh",
            args=["-c", f"echo tools-v0-with-{final.shell.name} > $out"],
            deps=[final.shell],
        ),
        "app": lambda final: drv(
            name="app",
            builder="/bin/sh",
            args=["-c", f"echo app-with-{final.shell.name}-{final.tools.name} > $out"],
            deps=[final.shell, final.tools],
        ),
    })


def stage1_overlay(final, prev) -> dict:
    """Stage 1: rebuild tools using prev's shell."""
    return {
        "tools": lambda final: drv(
            name="tools-v1",
            builder="/bin/sh",
            args=["-c", f"echo tools-v1-rebuilt-with-{prev.shell.name} > $out"],
            deps=[prev.shell],
        ),
    }


def stage2_overlay(final, prev) -> dict:
    """Stage 2: rebuild shell using prev's tools."""
    return {
        "shell": lambda final: drv(
            name="shell-v1",
            builder="/bin/sh",
            args=["-c", f"echo shell-v1-rebuilt-with-{prev.tools.name} > $out"],
            deps=[prev.tools],
        ),
    }


def make_stage0():
    base = make_base()
    base._set_final(base)
    return base


def make_stage1():
    base = make_base()
    s1 = Overlay(base, stage1_overlay)
    s1._set_final(s1)
    return s1


def make_stage2():
    base = make_base()
    s1 = Overlay(base, stage1_overlay)
    s2 = Overlay(s1, stage2_overlay)
    s2._set_final(s2)
    return s2
