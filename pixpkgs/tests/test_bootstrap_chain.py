"""Tests for pixpkgs bootstrap chain.

Verifies that hand-written package definitions produce derivations
hash-identical to real nixpkgs — without reading .drv files.
"""

from pixpkgs.bootstrap import (
    Stage0, Stage1, StageXgcc,
    EXPECTED_STAGE0, EXPECTED_STAGE1, EXPECTED_STAGE_XGCC,
)


class TestStage0:
    """Stage0: 4 bootstrap seed packages, hash-perfect against nixpkgs."""

    def test_busybox_drv_path(self):
        assert Stage0().busybox.drv_path == EXPECTED_STAGE0["busybox.drv"]

    def test_busybox_out_path(self):
        assert Stage0().busybox.out == EXPECTED_STAGE0["busybox.out"]

    def test_tarball_drv_path(self):
        assert Stage0().tarball.drv_path == EXPECTED_STAGE0["tarball.drv"]

    def test_tarball_out_path(self):
        assert Stage0().tarball.out == EXPECTED_STAGE0["tarball.out"]

    def test_bootstrap_tools_drv_path(self):
        assert Stage0().bootstrap_tools.drv_path == EXPECTED_STAGE0["bootstrap_tools.drv"]

    def test_bootstrap_tools_out_path(self):
        assert Stage0().bootstrap_tools.out == EXPECTED_STAGE0["bootstrap_tools.out"]

    def test_stdenv_drv_path(self):
        assert Stage0().stdenv.drv_path == EXPECTED_STAGE0["stdenv.drv"]

    def test_stdenv_out_path(self):
        assert Stage0().stdenv.out == EXPECTED_STAGE0["stdenv.out"]

    def test_all_packages_has_4(self):
        assert len(Stage0().all_packages) == 4

    def test_caching(self):
        s0 = Stage0()
        assert s0.busybox is s0.busybox
        assert s0.stdenv is s0.stdenv
        assert s0.all_packages is s0.all_packages


class TestStage1:
    """Stage1: 8 new packages (wrappers, gnu-config, hooks), hash-perfect."""

    def test_config_guess_drv_path(self):
        assert Stage1().config_guess.drv_path == EXPECTED_STAGE1["config_guess.drv"]

    def test_config_guess_out_path(self):
        assert Stage1().config_guess.out == EXPECTED_STAGE1["config_guess.out"]

    def test_config_sub_drv_path(self):
        assert Stage1().config_sub.drv_path == EXPECTED_STAGE1["config_sub.drv"]

    def test_config_sub_out_path(self):
        assert Stage1().config_sub.out == EXPECTED_STAGE1["config_sub.out"]

    def test_glibc_bootstrap_files_drv_path(self):
        assert Stage1().glibc_bootstrap_files.drv_path == EXPECTED_STAGE1["glibc_bootstrap_files.drv"]

    def test_glibc_bootstrap_files_out_path(self):
        assert Stage1().glibc_bootstrap_files.out == EXPECTED_STAGE1["glibc_bootstrap_files.out"]

    def test_binutils_wrapper_drv_path(self):
        assert Stage1().binutils_wrapper.drv_path == EXPECTED_STAGE1["binutils_wrapper.drv"]

    def test_binutils_wrapper_out_path(self):
        assert Stage1().binutils_wrapper.out == EXPECTED_STAGE1["binutils_wrapper.out"]

    def test_gnu_config_drv_path(self):
        assert Stage1().gnu_config.drv_path == EXPECTED_STAGE1["gnu_config.drv"]

    def test_gnu_config_out_path(self):
        assert Stage1().gnu_config.out == EXPECTED_STAGE1["gnu_config.out"]

    def test_update_autotools_hook_drv_path(self):
        assert Stage1().update_autotools_hook.drv_path == EXPECTED_STAGE1["update_autotools_hook.drv"]

    def test_update_autotools_hook_out_path(self):
        assert Stage1().update_autotools_hook.out == EXPECTED_STAGE1["update_autotools_hook.out"]

    def test_gcc_wrapper_drv_path(self):
        assert Stage1().gcc_wrapper.drv_path == EXPECTED_STAGE1["gcc_wrapper.drv"]

    def test_gcc_wrapper_out_path(self):
        assert Stage1().gcc_wrapper.out == EXPECTED_STAGE1["gcc_wrapper.out"]

    def test_stdenv_drv_path(self):
        assert Stage1().stdenv.drv_path == EXPECTED_STAGE1["stdenv.drv"]

    def test_stdenv_out_path(self):
        assert Stage1().stdenv.out == EXPECTED_STAGE1["stdenv.out"]

    def test_all_packages_has_12(self):
        assert len(Stage1().all_packages) == 12  # 4 from stage0 + 8 new

    def test_inherits_stage0(self):
        s1 = Stage1()
        assert s1.busybox.drv_path == EXPECTED_STAGE0["busybox.drv"]
        assert s1.bootstrap_tools.drv_path == EXPECTED_STAGE0["bootstrap_tools.drv"]

    def test_caching(self):
        s1 = Stage1()
        assert s1.gcc_wrapper is s1.gcc_wrapper
        assert s1.stdenv is s1.stdenv
        assert s1.all_packages is s1.all_packages


