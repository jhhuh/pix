"""GNU which — shows the full path of shell commands.

Like nixpkgs/pkgs/by-name/wh/which/package.nix.
Simplest possible mkDerivation package: just stdenv + source, no extra deps.
"""

from pixpkgs.drv import Package
from pixpkgs.mk_derivation import mk_derivation


def make_which(bootstrap_tools: Package, stdenv: Package, src: Package) -> Package:
    bt = str(bootstrap_tools)
    return mk_derivation(
        pname="which",
        version="2.23",
        builder=f"{bt}/bin/bash",
        stdenv=stdenv,
        deps=[bootstrap_tools, src],
        env={
            "NIX_MAIN_PROGRAM": "which",
            "enableParallelBuilding": "1",
            "enableParallelChecking": "1",
            "enableParallelInstalling": "1",
            "src": str(src),
            "strictDeps": "1",
        },
    )
