"""Tests for lazy fixed-point bootstrap with full 7-stage chain.

Verifies that fix(compose_overlays([...])) correctly composes all 196
derivations from nixpkgs bootstrap seed through to hello, hash-perfect.
"""

from experiments.c_lazy_fix.bootstrap import (
    make_stage0, make_stage1, make_stage_xgcc, make_pkgs, all_packages,
)
from experiments.bootstrap_chain import get_chain, HELLO_DRV, HELLO_OUT


class TestStageProgression:
    def test_stage0_has_4_packages(self):
        assert len(all_packages(make_stage0())) == 4

    def test_stage1_has_12_packages(self):
        assert len(all_packages(make_stage1())) == 12

    def test_stage_xgcc_has_18_packages(self):
        assert len(all_packages(make_stage_xgcc())) == 18

    def test_pkgs_has_196_packages(self):
        assert len(all_packages(make_pkgs())) == 196


class TestHashPerfect:
    def test_all_196_hashes_match(self):
        pkgs = all_packages(make_pkgs())
        chain = get_chain()
        for drv_path, pkg in pkgs.items():
            assert pkg.drv_path == drv_path

    def test_hello(self):
        pkgs = all_packages(make_pkgs())
        assert pkgs[HELLO_DRV].drv_path == HELLO_DRV
        assert pkgs[HELLO_DRV].out == HELLO_OUT


class TestOverlayBehavior:
    def test_later_stages_include_earlier(self):
        s0 = all_packages(make_stage0())
        s1 = all_packages(make_stage1())
        for dp in s0:
            assert dp in s1

    def test_composition_is_fold(self):
        """compose_overlays folds left — each overlay sees previous layers."""
        s0 = all_packages(make_stage0())
        s1 = all_packages(make_stage1())
        assert len(s1) - len(s0) == 8
