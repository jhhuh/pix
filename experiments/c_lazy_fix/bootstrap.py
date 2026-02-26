"""3-stage bootstrap using lazy fixed-point computation.

Overlays are plain functions: (final, prev) -> dict of thunks.
Composed via compose_overlays and evaluated via fix.

    base_overlay:   shell, tools(final.shell), app(final.shell, final.tools)
    stage1_overlay: tools = rebuilt with prev.shell
    stage2_overlay: shell = rebuilt with prev.tools
"""

from pixpkgs.drv import drv, Package
from experiments.c_lazy_fix.lazy import fix, compose_overlays


def base_overlay(final, prev) -> dict:
    """Stage 0: bootstrap seed."""
    return {
        "shell": lambda: drv(
            name="shell",
            builder="/bin/sh",
            args=["-c", "echo shell-v0 > $out"],
        ),
        "tools": lambda: drv(
            name="tools",
            builder="/bin/sh",
            args=["-c", f"echo tools-v0-with-{final.shell.name} > $out"],
            deps=[final.shell],
        ),
        "app": lambda: drv(
            name="app",
            builder="/bin/sh",
            args=["-c", f"echo app-with-{final.shell.name}-{final.tools.name} > $out"],
            deps=[final.shell, final.tools],
        ),
    }


def stage1_overlay(final, prev) -> dict:
    """Stage 1: rebuild tools using prev's shell."""
    # prev.shell is a thunk — we need to call it to get the Package.
    # But prev is a dict of thunks, while final is a LazyAttrSet.
    # Access prev["shell"]() for the previous layer's value.
    prev_shell = prev["shell"]
    return {
        "tools": lambda: drv(
            name="tools-v1",
            builder="/bin/sh",
            args=["-c", f"echo tools-v1-rebuilt-with-{prev_shell().name} > $out"],
            deps=[prev_shell()],
        ),
    }


def stage2_overlay(final, prev) -> dict:
    """Stage 2: rebuild shell using prev's tools."""
    prev_tools = prev["tools"]
    return {
        "shell": lambda: drv(
            name="shell-v1",
            builder="/bin/sh",
            args=["-c", f"echo shell-v1-rebuilt-with-{prev_tools().name} > $out"],
            deps=[prev_tools()],
        ),
    }


def make_stage0():
    return fix(compose_overlays([base_overlay]))


def make_stage1():
    return fix(compose_overlays([base_overlay, stage1_overlay]))


def make_stage2():
    return fix(compose_overlays([base_overlay, stage1_overlay, stage2_overlay]))
