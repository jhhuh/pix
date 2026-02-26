"""GNU config scripts (config.guess, config.sub) for platform detection.

Like nixpkgs/pkgs/by-name/gn/gnu-config/package.nix.
"""

from pixpkgs.drv import Package
from pixpkgs.mk_derivation import mk_derivation


def make_gnu_config(
    config_guess: Package, config_sub: Package,
    bootstrap_tools: Package, stdenv: Package,
) -> Package:
    bt = str(bootstrap_tools)
    guess = str(config_guess)
    sub = str(config_sub)
    return mk_derivation(
        pname="gnu-config",
        version="2024-01-01",
        builder=f"{bt}/bin/bash",
        stdenv=stdenv,
        deps=[bootstrap_tools, config_guess, config_sub],
        env={
            "dontBuild": "1",
            "dontConfigure": "1",
            "dontUpdateAutotoolsGnuConfigScripts": "1",
            "installPhase": """\
runHook preInstall
install -Dm755 ./config.guess $out/config.guess
install -Dm755 ./config.sub $out/config.sub
runHook postInstall
""",
            "strictDeps": "",
            "unpackPhase": f"""\
runHook preUnpack
cp {guess} ./config.guess
cp {sub} ./config.sub
chmod +w ./config.sub ./config.guess
runHook postUnpack
""",
        },
    )
