"""bash — GNU Bourne-Again Shell.

Like nixpkgs/pkgs/shells/bash/5.nix with interactive=false.
Uses stage1 stdenv. Multi-output: out, dev, man, doc, info + debug
(from separateDebugInfo=true).

The bootstrap builds the non-interactive variant (pname="bash").
Interactive=true would produce pname="bash-interactive".

patches: 3 upstream bash53-001/002/003 + pgrp-pipe-5.patch (enables
PGRP_PIPE unconditionally, independent of the build machine's kernel).
patchFlags=-p0 because upstream patches use -p0 format.

depsBuildBuild includes gcc_wrapper (buildPackages.stdenv.cc for native build).
nativeBuildInputs includes update_autotools_hook + bison.
separateDebugInfo=true adds the separate-debug-info.sh setup hook.
"""

from pix.store_path import placeholder
from pixpkgs.drv import Package
from pixpkgs.mk_derivation import mk_derivation
from pixpkgs.vendor import BASH_PGRP_PIPE_PATCH, SEPARATE_DEBUG_INFO_SH


def make_bash(
    bootstrap_tools: Package,
    stdenv: Package,
    src: Package,
    bash_patch_001: Package,
    bash_patch_002: Package,
    bash_patch_003: Package,
    gcc_wrapper: Package,
    update_autotools_hook: Package,
    bison: Package,
) -> Package:
    bt = str(bootstrap_tools)

    patches = " ".join([
        str(bash_patch_001),
        str(bash_patch_002),
        str(bash_patch_003),
        BASH_PGRP_PIPE_PATCH,
    ])

    # NIX_CFLAGS_COMPILE: from env.NIX_CFLAGS_COMPILE in bash/5.nix
    # Three Nix '' multiline strings concatenated (each strips indentation).
    # forFHSEnv=false, so DEFAULT_PATH_VALUE etc. are set to /no-such-path.
    # placeholder("out") for LOADABLE_BUILTINS_PATH.
    nix_cflags_compile = (
        '-DSYS_BASHRC="/etc/bashrc"\n'
        '-DSYS_BASH_LOGOUT="/etc/bash_logout"\n'
        '-DDEFAULT_PATH_VALUE="/no-such-path"\n'
        '-DSTANDARD_UTILS_PATH="/no-such-path"\n'
        f'-DDEFAULT_LOADABLE_BUILTINS_PATH="{placeholder("out")}/lib/bash:."\n'
        "-DNON_INTERACTIVE_LOGIN_SHELLS\n"
        "-DSSH_SOURCE_BASHRC\n"
    )

    # NIX_HARDENING_ENABLE: bintools-wrapper defaultHardeningFlags minus
    # hardeningDisable=["format"]. Set by make-derivation.nix when
    # hardeningDisable != [].
    nix_hardening_enable = (
        "bindnow fortify fortify3 libcxxhardeningextensive"
        " libcxxhardeningfast pic relro stackclashprotection"
        " stackprotector strictoverflow zerocallusedregs"
    )

    return mk_derivation(
        pname="bash",
        version="5.3p3",
        builder=f"{bt}/bin/bash",
        stdenv=stdenv,
        output_names=["out", "dev", "man", "doc", "info", "debug"],
        deps=[
            bootstrap_tools, src,
            bash_patch_001, bash_patch_002, bash_patch_003,
            gcc_wrapper, update_autotools_hook, bison,
        ],
        # bison has single output; bash patches are fetchurl (single out)
        input_drvs={},
        srcs=[BASH_PGRP_PIPE_PATCH, SEPARATE_DEBUG_INFO_SH],
        env={
            "NIX_CFLAGS_COMPILE": nix_cflags_compile,
            "NIX_HARDENING_ENABLE": nix_hardening_enable,
            # meta.mainProgram = "bash" → make-derivation adds NIX_MAIN_PROGRAM
            "NIX_MAIN_PROGRAM": "bash",
            "configureFlags": "--without-bash-malloc --disable-readline",
            "depsBuildBuild": str(gcc_wrapper),
            "enableParallelBuilding": "1",
            "enableParallelChecking": "1",
            "enableParallelInstalling": "1",
            "hardeningDisable": "format",
            # makeFlags = lib.optionals stdenv.hostPlatform.isCygwin [...] → [] on Linux → ""
            "makeFlags": "",
            "nativeBuildInputs": (
                f"{update_autotools_hook} {bison} {SEPARATE_DEBUG_INFO_SH}"
            ),
            "patchFlags": "-p0",
            # bash/5.nix: patch_suffix = "p${toString (builtins.length upstreamPatches)}"
            # Survives into env via attrs pass-through (not in removedOrReplacedAttrNames)
            "patch_suffix": "p3",
            "patches": patches,
            "postFixup": 'rm -rf "$out/share" "$out/bin/bashbug"\n',
            "postInstall": (
                'ln -s bash "$out/bin/sh"\n'
                "rm -f $out/lib/bash/Makefile.inc\n"
            ),
            "separateDebugInfo": "1",
            "src": str(src),
            "strictDeps": "1",
        },
    )