class TestStageXgcc:
    """StageXgcc: 6 new packages (expand-response-params, wrappers), hash-perfect."""

    def test_cc_wrapper_stdenv_drv_path(self):
        assert StageXgcc().cc_wrapper_stdenv.drv_path == EXPECTED_STAGE_XGCC["cc_wrapper_stdenv.drv"]

    def test_cc_wrapper_stdenv_out_path(self):
        assert StageXgcc().cc_wrapper_stdenv.out == EXPECTED_STAGE_XGCC["cc_wrapper_stdenv.out"]

    def test_expand_response_params_drv_path(self):
        assert StageXgcc().expand_response_params.drv_path == EXPECTED_STAGE_XGCC["expand_response_params.drv"]

    def test_expand_response_params_out_path(self):
        assert StageXgcc().expand_response_params.out == EXPECTED_STAGE_XGCC["expand_response_params.out"]

    def test_gnu_config_drv_path(self):
        assert StageXgcc().gnu_config.drv_path == EXPECTED_STAGE_XGCC["gnu_config.drv"]

    def test_gnu_config_out_path(self):
        assert StageXgcc().gnu_config.out == EXPECTED_STAGE_XGCC["gnu_config.out"]

    def test_update_autotools_hook_drv_path(self):
        assert StageXgcc().update_autotools_hook.drv_path == EXPECTED_STAGE_XGCC["update_autotools_hook.drv"]

    def test_update_autotools_hook_out_path(self):
        assert StageXgcc().update_autotools_hook.out == EXPECTED_STAGE_XGCC["update_autotools_hook.out"]

    def test_gcc_wrapper_drv_path(self):
        assert StageXgcc().gcc_wrapper.drv_path == EXPECTED_STAGE_XGCC["gcc_wrapper.drv"]

    def test_gcc_wrapper_out_path(self):
        assert StageXgcc().gcc_wrapper.out == EXPECTED_STAGE_XGCC["gcc_wrapper.out"]

    def test_stdenv_drv_path(self):
        assert StageXgcc().stdenv.drv_path == EXPECTED_STAGE_XGCC["stdenv.drv"]

    def test_stdenv_out_path(self):
        assert StageXgcc().stdenv.out == EXPECTED_STAGE_XGCC["stdenv.out"]

    def test_all_packages_has_18(self):
        assert len(StageXgcc().all_packages) == 18  # 12 from stage1 + 6 new

    def test_inherits_stage1(self):
        sx = StageXgcc()
        assert sx.binutils_wrapper.drv_path == EXPECTED_STAGE1["binutils_wrapper.drv"]
        assert sx.glibc_bootstrap_files.drv_path == EXPECTED_STAGE1["glibc_bootstrap_files.drv"]

    def test_caching(self):
        sx = StageXgcc()
        assert sx.gcc_wrapper is sx.gcc_wrapper
        assert sx.stdenv is sx.stdenv
        assert sx.expand_response_params is sx.expand_response_params
        assert sx.all_packages is sx.all_packages
