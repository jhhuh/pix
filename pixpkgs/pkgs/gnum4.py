"""GNU m4 — macro processor.

Like nixpkgs/pkgs/by-name/gn/gnum4/package.nix.
Uses stage1 stdenv. Single output.
"""

from pixpkgs.drv import Package
from pixpkgs.mk_derivation import mk_derivation


def make_gnum4(bootstrap_tools: Package, stdenv: Package, src: Package) -> Package:
    bt = str(bootstrap_tools)
    return mk_derivation(
        pname="gnum4",
        version="1.4.20",
        builder=f"{bt}/bin/bash",
        stdenv=stdenv,
        deps=[bootstrap_tools, src],
        env={
            "NIX_HARDENING_ENABLE": (
                "bindnow fortify fortify3 libcxxhardeningextensive"
                " libcxxhardeningfast pic relro stackclashprotection"
                " stackprotector strictoverflow zerocallusedregs"
            ),
            "NIX_MAIN_PROGRAM": "m4",
            "configureFlags": f"--with-syscmd-shell={bt}/bin/bash",
            "enableParallelBuilding": "1",
            "enableParallelChecking": "1",
            "enableParallelInstalling": "1",
            "hardeningDisable": "format",
            "postPatch": (
                "substituteInPlace ./build-aux/config.guess"
                " --replace-fail /usr/bin/uname uname\n"
            ),
            "src": str(src),
            "strictDeps": "1",
        },
    )
