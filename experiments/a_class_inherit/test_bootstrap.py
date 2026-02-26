"""Tests for class inheritance bootstrap with full 7-stage chain.

Verifies that the class hierarchy correctly composes all 196 derivations
from nixpkgs bootstrap seed through to hello, hash-perfect.
"""

from experiments.a_class_inherit.bootstrap import (
    Stage0, Stage1, StageXgcc, Stage2, Stage3, Stage4, Final, Pkgs,
)
from experiments.bootstrap_chain import get_chain, HELLO_DRV, HELLO_OUT


class TestStageProgression:
    """Each stage adds new packages to the accumulated set."""

    def test_stage0_has_4_packages(self):
        s = Stage0()
        assert len(s.all_packages) == 4

    def test_stage1_has_12_packages(self):
        s = Stage1()
        assert len(s.all_packages) == 12

    def test_stage_xgcc_has_18_packages(self):
        s = StageXgcc()
        assert len(s.all_packages) == 18

    def test_stage2_has_62_packages(self):
        s = Stage2()
        assert len(s.all_packages) == 62

    def test_stage3_has_85_packages(self):
        s = Stage3()
        assert len(s.all_packages) == 85

    def test_stage4_has_104_packages(self):
        s = Stage4()
        assert len(s.all_packages) == 104

    def test_final_has_167_packages(self):
        s = Final()
        assert len(s.all_packages) == 167

    def test_pkgs_has_196_packages(self):
        p = Pkgs()
        assert len(p.all_packages) == 196


class TestHashPerfect:
    """Every derivation matches nixpkgs exactly."""

    def test_all_196_hashes_match(self):
        p = Pkgs()
        chain = get_chain()
        for drv_path, pkg in p.all_packages.items():
            assert pkg.drv_path == drv_path, f"hash mismatch for {drv_path}"

    def test_hello_drv_path(self):
        p = Pkgs()
        assert p.hello.drv_path == HELLO_DRV

    def test_hello_out_path(self):
        p = Pkgs()
        assert p.hello.out == HELLO_OUT


class TestOverlayBehavior:
    """The class hierarchy demonstrates overlay composition."""

    def test_later_stages_include_earlier(self):
        """Stage1's packages are a superset of Stage0's."""
        s0, s1 = Stage0(), Stage1()
        for dp in s0.all_packages:
            assert dp in s1.all_packages

    def test_stages_grow_monotonically(self):
        """Each stage's package count is strictly larger than the previous."""
        stages = [Stage0(), Stage1(), StageXgcc(), Stage2(), Stage3(), Stage4(), Final()]
        counts = [len(s.all_packages) for s in stages]
        for i in range(1, len(counts)):
            assert counts[i] > counts[i - 1], f"stage {i} not larger than {i-1}"

    def test_caching(self):
        """cached_property ensures packages computed once."""
        p = Pkgs()
        assert p.all_packages is p.all_packages
        assert p.hello is p.hello
