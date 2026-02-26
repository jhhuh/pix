"""Setup hook that updates config.guess/config.sub in packages.

Like nixpkgs/pkgs/by-name/up/update-autotools-gnu-config-scripts-hook/.
"""

from pixpkgs.drv import Package
from pixpkgs.mk_derivation import mk_derivation
from pixpkgs.vendor import UPDATE_AUTOTOOLS_SCRIPT


def make_update_autotools_hook(
    gnu_config: Package, bootstrap_tools: Package, stdenv: Package,
) -> Package:
    bt = str(bootstrap_tools)
    return mk_derivation(
        name="update-autotools-gnu-config-scripts-hook",
        builder=f"{bt}/bin/bash",
        stdenv=stdenv,
        deps=[bootstrap_tools, gnu_config],
        srcs=[UPDATE_AUTOTOOLS_SCRIPT],
        env={
            "buildCommand": f"""\
mkdir -p $out/nix-support
cp {UPDATE_AUTOTOOLS_SCRIPT} $out/nix-support/setup-hook
recordPropagatedDependencies
substituteAll {UPDATE_AUTOTOOLS_SCRIPT} $out/nix-support/setup-hook
""",
            "enableParallelBuilding": "1",
            "enableParallelChecking": "1",
            "enableParallelInstalling": "1",
            "gnu_config": str(gnu_config),
            "passAsFile": "buildCommand",
            "strictDeps": "1",
        },
    )
