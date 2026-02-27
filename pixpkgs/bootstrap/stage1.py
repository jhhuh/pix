"""Stage 1: First "real" standard environment.

Creates wrappers around the bootstrap-tools compiler and linker, plus
GNU config scripts for autotools-based builds. This is the first stage
that has a "real" cc-wrapper with proper nix-support files.

Like nixpkgs/pkgs/stdenv/linux/default.nix stage 1:
  - glibc-bootstrapFiles: symlink proxy to bootstrap-tools glibc
  - binutils-wrapper: wraps bootstrap-tools ld/ar/nm/etc.
  - gcc-wrapper: wraps bootstrap-tools gcc/g++/cpp
  - gnu-config: config.guess + config.sub for platform detection
  - update-autotools-hook: setup hook to update stale config scripts
  - stage1-stdenv: stdenv with gcc-wrapper and hooks

Packages compiled with stage1 stdenv (for use in later stages):
  - which, zlib, gnum4, patchelf, perl, bison, bash
"""

from functools import cached_property

from pixpkgs.bootstrap.helpers import (
    GNU_CONFIG_BASE, GNU_CONFIG_COMMIT, STAGE0_PREHOOK, make_stdenv,
)
from pixpkgs.bootstrap.sources import (
    bash_patch_001, bash_patch_002, bash_patch_003, bash_src,
    bison_src, m4_src, patchelf_src, perl_src, which_src, zlib_src,
)
from pixpkgs.bootstrap.stage0 import Stage0
from pixpkgs.drv import Package
from pixpkgs.fetchurl import fetchurl
from pixpkgs.pkgs.bash import make_bash
from pixpkgs.pkgs.bintools_wrapper import make_binutils_wrapper
from pixpkgs.pkgs.bison import make_bison
from pixpkgs.pkgs.cc_wrapper import make_gcc_wrapper
from pixpkgs.pkgs.glibc_bootstrap import make_glibc_bootstrap_files
from pixpkgs.pkgs.gnum4 import make_gnum4
from pixpkgs.pkgs.gnu_config import make_gnu_config
from pixpkgs.pkgs.patchelf import make_patchelf
from pixpkgs.pkgs.perl import make_perl
from pixpkgs.pkgs.update_autotools import make_update_autotools_hook
from pixpkgs.pkgs.which import make_which
from pixpkgs.pkgs.zlib import make_zlib
from pixpkgs.vendor import DEFAULT_NATIVE_BUILD_INPUTS


EXPECTED_STAGE1 = {
    "config_guess.drv": "/nix/store/bamwxswxacs3cjdcydv0z7bj22d7g2kc-config.guess-948ae97.drv",
    "config_guess.out": "/nix/store/vq0j27nvpks679djbiykl8ikdyj6z5a9-config.guess-948ae97",
    "config_sub.drv": "/nix/store/nbsdqpfzh1jlpmh95s69b3iivfcvv3lh-config.sub-948ae97.drv",
    "config_sub.out": "/nix/store/1p61qjvlqmwrqab3zp5yh3z8rf3mvjmz-config.sub-948ae97",
    "glibc_bootstrap_files.drv": "/nix/store/swcark68dhh8qx8jnq6xjs2siakw5ggz-bootstrap-stage0-glibc-bootstrapFiles.drv",
    "glibc_bootstrap_files.out": "/nix/store/vwfprzg8aimy7mfjyn9qcj1swk0f0i82-bootstrap-stage0-glibc-bootstrapFiles",
    "binutils_wrapper.drv": "/nix/store/9khsa6l6wxk1rqlhmgmlhmm002nsx8fn-bootstrap-stage0-binutils-wrapper-.drv",
    "binutils_wrapper.out": "/nix/store/zq3ghlkzyr8rcxq2ajbrvrnccqzflmwf-bootstrap-stage0-binutils-wrapper-",
    "gnu_config.drv": "/nix/store/bhbpzhiqjrnmb3jxzya8cx5wci0f6fkp-gnu-config-2024-01-01.drv",
    "gnu_config.out": "/nix/store/nkp2jjfx646f1brf8mbyn6ypagxks2vi-gnu-config-2024-01-01",
    "update_autotools_hook.drv": "/nix/store/zgb9kik3lxh6yz3nhl2pjhzpqxhaf301-update-autotools-gnu-config-scripts-hook.drv",
    "update_autotools_hook.out": "/nix/store/ivs0ximaj8m0dgakfd87cd9s466s2r2i-update-autotools-gnu-config-scripts-hook",
    "gcc_wrapper.drv": "/nix/store/0mbanw6inqr1ybpqr70ass09c445amf2-bootstrap-stage1-gcc-wrapper-.drv",
    "gcc_wrapper.out": "/nix/store/9lvmgjwhra5s9swb1v0mfb4i6kb8wvjk-bootstrap-stage1-gcc-wrapper-",
    "stdenv.drv": "/nix/store/df3ibqm3m62scbv1j0yahsrydfhmdslj-bootstrap-stage1-stdenv-linux.drv",
    "stdenv.out": "/nix/store/w0yz7fjnrh47chamv5mmadnk7k289lbq-bootstrap-stage1-stdenv-linux",
}


