"""texinfo — GNU documentation system.

Like nixpkgs/pkgs/by-name/te/texinfo/package.nix.
Uses stage1 stdenv. Single output: out.

Key details:
  - configureFlags: PERL=<perl>/bin/perl (tells configure where perl is)
  - depsBuildBuild: gcc_wrapper + perl (cross-compilation aware)
  - installFlags: TEXMF=$(out)/texmf-dist (redirects TeX file install)
  - installTargets: "install install-tex" (runs both targets)
  - NIX_MAIN_PROGRAM: texi2any
  - postPatch: patchShebangs one perl script
  - buildInputs: bash.dev (getDev returns bash's dev output)
  - nativeBuildInputs: update_autotools_hook
  - strictDeps=1
"""

from pix.store_path import placeholder
from pixpkgs.drv import Package
from pixpkgs.mk_derivation import mk_derivation


def make_texinfo(
    bootstrap_tools: Package,
    stdenv: Package,
    src: Package,
    bash: Package,
    gcc_wrapper: Package,
    perl: Package,
    update_autotools_hook: Package,
) -> Package:
    bt = str(bootstrap_tools)

    # bash is multi-output → getDev returns bash.dev
    bash_dev = bash.outputs["dev"]
    # perl is multi-output (out/man/devdoc) but getDev returns perl.out
    # (no "dev" output), and gcc_wrapper is single-output.
    # input_drvs: bash → ["dev"], gcc_wrapper → ["out"], perl → ["out"]
    input_drvs = {
        bash.drv_path: ["dev"],
        gcc_wrapper.drv_path: ["out"],
        perl.drv_path: ["out"],
    }

    return mk_derivation(
        pname="texinfo",
        version="7.2",
        builder=f"{bt}/bin/bash",
        stdenv=stdenv,
        deps=[
            bootstrap_tools, src, bash, gcc_wrapper, perl,
            update_autotools_hook,
        ],
        input_drvs=input_drvs,
        env={
            "NIX_MAIN_PROGRAM": "texi2any",
            "XFAIL_TESTS": "",
            "buildInputs": f"{bash_dev} ",
            "configureFlags": f"PERL={perl}/bin/perl",
            "depsBuildBuild": f"{gcc_wrapper} {perl}",
            "enableParallelBuilding": "1",
            "enableParallelChecking": "1",
            "enableParallelInstalling": "1",
            "installFlags": "TEXMF=$(out)/texmf-dist",
            "installTargets": "install install-tex",
            "nativeBuildInputs": str(update_autotools_hook),
            # texinfo/package.nix: postFixup = lib.optionalString cross "..."
            # On native builds this is "" but still an explicit attr.
            "postFixup": "",
            "postPatch": "patchShebangs tp/maintain/regenerate_commands_perl_info.pl\n",
            "src": str(src),
            "strictDeps": "1",
        },
    )
