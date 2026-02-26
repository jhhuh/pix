"""Symlink proxy exposing glibc headers/libs from bootstrap-tools.

Like nixpkgs/pkgs/stdenv/linux/default.nix stage 0 override for ${libc}.
Creates a separate prefix so GCC doesn't confuse its own headers with
glibc headers (they can't share the same prefix).
"""

from pixpkgs.drv import Package
from pixpkgs.mk_derivation import mk_derivation


def make_glibc_bootstrap_files(
    bootstrap_tools: Package, stdenv: Package,
) -> Package:
    bt = str(bootstrap_tools)
    return mk_derivation(
        pname="bootstrap-stage0-glibc",
        version="bootstrapFiles",
        builder=f"{bt}/bin/bash",
        stdenv=stdenv,
        deps=[bootstrap_tools],
        env={
            "buildCommand": f"""\
mkdir -p $out
ln -s {bt}/lib $out/lib
ln -s {bt}/include-glibc $out/include
""",
            "enableParallelBuilding": "1",
            "enableParallelChecking": "1",
            "enableParallelInstalling": "1",
            "strictDeps": "1",
        },
    )
