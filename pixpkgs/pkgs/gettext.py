"""gettext — GNU internationalization library and tools.

Like nixpkgs/pkgs/development/libraries/gettext/default.nix.
Uses stage1 stdenv. Multi-output: out, man, doc, info.

Key details:
  - configureFlags: --disable-csharp (no Mono support)
  - am_cv_func_iconv_works = "yes" (avoids iconv test failures)
  - 3 patches: absolute-paths.diff, 0001-msginit-Do-not-use-POT-Creation-Date.patch,
    memory-safety.patch
  - setupHooks: role.bash + gettext-setup-hook.sh (GETTEXTDATADIRS)
  - buildInputs: bash.dev (getDev returns bash's dev output)
  - nativeBuildInputs: update_autotools_hook
  - postPatch: replaces old extern-inline.m4 in archive.dir.tar for clang 18
    compatibility, plus substituteAllInPlace/substituteInPlace for paths
  - strictDeps=1
  - enableParallelChecking="" (disabled, fails sometimes)
"""

from pixpkgs.drv import Package
from pixpkgs.mk_derivation import mk_derivation
from pixpkgs.vendor import (
    GETTEXT_PATCH_ABSOLUTE_PATHS,
    GETTEXT_PATCH_MEMORY_SAFETY,
    GETTEXT_PATCH_NO_POT_DATE,
    GETTEXT_SETUP_HOOK,
    ROLE_BASH,
)


def make_gettext(
    bootstrap_tools: Package,
    stdenv: Package,
    src: Package,
    bash: Package,
    update_autotools_hook: Package,
) -> Package:
    bt = str(bootstrap_tools)

    patches = " ".join([
        GETTEXT_PATCH_ABSOLUTE_PATHS,
        GETTEXT_PATCH_NO_POT_DATE,
        GETTEXT_PATCH_MEMORY_SAFETY,
    ])

    # bash is multi-output (out/dev/man/doc/info/debug).
    # make-derivation.nix applies getDev → bash.dev for buildInputs.
    bash_dev = bash.outputs["dev"]
    input_drvs = {bash.drv_path: ["dev"]}

    # postPatch: replaces old extern-inline.m4 copies in archive.dir.tar
    # for clang 18 compatibility, then fixes hardcoded /bin/pwd paths.
    post_patch = (
        "# Older versions of gettext come with a copy of `extern-inline.m4` that is not compatible with clang 18.\n"
        "# When a project uses gettext + autoreconfPhase, autoreconfPhase will invoke `autopoint -f`, which will\n"
        "# replace whatever (probably compatible) version of `extern-inline.m4` with one that probalby won\u2019t work\n"
        "# because `autopoint` will copy the autoconf macros from the project\u2019s required version of gettext.\n"
        "# Fixing this requires replacing all the older copies of the problematic file with a new one.\n"
        "#\n"
        "# This is ugly, but it avoids requiring workarounds in every package using gettext and autoreconfPhase.\n"
        "declare -a oldFiles=($(tar tf gettext-tools/misc/archive.dir.tar | grep '^gettext-0\\.[19].*/extern-inline.m4'))\n"
        "oldFilesDir=$(mktemp -d)\n"
        'for oldFile in "${oldFiles[@]}"; do\n'
        '  mkdir -p "$oldFilesDir/$(dirname "$oldFile")"\n'
        '  cp -a gettext-tools/gnulib-m4/extern-inline.m4 "$oldFilesDir/$oldFile"\n'
        "done\n"
        'tar uf gettext-tools/misc/archive.dir.tar --owner=0 --group=0 --numeric-owner -C "$oldFilesDir" "${oldFiles[@]}"\n'
        "\n"
        "substituteAllInPlace gettext-runtime/src/gettext.sh.in\n"
        'substituteInPlace gettext-tools/projects/KDE/trigger --replace "/bin/pwd" pwd\n'
        'substituteInPlace gettext-tools/projects/GNOME/trigger --replace "/bin/pwd" pwd\n'
        'substituteInPlace gettext-tools/src/project-id --replace "/bin/pwd" pwd\n'
    )

    return mk_derivation(
        pname="gettext",
        version="0.25.1",
        builder=f"{bt}/bin/bash",
        stdenv=stdenv,
        output_names=["out", "man", "doc", "info"],
        deps=[bootstrap_tools, src, bash, update_autotools_hook],
        input_drvs=input_drvs,
        srcs=[
            GETTEXT_PATCH_ABSOLUTE_PATHS,
            GETTEXT_PATCH_NO_POT_DATE,
            GETTEXT_PATCH_MEMORY_SAFETY,
            GETTEXT_SETUP_HOOK,
            ROLE_BASH,
        ],
        env={
            "LDFLAGS": "",
            "am_cv_func_iconv_works": "yes",
            "buildInputs": bash_dev,
            "configureFlags": "--disable-csharp",
            "enableParallelBuilding": "1",
            "enableParallelChecking": "",
            "enableParallelInstalling": "1",
            "gettextNeedsLdflags": "",
            "nativeBuildInputs": str(update_autotools_hook),
            "patches": patches,
            "postPatch": post_patch,
            "setupHooks": f"{ROLE_BASH} {GETTEXT_SETUP_HOOK}",
            "src": str(src),
            "strictDeps": "1",
        },
    )
