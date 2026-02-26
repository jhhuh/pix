"""zlib — general-purpose compression library.

Like nixpkgs/pkgs/development/libraries/zlib/default.nix.
Multi-output: out, dev, static. Uses stage1 stdenv.
"""

from pixpkgs.drv import Package
from pixpkgs.mk_derivation import mk_derivation


def make_zlib(bootstrap_tools: Package, stdenv: Package, src: Package) -> Package:
    bt = str(bootstrap_tools)
    return mk_derivation(
        pname="zlib",
        version="1.3.1",
        builder=f"{bt}/bin/bash",
        stdenv=stdenv,
        output_names=["dev", "out", "static"],
        deps=[bootstrap_tools, src],
        env={
            "NIX_CFLAGS_COMPILE": "-static-libgcc",
            "configureFlags": "--static --shared",
            "configurePlatforms": "",
            "doCheck": "1",
            "dontAddStaticConfigureFlags": "1",
            "dontConfigure": "",
            "dontDisableStatic": "1",
            "dontStrip": "",
            "enableParallelBuilding": "1",
            "enableParallelChecking": "1",
            "enableParallelInstalling": "1",
            "installFlags": "",
            "makeFlags": "PREFIX= SHARED_MODE=1",
            "outputDoc": "dev",
            "postInstall": 'moveToOutput lib/libz.a "$static"\n',
            "postPatch": "",
            "preConfigure": "",
            "setOutputFlags": "",
            "src": str(src),
            "strictDeps": "1",
        },
    )
