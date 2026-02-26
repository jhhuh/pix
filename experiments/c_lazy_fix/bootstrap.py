"""Full 7-stage bootstrap using lazy fixed-point computation.

Each stage is an overlay function: (final, prev) -> dict of thunks.
Composed via compose_overlays and evaluated via fix. This is the closest
translation of Nix's lib.fix + lib.composeExtensions.

    base_overlay: defines stage0 packages
    stage1_overlay: adds stage1 packages
    ...
    result = fix(compose_overlays([base, s1, s2, ..., hello]))

All 196 derivations are reconstructed from .drv files and grouped by
bootstrap stage via closure set-differences.
"""

from experiments.c_lazy_fix.lazy import fix, compose_overlays
from experiments.bootstrap_chain import get_chain, HELLO_DRV


def _make_overlay(stage_idx):
    """Create an overlay function for a stage.

    Returns: (final, prev) -> dict of thunks {drv_path: lambda: Package}
    """
    def overlay(final, prev):
        chain = get_chain()
        return {
            dp: (lambda _dp=dp: lambda: chain.packages[_dp])()
            for dp in chain.stages[stage_idx]
        }
    return overlay


# 8 overlay functions (7 bootstrap stages + hello)
base_overlay = _make_overlay(0)
stage1_overlay = _make_overlay(1)
stage_xgcc_overlay = _make_overlay(2)
stage2_overlay = _make_overlay(3)
stage3_overlay = _make_overlay(4)
stage4_overlay = _make_overlay(5)
final_overlay = _make_overlay(6)
hello_overlay = _make_overlay(7)


def make_stage0():
    return fix(compose_overlays([base_overlay]))


def make_stage1():
    return fix(compose_overlays([base_overlay, stage1_overlay]))


def make_stage_xgcc():
    return fix(compose_overlays([base_overlay, stage1_overlay, stage_xgcc_overlay]))


def make_pkgs():
    """Full chain: all 8 overlays composed into one fixed point."""
    return fix(compose_overlays([
        base_overlay,
        stage1_overlay,
        stage_xgcc_overlay,
        stage2_overlay,
        stage3_overlay,
        stage4_overlay,
        final_overlay,
        hello_overlay,
    ]))


def all_packages(lazy_set) -> dict:
    """Force all thunks and collect packages from a LazyAttrSet.

    Since our attribute names are drv_paths (not valid Python identifiers),
    we access the thunks dict directly.
    """
    thunks = object.__getattribute__(lazy_set, '_thunks')
    cache = object.__getattribute__(lazy_set, '_cache')
    result = {}
    for key in thunks:
        if key in cache:
            result[key] = cache[key]
        else:
            result[key] = thunks[key]()
    return result
