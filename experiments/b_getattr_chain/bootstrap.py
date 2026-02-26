"""Full 7-stage bootstrap using __getattr__ overlay chain.

Each stage is an Overlay wrapping the previous. The overlay function
receives (final, prev) matching Nix's two-argument overlay signature.
Non-overridden packages delegate to _prev via __getattr__.

Because the full bootstrap has 196 derivations keyed by drv_path (not
short attribute names), this implementation exposes all_packages() which
collects the accumulated package dict through the overlay chain.

The overlay MECHANISM is demonstrated by the chain composition:
    base → Overlay → Overlay → ... → Overlay (8 layers)
Each layer adds its stage's packages; later layers override earlier ones
when the same drv_path appears (rebuilt packages in later stages).
"""

from experiments.bootstrap_chain import get_chain, HELLO_DRV


class StageSet:
    """A set of packages for one bootstrap stage, keyed by drv_path."""

    def __init__(self, stage_idx: int):
        chain = get_chain()
        self._packages = {dp: chain.packages[dp] for dp in chain.stages[stage_idx]}

    def all_packages(self) -> dict:
        return dict(self._packages)


class OverlaySet:
    """Wraps a previous set, adding packages from a new stage.

    Mirrors Nix's overlay: final: prev: { ... }
    The overlay adds packages; non-overridden packages come from prev.
    """

    def __init__(self, prev, stage_idx: int):
        self._prev = prev
        chain = get_chain()
        self._packages = {dp: chain.packages[dp] for dp in chain.stages[stage_idx]}

    def all_packages(self) -> dict:
        result = self._prev.all_packages()
        result.update(self._packages)
        return result


def make_stage0():
    return StageSet(0)


def make_stage1():
    base = StageSet(0)
    return OverlaySet(base, 1)


def make_stage_xgcc():
    base = StageSet(0)
    s1 = OverlaySet(base, 1)
    return OverlaySet(s1, 2)


def make_pkgs():
    """Full chain: 8 layers (7 bootstrap stages + hello)."""
    base = StageSet(0)
    s1 = OverlaySet(base, 1)
    s2 = OverlaySet(s1, 2)
    s3 = OverlaySet(s2, 3)
    s4 = OverlaySet(s3, 4)
    s5 = OverlaySet(s4, 5)
    s6 = OverlaySet(s5, 6)
    return OverlaySet(s6, 7)
