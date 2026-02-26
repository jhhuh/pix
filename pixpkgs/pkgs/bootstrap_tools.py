"""Unpack bootstrap-tools from the prebuilt tarball.

Like nixpkgs/pkgs/stdenv/linux/bootstrap-tools/ — the tarball contains
125 prebuilt binaries (gcc, coreutils, binutils, bash, glibc, etc.).
"""

from pixpkgs.drv import Package, drv
from pixpkgs.vendor import UNPACK_SCRIPT


def make_bootstrap_tools(busybox: Package, tarball: Package) -> Package:
    return drv(
        name="bootstrap-tools",
        builder=str(busybox),
        system="x86_64-linux",
        args=["ash", "-e", UNPACK_SCRIPT],
        deps=[busybox, tarball],
        srcs=[UNPACK_SCRIPT],
        env={
            "hardeningUnsupportedFlags": (
                "fortify3 shadowstack pacret stackclashprotection "
                "trivialautovarinit zerocallusedregs"
            ),
            "isGNU": "1",
            "langC": "1",
            "langCC": "1",
            "tarball": str(tarball),
        },
    )
