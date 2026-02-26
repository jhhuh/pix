"""Stage 0: Bootstrap seed.

Everything starts from a single prebuilt tarball. Stage0 produces 4
derivations: busybox (for unpacking), the tarball itself, the unpacked
bootstrap-tools, and a dummy stdenv that uses bootstrap-tools as compiler.

Like nixpkgs/pkgs/stdenv/linux/default.nix stage 0.
"""

from functools import cached_property

from pixpkgs.bootstrap.helpers import (
    STAGE0_PREHOOK, TARBALLS_BASE, make_stdenv,
)
from pixpkgs.drv import Package
from pixpkgs.fetchurl import fetchurl
from pixpkgs.package_set import PackageSet
from pixpkgs.pkgs.bootstrap_tools import make_bootstrap_tools
from pixpkgs.vendor import DEFAULT_NATIVE_BUILD_INPUTS


EXPECTED_STAGE0 = {
    "busybox.drv": "/nix/store/0m4y3j4pnivlhhpr5yqdvlly86p93fwc-busybox.drv",
    "busybox.out": "/nix/store/p9wzypb84a60ymqnhqza17ws0dvlyprg-busybox",
    "tarball.drv": "/nix/store/xjkydxc0n24mwxp8kh4wn5jq0fppga9k-bootstrap-tools.tar.xz.drv",
    "tarball.out": "/nix/store/2pizl7lq4awa7p9bklr8037yh1sca0hg-bootstrap-tools.tar.xz",
    "bootstrap_tools.drv": "/nix/store/05q48dcd4lgk4vh7wyk330gr2fr082i2-bootstrap-tools.drv",
    "bootstrap_tools.out": "/nix/store/razasrvdg7ckplfmvdxv4ia3wbayr94s-bootstrap-tools",
    "stdenv.drv": "/nix/store/ydld0fh638kgppqrfx30fr205wiab9ja-bootstrap-stage0-stdenv-linux.drv",
    "stdenv.out": "/nix/store/ajrdf015k5ipn89gyh06isniabysrkcw-bootstrap-stage0-stdenv-linux",
}


class Stage0(PackageSet):
    """Bootstrap seed: busybox, tarball, bootstrap-tools, stdenv (4 packages)."""

    @cached_property
    def busybox(self) -> Package:
        """Statically-linked busybox — the only executable available to unpack."""
        return fetchurl(
            "busybox",
            f"{TARBALLS_BASE}/busybox",
            "42b4c49d04c133563fa95f6876af22ad9910483f6e38c6ecd90e4d802bca08d4",
            recursive=True,
            executable=True,
        )

    @cached_property
    def tarball(self) -> Package:
        """Prebuilt bootstrap-tools tarball (125 binaries + glibc)."""
        return fetchurl(
            "bootstrap-tools.tar.xz",
            f"{TARBALLS_BASE}/bootstrap-tools.tar.xz",
            "61096bd3cf073e8556054da3a4f86920cc8eca81036580f0d72eb448619b50cd",
        )

    @cached_property
    def bootstrap_tools(self) -> Package:
        """Unpacked bootstrap-tools: gcc, coreutils, binutils, bash, etc."""
        return make_bootstrap_tools(self.busybox, self.tarball)

    @cached_property
    def stdenv(self) -> Package:
        """Stage0 stdenv: uses bootstrap-tools as the compiler/shell."""
        bt = str(self.bootstrap_tools)
        return make_stdenv(
            "bootstrap-stage0-stdenv-linux",
            shell=f"{bt}/bin/bash",
            initial_path=bt,
            builder=f"{bt}/bin/bash",
            default_native_build_inputs=DEFAULT_NATIVE_BUILD_INPUTS,
            pre_hook=STAGE0_PREHOOK,
            deps=[self.bootstrap_tools],
        )

    @cached_property
    def all_packages(self) -> dict[str, Package]:
        return {
            self.busybox.drv_path: self.busybox,
            self.tarball.drv_path: self.tarball,
            self.bootstrap_tools.drv_path: self.bootstrap_tools,
            self.stdenv.drv_path: self.stdenv,
        }
