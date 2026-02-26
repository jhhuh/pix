"""Expand @response-file arguments for compiler wrappers.

Like nixpkgs/pkgs/by-name/ex/expand-response-params/package.nix.
A tiny C99 program that expands @file arguments into actual args.
Used by cc-wrapper and bintools-wrapper scripts.
"""

from pixpkgs.drv import Package
from pixpkgs.mk_derivation import mk_derivation
from pixpkgs.vendor import EXPAND_RESPONSE_PARAMS_C


def make_expand_response_params(
    bootstrap_tools: Package, stdenv: Package,
) -> Package:
    bt = str(bootstrap_tools)
    return mk_derivation(
        name="expand-response-params",
        builder=f"{bt}/bin/bash",
        stdenv=stdenv,
        deps=[bootstrap_tools],
        srcs=[EXPAND_RESPONSE_PARAMS_C],
        env={
            "NIX_MAIN_PROGRAM": "expand-response-params",
            "buildPhase": (
                'NIX_CC_USE_RESPONSE_FILE=0 "$CC" -std=c99 -O3'
                ' -o "expand-response-params" expand-response-params.c\n'
            ),
            "enableParallelBuilding": "1",
            "enableParallelChecking": "1",
            "enableParallelInstalling": "1",
            "installPhase": """\
mkdir -p $prefix/bin
mv expand-response-params $prefix/bin/
""",
            "src": EXPAND_RESPONSE_PARAMS_C,
            "strictDeps": "1",
            "unpackPhase": """\
cp "$src" expand-response-params.c
src=$PWD
""",
        },
    )