class Stage1(Stage0):
    """First real stdenv: wraps bootstrap-tools with proper nix-support files.

    Adds 8 packages: glibc-bootstrapFiles, binutils-wrapper, gcc-wrapper,
    config.guess, config.sub, gnu-config, update-autotools-hook, stage1-stdenv.
    """

    @cached_property
    def _prev(self) -> Stage0:
        return Stage0()

    # --- fetchurl sources ---

    @cached_property
    def config_guess(self) -> Package:
        """GNU config.guess for platform detection."""
        return fetchurl(
            "config.guess-948ae97",
            f"{GNU_CONFIG_BASE}/config.guess?id={GNU_CONFIG_COMMIT}",
            "641cae3c0c74c49354d3ede009f3febd80febe1501a77c1d9fac8d42cc45b6cb",
        )

    @cached_property
    def config_sub(self) -> Package:
        """GNU config.sub for platform detection."""
        return fetchurl(
            "config.sub-948ae97",
            f"{GNU_CONFIG_BASE}/config.sub?id={GNU_CONFIG_COMMIT}",
            "fe3a2f32fbaff57848732549f48d983fd6526024ec2f0f5a9dc75c2f4359a3a6",
        )

    # --- stage1 packages ---

    @cached_property
    def glibc_bootstrap_files(self) -> Package:
        """Symlink proxy exposing bootstrap-tools glibc headers/libs."""
        return make_glibc_bootstrap_files(
            self._prev.bootstrap_tools, self._prev.stdenv,
        )

    @cached_property
    def binutils_wrapper(self) -> Package:
        """Wrapped binutils (ld, ar, nm, strip, etc.)."""
        return make_binutils_wrapper(
            self._prev.bootstrap_tools, self.glibc_bootstrap_files,
            self._prev.stdenv,
        )

    @cached_property
    def gnu_config(self) -> Package:
        """GNU config scripts (config.guess + config.sub)."""
        return make_gnu_config(
            self.config_guess, self.config_sub,
            self._prev.bootstrap_tools, self._prev.stdenv,
        )

    @cached_property
    def update_autotools_hook(self) -> Package:
        """Setup hook: updates stale config.guess/config.sub in packages."""
        return make_update_autotools_hook(
            self.gnu_config, self._prev.bootstrap_tools, self._prev.stdenv,
        )

    @cached_property
    def gcc_wrapper(self) -> Package:
        """Wrapped GCC (gcc, g++, cpp) with nix-support files."""
        return make_gcc_wrapper(
            self._prev.bootstrap_tools, self.binutils_wrapper,
            self.glibc_bootstrap_files, self._prev.stdenv,
        )

    @cached_property
    def stdenv(self) -> Package:
        """Stage1 stdenv: uses gcc-wrapper and update-autotools hook."""
        bt = str(self._prev.bootstrap_tools)
        gcc_w = str(self.gcc_wrapper)
        hook = str(self.update_autotools_hook)
        return make_stdenv(
            "bootstrap-stage1-stdenv-linux",
            shell=f"{bt}/bin/bash",
            initial_path=bt,
            builder=f"{bt}/bin/bash",
            default_native_build_inputs=" ".join([
                hook,
                *DEFAULT_NATIVE_BUILD_INPUTS.split(),
                gcc_w,
            ]),
            pre_hook=STAGE0_PREHOOK,
            deps=[
                self._prev.bootstrap_tools,
                self.gcc_wrapper,
                self.update_autotools_hook,
            ],
        )

    # --- Packages compiled with stage1 stdenv ---
    # These are used by the xgcc stage and later. In nixpkgs, they come
    # from evaluating ALL of nixpkgs with stage1's stdenv. Here we only
    # build the ones needed for the bootstrap chain.

    @cached_property
    def which(self) -> Package:
        return make_which(self._prev.bootstrap_tools, self.stdenv, which_src())

    @cached_property
    def zlib(self) -> Package:
        return make_zlib(self._prev.bootstrap_tools, self.stdenv, zlib_src())

    @cached_property
    def gnum4(self) -> Package:
        return make_gnum4(self._prev.bootstrap_tools, self.stdenv, m4_src())

    @cached_property
    def patchelf(self) -> Package:
        return make_patchelf(self._prev.bootstrap_tools, self.stdenv, patchelf_src())

    @cached_property
    def perl(self) -> Package:
        return make_perl(
            self._prev.bootstrap_tools, self.stdenv, perl_src(),
            self.zlib, self.glibc_bootstrap_files, self.gcc_wrapper,
        )

    @cached_property
    def bison(self) -> Package:
        return make_bison(
            self._prev.bootstrap_tools, self.stdenv, bison_src(),
            self.gnum4, self.perl,
        )

    @cached_property
    def bash(self) -> Package:
        return make_bash(
            bootstrap_tools=self._prev.bootstrap_tools,
            stdenv=self.stdenv,
            src=bash_src(),
            bash_patch_001=bash_patch_001(),
            bash_patch_002=bash_patch_002(),
            bash_patch_003=bash_patch_003(),
            gcc_wrapper=self.gcc_wrapper,
            update_autotools_hook=self.update_autotools_hook,
            bison=self.bison,
        )

    @cached_property
    def all_packages(self) -> dict[str, Package]:
        own = {
            self.config_guess.drv_path: self.config_guess,
            self.config_sub.drv_path: self.config_sub,
            self.glibc_bootstrap_files.drv_path: self.glibc_bootstrap_files,
            self.binutils_wrapper.drv_path: self.binutils_wrapper,
            self.gnu_config.drv_path: self.gnu_config,
            self.update_autotools_hook.drv_path: self.update_autotools_hook,
            self.gcc_wrapper.drv_path: self.gcc_wrapper,
            self.stdenv.drv_path: self.stdenv,
            self.which.drv_path: self.which,
            self.zlib.drv_path: self.zlib,
            self.gnum4.drv_path: self.gnum4,
            self.patchelf.drv_path: self.patchelf,
            self.perl.drv_path: self.perl,
            self.bison.drv_path: self.bison,
            self.bash.drv_path: self.bash,
        }
        return {**self._prev.all_packages, **own}
