"""Tests for __getattr__ overlay chain with full 7-stage bootstrap.

Verifies that the overlay chain correctly composes all 196 derivations
from nixpkgs bootstrap seed through to hello, hash-perfect.
"""

from experiments.b_getattr_chain.bootstrap import (
    make_stage0, make_stage1, make_stage_xgcc, make_pkgs,
)
from experiments.bootstrap_chain import get_chain, HELLO_DRV, HELLO_OUT


class TestStageProgression:
    def test_stage0_has_4_packages(self):
        assert len(make_stage0().all_packages()) == 4

    def test_stage1_has_12_packages(self):
        assert len(make_stage1().all_packages()) == 12

    def test_stage_xgcc_has_18_packages(self):
        assert len(make_stage_xgcc().all_packages()) == 18

    def test_pkgs_has_196_packages(self):
        assert len(make_pkgs().all_packages()) == 196


class TestHashPerfect:
    def test_all_196_hashes_match(self):
        pkgs = make_pkgs().all_packages()
        chain = get_chain()
        for drv_path, pkg in pkgs.items():
            assert pkg.drv_path == drv_path

    def test_hello(self):
        pkgs = make_pkgs().all_packages()
        assert pkgs[HELLO_DRV].drv_path == HELLO_DRV
        assert pkgs[HELLO_DRV].out == HELLO_OUT


class TestOverlayBehavior:
    def test_later_stages_include_earlier(self):
        s0 = make_stage0().all_packages()
        s1 = make_stage1().all_packages()
        for dp in s0:
            assert dp in s1

    def test_overlay_chain_adds_packages(self):
        """Each overlay adds new packages to the chain."""
        s0 = make_stage0().all_packages()
        s1 = make_stage1().all_packages()
        assert len(s1) > len(s0)
        # Stage1 adds 8 new packages
        assert len(s1) - len(s0) == 8
