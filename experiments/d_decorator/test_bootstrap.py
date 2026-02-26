"""Tests for decorator bootstrap with full 7-stage chain.

Verifies that the @stage_overlay decorator correctly composes all 196
derivations from nixpkgs bootstrap seed through to hello, hash-perfect.
"""

from experiments.d_decorator.bootstrap import (
    Stage0, Stage1, StageXgcc, Stage2, Stage3, Stage4, Final, Pkgs,
)
from experiments.bootstrap_chain import get_chain, HELLO_DRV, HELLO_OUT


class TestStageProgression:
    def test_stage0_has_4_packages(self):
        assert len(Stage0().all_packages) == 4

    def test_stage1_has_12_packages(self):
        assert len(Stage1().all_packages) == 12

    def test_stage_xgcc_has_18_packages(self):
        assert len(StageXgcc().all_packages) == 18

    def test_stage2_has_62_packages(self):
        assert len(Stage2().all_packages) == 62

    def test_stage3_has_85_packages(self):
        assert len(Stage3().all_packages) == 85

    def test_stage4_has_104_packages(self):
        assert len(Stage4().all_packages) == 104

    def test_final_has_167_packages(self):
        assert len(Final().all_packages) == 167

    def test_pkgs_has_196_packages(self):
        assert len(Pkgs().all_packages) == 196


class TestHashPerfect:
    def test_all_196_hashes_match(self):
        p = Pkgs()
        chain = get_chain()
        for drv_path, pkg in p.all_packages.items():
            assert pkg.drv_path == drv_path

    def test_hello_drv_path(self):
        assert Pkgs().hello.drv_path == HELLO_DRV

    def test_hello_out_path(self):
        assert Pkgs().hello.out == HELLO_OUT


class TestOverlayBehavior:
    def test_later_stages_include_earlier(self):
        s0 = Stage0().all_packages
        s1 = Stage1().all_packages
        for dp in s0:
            assert dp in s1

    def test_decorator_adds_packages(self):
        s0 = Stage0().all_packages
        s1 = Stage1().all_packages
        assert len(s1) - len(s0) == 8

    def test_caching(self):
        p = Pkgs()
        assert p.all_packages is p.all_packages
        assert p.hello is p.hello
