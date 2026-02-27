"""nuke-references — Strip store references from build outputs.

Like nixpkgs/pkgs/build-support/nuke-references/default.nix.
Uses xgcc stdenvNoCC. Single output: out.

Very simple package: installs nuke-refs.sh script with substituteAll
to fill in @perl@, @shell@, @storeDir@, @signingUtils@ placeholders.

Key details:
  - dontUnpack/dontConfigure/dontBuild: "1"
  - installPhase: mkdir + substituteAll + chmod
  - NIX_MAIN_PROGRAM: nuke-refs
  - strictDeps=1
  - perl: stage1 perl (for substituteAll in nuke-refs.sh)
"""

from pixpkgs.drv import Package
from pixpkgs.mk_derivation import mk_derivation
from pixpkgs.vendor import NUKE_REFS_SH


def make_nuke_references(
    bootstrap_tools: Package,
    stdenv: Package,
    perl: Package,
) -> Package:
    bt = str(bootstrap_tools)

    # perl is multi-output (out/man/devdoc) but we reference perl.out
    input_drvs = {perl.drv_path: ["out"]}

    return mk_derivation(
        name="nuke-references",
        builder=f"{bt}/bin/bash",
        stdenv=stdenv,
        deps=[bootstrap_tools, perl],
        input_drvs=input_drvs,
        srcs=[NUKE_REFS_SH],
        env={
            "NIX_MAIN_PROGRAM": "nuke-refs",
            "dontBuild": "1",
            "dontConfigure": "1",
            "dontUnpack": "1",
            "enableParallelBuilding": "1",
            "enableParallelChecking": "1",
            "enableParallelInstalling": "1",
            "installPhase": (
                "mkdir -p $out/bin\n"
                f"substituteAll {NUKE_REFS_SH} $out/bin/nuke-refs\n"
                "chmod a+x $out/bin/nuke-refs\n"
            ),
            "perl": str(perl),
            "shell": f"{bt}/bin/bash",
            # signingUtils is empty in the bootstrap (no signing)
            "signingUtils": "",
            "storeDir": "/nix/store",
            "strictDeps": "1",
        },
    )
