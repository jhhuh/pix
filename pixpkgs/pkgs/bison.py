"""bison — GNU parser generator (yacc replacement).

Like nixpkgs/pkgs/by-name/bi/bison/package.nix.
Uses stage1 stdenv. Single output.

nativeBuildInputs: gnum4 + perl.
propagatedBuildInputs: gnum4 (so downstream packages can use m4 macros).
enableParallelBuilding=true, doInstallCheck=true.

configurePlatforms = ["build" "host"] adds --build/--host flags to
configureFlags even for native builds. This is unlike most packages
which default to empty configurePlatforms for native builds.
"""

from pixpkgs.drv import Package
from pixpkgs.mk_derivation import mk_derivation


def make_bison(
    bootstrap_tools: Package,
    stdenv: Package,
    src: Package,
    gnum4: Package,
    perl: Package,
) -> Package:
    bt = str(bootstrap_tools)
    return mk_derivation(
        pname="bison",
        version="3.8.2",
        builder=f"{bt}/bin/bash",
        stdenv=stdenv,
        deps=[bootstrap_tools, src, gnum4, perl],
        # perl has 3 outputs but bison only needs "out"
        input_drvs={perl.drv_path: ["out"]},
        env={
            "configurePlatforms": "build host",
            "configureFlags": (
                "--build=x86_64-unknown-linux-gnu"
                " --host=x86_64-unknown-linux-gnu"
            ),
            "doInstallCheck": "1",
            "enableParallelBuilding": "1",
            "enableParallelChecking": "1",
            "enableParallelInstalling": "1",
            "nativeBuildInputs": f"{gnum4} {perl}",
            "propagatedBuildInputs": str(gnum4),
            "src": str(src),
            "strictDeps": "",
        },
    )
