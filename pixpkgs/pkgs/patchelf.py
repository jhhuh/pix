"""patchelf — modify ELF executables.

Like nixpkgs/pkgs/development/tools/misc/patchelf/default.nix.
Uses stage1 stdenv. Single output. Has a setup-hook.
"""

from pixpkgs.drv import Package
from pixpkgs.mk_derivation import mk_derivation
from pixpkgs.vendor import PATCHELF_SETUP_HOOK


def make_patchelf(bootstrap_tools: Package, stdenv: Package, src: Package) -> Package:
    bt = str(bootstrap_tools)
    return mk_derivation(
        pname="patchelf",
        version="0.15.2",
        builder=f"{bt}/bin/bash",
        stdenv=stdenv,
        deps=[bootstrap_tools, src],
        srcs=[PATCHELF_SETUP_HOOK],
        env={
            "NIX_MAIN_PROGRAM": "patchelf",
            "enableParallelBuilding": "1",
            "enableParallelChecking": "1",
            "enableParallelInstalling": "1",
            "setupHook": PATCHELF_SETUP_HOOK,
            "src": str(src),
            "strictDeps": "1",
        },
    )
