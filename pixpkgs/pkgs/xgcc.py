"""xgcc — First GCC compiled from source (gcc-unwrapped 14.3.0).

Like nixpkgs/pkgs/development/compilers/gcc/default.nix with the
bootstrap-stage-xgcc overrides from pkgs/stdenv/linux/default.nix.

The xgcc binary is "linked against junk from bootstrap-files" but we
only care about the code it *emits* — it's not part of the final stdenv.

6 outputs: out, man, info, lib, libgcc, checksum.
19 inputDrvs, 5 GCC patches, massive env with shell scripts.

Key features:
  - configureFlags: ~25 flags with interpolated store paths
  - noSysDirs=1: massive preUnpack phase extracts compiler/linker flags
  - postPatch: fixes dynamic linker paths in gcc headers
  - preConfigure: symlinks libxcrypt crypt.h, removes bundled zlib
  - postInstallSaveChecksumPhase: wraps genchecksum with nuke-refs
  - preFixupLibGccPhase: moves libgcc_s to its own output
  - hardeningDisable: format stackclashprotection
  - depsBuildBuild: xgcc gcc_wrapper (build compiler)
  - depsBuildTarget: binutils_wrapper + patchelf
"""

from pix.store_path import placeholder
from pixpkgs.drv import Package
from pixpkgs.mk_derivation import mk_derivation
from pixpkgs.vendor import (
    GCC_CFI_STARTPROC_PATCH,
    GCC_MANGLE_NIX_STORE_PATCH,
    GCC_NO_SYS_DIRS_PATCH,
    GCC_NO_SYS_DIRS_RISCV_PATCH,
    GCC_PPC_MUSL_PATCH,
)


def make_xgcc(
    bootstrap_tools: Package,
    stdenv: Package,
    src: Package,
    gcc_wrapper: Package,
    binutils_wrapper: Package,
    patchelf: Package,
    glibc_bootstrap_files: Package,
    gmp: Package,
    mpfr: Package,
    libmpc: Package,
    libxcrypt: Package,
    isl: Package,
    zlib: Package,
    texinfo: Package,
    which_pkg: Package,
    gettext: Package,
    perl: Package,
    bash_xgcc: Package,
    nuke_references: Package,
) -> Package:
    bt = str(bootstrap_tools)

    gmp_dev = gmp.outputs["dev"]
    mpfr_dev = mpfr.outputs["dev"]
    zlib_dev = zlib.outputs["dev"]

    glibc_bf = str(glibc_bootstrap_files)
    out_ph = placeholder("out")

    patches = " ".join([
        GCC_NO_SYS_DIRS_PATCH,
        GCC_NO_SYS_DIRS_RISCV_PATCH,
        GCC_MANGLE_NIX_STORE_PATCH,
        GCC_PPC_MUSL_PATCH,
        GCC_CFI_STARTPROC_PATCH,
    ])

    configure_flags = " ".join([
        f"--with-gmp-include={gmp_dev}/include",
        f"--with-gmp-lib={gmp}/lib",
        f"--with-mpfr-include={mpfr_dev}/include",
        f"--with-mpfr-lib={mpfr}/lib",
        f"--with-mpc={libmpc}",
        f"--with-native-system-header-dir={glibc_bf}/include",
        "--with-build-sysroot=/",
        f"--with-gxx-include-dir={out_ph}/include/c++/14.3.0/",
        "--program-prefix=",
        "--disable-lto",
        "--disable-libstdcxx-pch",
        "--without-included-gettext",
        "--with-system-zlib",
        "--enable-static",
        "--enable-languages=c,c++",
        "--disable-multilib",
        "--enable-plugin",
        "--disable-libcc1",
        f"--with-isl={isl}",
        "--disable-bootstrap",
        "--with-native-system-header-dir=/include",
        f"--with-build-sysroot={glibc_bf}",
        "--disable-nls",
        "--build=x86_64-unknown-linux-gnu",
        "--host=x86_64-unknown-linux-gnu",
        "--target=x86_64-unknown-linux-gnu",
    ])

    build_inputs = " ".join([
        gmp_dev,
        mpfr_dev,
        str(libmpc),
        str(libxcrypt),
        str(binutils_wrapper),
        str(isl),
        zlib_dev,
    ])

    # postPatch: fixes GLIBC/UCLIBC/MUSL_DYNAMIC_LINKER macros in gcc headers
    post_patch = (
        "configureScripts=$(find . -name configure)\n"
        "for configureScript in $configureScripts; do\n"
        "  patchShebangs $configureScript\n"
        "done\n"
        "\n"
        "# Make sure nixpkgs versioning match upstream one\n"
        "# to ease version-based comparisons.\n"
        "gcc_base_version=$(< gcc/BASE-VER)\n"
        "if [[ 14.3.0 != $gcc_base_version ]]; then\n"
        "  echo \"Please update 'version' variable:\"\n"
        "  echo \"  Expected: '$gcc_base_version'\"\n"
        "  echo \"  Actual: '14.3.0'\"\n"
        "  exit 1\n"
        "fi\n"
        'echo "fixing the {GLIBC,UCLIBC,MUSL}_DYNAMIC_LINKER macros..."\n'
        'for header in "gcc/config/"*-gnu.h "gcc/config/"*"/"*.h\n'
        "do\n"
        '  grep -q _DYNAMIC_LINKER "$header" || continue\n'
        '  echo "  fixing $header..."\n'
        '  sed -i "$header" \\\n'
        "      -e 's|define[[:blank:]]*\\([UCG]\\+\\)LIBC_DYNAMIC_LINKER\\([0-9]*\\)[[:blank:]]\"\\([^\\\"]"
        "\\+\\)\"$|define \\1LIBC_DYNAMIC_LINKER\\2 \""
        f"{glibc_bf}"
        "\\3\"|g' \\\n"
        "      -e 's|define[[:blank:]]*MUSL_DYNAMIC_LINKER\\([0-9]*\\)[[:blank:]]\"\\([^\\\"]"
        "\\+\\)\"$|define MUSL_DYNAMIC_LINKER\\1 \""
        f"{glibc_bf}"
        "\\2\"|g'\n"
        "  done\n"
    )

    # preConfigure: symlinks libxcrypt crypt.h, removes bundled zlib,
    # creates out-of-tree build directory
    pre_configure = (
        f"ln -sf {libxcrypt}/include/crypt.h libsanitizer/sanitizer_common/crypt.h\n"
        'if test -n "$newlibSrc"; then\n'
        '    tar xvf "$newlibSrc" -C ..\n'
        "    ln -s ../newlib-*/newlib newlib\n"
        "    # Patch to get armvt5el working:\n"
        "    sed -i -e 's/ arm)/ arm*)/' newlib/configure.host\n"
        "fi\n"
        "\n"
        "# Bug - they packaged zlib\n"
        'if test -d "zlib"; then\n'
        "    # This breaks the build without-headers, which should build only\n"
        "    # the target libgcc as target libraries.\n"
        "    # See 'configure:5370'\n"
        "    rm -Rf zlib\n"
        "fi\n"
        "\n"
        'if test -n "$crossMingw" -a -n "$withoutTargetLibc"; then\n'
        "    mkdir -p ../mingw\n"
        "    # --with-build-sysroot expects that:\n"
        "    cp -R $libcCross/include ../mingw\n"
        '    appendToVar configureFlags "--with-build-sysroot=`pwd`/.."\n'
        "fi\n"
        "\n"
        "# Perform the build in a different directory.\n"
        "mkdir ../build\n"
        "cd ../build\n"
        "configureScript=../$sourceRoot/configure\n"
    )

    # postConfigure: scrubs store paths from embedded configure flags
    post_configure = (
        "# Avoid store paths when embedding ./configure flags into gcc.\n"
        "# Mangled arguments are still useful when reporting bugs upstream.\n"
        'sed -e "/TOPLEVEL_CONFIGURE_ARGUMENTS=/ s|$NIX_STORE/[a-z0-9]\\{32\\}-'
        '|$NIX_STORE/eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee-|g" -i Makefile\n'
    )

    # preInstall: creates lib32/lib64 compatibility symlinks
    pre_install = (
        "declare -ga compatibilitySymlinks=()\n"
        "\n"
        "makeCompatibilitySymlink() {\n"
        '  declare -a outputsToLink=("$out")\n'
        "\n"
        '  if [ -n "$lib" ]; then\n'
        '    outputsToLink+=("$lib")\n'
        "  fi\n"
        "\n"
        '  for output in "${outputsToLink[@]}"; do\n'
        '    local linkTarget="$1"\n'
        '    local linkName="$output/$2"\n'
        "\n"
        '    echo "Creating compatibility symlink: $linkTarget -> $linkName"\n'
        "\n"
        '    mkdir -p "$(dirname "$linkName")"\n'
        '    ln -s "$linkTarget" "$linkName"\n'
        '    compatibilitySymlinks+=("$linkName")\n'
        "  done\n"
        "}\n"
        "makeCompatibilitySymlink lib lib32\n"
        "makeCompatibilitySymlink lib lib64\n"
    )

    # postInstall: moves libs to $lib output, cleans up, replaces hard links
    post_install = (
        "# Clean up our compatibility symlinks (see above)\n"
        'for link in "${compatibilitySymlinks[@]}"; do\n'
        '  echo "Removing compatibility symlink: $link"\n'
        '  rm -f "$link"\n'
        "done\n"
        "\n"
        "# Move target runtime libraries to lib output.\n"
        "# For non-cross, they're in $out/lib; for cross, they're in $out/$targetConfig/lib.\n"
        'targetLibDir="${targetConfig+$targetConfig/}lib"\n'
        "\n"
        'moveToOutput "$targetLibDir/lib*.so*" "${!outputLib}"\n'
        'moveToOutput "$targetLibDir/lib*.dylib" "${!outputLib}"\n'
        'moveToOutput "$targetLibDir/lib*.dll.a" "${!outputLib}"\n'
        'moveToOutput "$targetLibDir/lib*.dll" "${!outputLib}"\n'
        'moveToOutput "share/gcc-*/python" "${!outputLib}"\n'
        "\n"
        'if [ -z "$enableShared" ]; then\n'
        '    moveToOutput "$targetLibDir/lib*.a" "${!outputLib}"\n'
        "fi\n"
        "\n"
        'for i in "${!outputLib}"/$targetLibDir/*.py; do\n'
        '    substituteInPlace "$i" --replace "$out" "${!outputLib}"\n'
        "done\n"
        "\n"
        "# Multilib and cross can't exist at the same time, so just use lib64 here\n"
        'if [ -n "$enableMultilib" ]; then\n'
        '    moveToOutput "lib64/lib*.so*" "${!outputLib}"\n'
        '    moveToOutput "lib64/lib*.dylib" "${!outputLib}"\n'
        '    moveToOutput "lib64/lib*.dll.a" "${!outputLib}"\n'
        '    moveToOutput "lib64/lib*.dll" "${!outputLib}"\n'
        "\n"
        '    for i in "${!outputLib}"/lib64/*.py; do\n'
        '        substituteInPlace "$i" --replace "$out" "${!outputLib}"\n'
        "    done\n"
        "fi\n"
        "\n"
        "# Remove `fixincl' to prevent a retained dependency on the\n"
        "# previous gcc.\n"
        "rm -rf $out/libexec/gcc/*/*/install-tools\n"
        "rm -rf $out/lib/gcc/*/*/install-tools\n"
        "\n"
        "# More dependencies with the previous gcc or some libs (gccbug stores the build command line)\n"
        "rm -rf $out/bin/gccbug\n"
        "\n"
        "# Remove .la files, they're not adjusted for the makeCompatibilitySymlink magic,\n"
        "# which confuses libtool and leads to weird linking errors.\n"
        "# Removing the files just makes libtool link .so files directly, which is usually\n"
        "# what we want anyway.\n"
        "find $out -name '*.la' -delete\n"
        "\n"
        'if type "install_name_tool"; then\n'
        '    for i in "${!outputLib}"/lib/*.*.dylib "${!outputLib}"/lib/*.so.[0-9]; do\n'
        '        install_name_tool -id "$i" "$i" || true\n'
        '        for old_path in $(otool -L "$i" | grep "$out" | awk \'{print $1}\'); do\n'
        '          new_path=`echo "$old_path" | sed "s,$out,${!outputLib},"`\n'
        '          install_name_tool -change "$old_path" "$new_path" "$i" || true\n'
        "        done\n"
        "    done\n"
        "fi\n"
        "\n"
        "# Get rid of some \"fixed\" header files\n"
        "rm -rfv $out/lib/gcc/*/*/include-fixed/{root,linux,sys/mount.h,bits/statx.h,pthread.h}\n"
        "\n"
        "# Replace hard links for i686-pc-linux-gnu-gcc etc. with symlinks.\n"
        "for i in $out/bin/*-gcc*; do\n"
        "    if cmp -s $out/bin/gcc $i; then\n"
        "        ln -sfn gcc $i\n"
        "    fi\n"
        "done\n"
        "\n"
        "for i in $out/bin/c++ $out/bin/*-c++* $out/bin/*-g++*; do\n"
        "    if cmp -s $out/bin/g++ $i; then\n"
        "        ln -sfn g++ $i\n"
        "    fi\n"
        "done\n"
        "\n"
        "# Two identical man pages are shipped (moving and compressing is done later)\n"
        'for i in "$out"/share/man/man1/*g++.1; do\n'
        '    if test -e "$i"; then\n'
        '        man_prefix=`echo "$i" | sed "s,.*/\\(.*\\)g++.1,\\1,"`\n'
        "        ln -sf \"$man_prefix\"gcc.1 \"$i\"\n"
        "    fi\n"
        "done\n"
    )

    # preFixup: populates stripDebugList with correct library paths
    pre_fixup = (
        "# Populate most delicated lib/ part of stripDebugList{,Target}\n"
        "updateDebugListPaths() {\n"
        "  local oldOpts\n"
        '  oldOpts="$(shopt -p nullglob)" || true\n'
        "  shopt -s nullglob\n"
        "\n"
        "  pushd $out\n"
        "  local -ar outHostFiles=(\n"
        "    lib{,32,64}/*.{a,o,so*}\n"
        "    lib{,32,64}/gcc/x86_64-unknown-linux-gnu/*/plugin\n"
        "  )\n"
        "  local -ar outTargetFiles=(\n"
        "    lib{,32,64}/gcc/x86_64-unknown-linux-gnu/*/*.{a,o,so*}\n"
        "  )\n"
        "  popd\n"
        "\n"
        "  pushd $lib\n"
        "  local -ar libHostFiles=(\n"
        "    lib{,32,64}/*.{a,o,so*}\n"
        "  )\n"
        "  local -ar libTargetFiles=(\n"
        "    lib{,32,64}/x86_64-unknown-linux-gnu/*.{a,o,so*}\n"
        "  )\n"
        "  popd\n"
        "\n"
        '  eval "$oldOpts"\n'
        "\n"
        '  stripDebugList="$stripDebugList ${outHostFiles[*]} ${libHostFiles[*]}"\n'
        '  stripDebugListTarget="$stripDebugListTarget ${outTargetFiles[*]} ${libTargetFiles[*]}"\n'
        "}\n"
        "updateDebugListPaths\n"
    )

    # preFixupLibGccPhase: moves libgcc_s to its own output
    pre_fixup_libgcc_phase = (
        "# move libgcc from lib to its own output (libgcc)\n"
        "mkdir -p $libgcc/lib\n"
        "mv    $lib/lib/libgcc_s.so      $libgcc/lib/\n"
        "mv    $lib/lib/libgcc_s.so.1    $libgcc/lib/\n"
        "ln -s $libgcc/lib/libgcc_s.so   $lib/lib/\n"
        "ln -s $libgcc/lib/libgcc_s.so.1 $lib/lib/\n"
        'patchelf --set-rpath "" $libgcc/lib/libgcc_s.so.1\n'
    )

    # postInstallSaveChecksumPhase: wraps genchecksum with nuke-refs
    post_install_save_checksum = (
        "mv gcc/build/genchecksum gcc/build/.genchecksum-wrapped\n"
        "cat > gcc/build/genchecksum <<\\EOF\n"
        f"#!{bash_xgcc}/bin/bash\n"
        f"{nuke_references}/bin/nuke-refs $@\n"
        'for INPUT in "$@"; do install -Dt $INPUT $checksum/inputs/; done\n'
        "exec build/.genchecksum-wrapped $@\n"
        "EOF\n"
        "chmod +x gcc/build/genchecksum\n"
        "rm gcc/*-checksum.*\n"
        "make -C gcc cc1-checksum.o cc1plus-checksum.o\n"
        "install -Dt $checksum/checksums/ gcc/cc*-checksum.o\n"
    )

    # preFixupXgccPhase: shrinks rpaths on shared libs
    pre_fixup_xgcc_phase = (
        "find $lib/lib/ -name \\*.so\\* -exec patchelf --shrink-rpath {} \\; || true\n"
    )

    # NIX_HARDENING_ENABLE: 12 defaults minus format, stackclashprotection
    nix_hardening_enable = (
        "bindnow fortify fortify3 libcxxhardeningextensive"
        " libcxxhardeningfast pic relro"
        " stackprotector strictoverflow zerocallusedregs"
    )

    # preUnpack: the massive noSysDirs phase
    pre_unpack = _make_pre_unpack()

    # Override input_drvs for multi-output packages
    input_drvs = {
        gmp.drv_path: ["dev", "out"],
        mpfr.drv_path: ["dev", "out"],
        zlib.drv_path: ["dev", "out"],
        perl.drv_path: ["out"],
        bash_xgcc.drv_path: ["out"],
        gettext.drv_path: ["out"],
        libxcrypt.drv_path: ["out"],
    }

    return mk_derivation(
        pname="xgcc",
        version="14.3.0",
        builder=f"{bt}/bin/bash",
        stdenv=stdenv,
        output_names=["out", "man", "info", "lib", "libgcc", "checksum"],
        deps=[
            bootstrap_tools, src,
            gcc_wrapper, binutils_wrapper, patchelf,
            glibc_bootstrap_files, gmp, mpfr, libmpc, libxcrypt, isl, zlib,
            texinfo, which_pkg, gettext, perl,
            bash_xgcc, nuke_references,
        ],
        input_drvs=input_drvs,
        srcs=[
            GCC_NO_SYS_DIRS_PATCH,
            GCC_NO_SYS_DIRS_RISCV_PATCH,
            GCC_MANGLE_NIX_STORE_PATCH,
            GCC_PPC_MUSL_PATCH,
            GCC_CFI_STARTPROC_PATCH,
        ],
        env={
            "CPATH": f"{zlib_dev}/include",
            "EXTRA_FLAGS_FOR_TARGET": "",
            "EXTRA_LDFLAGS_FOR_TARGET": "",
            "LIBRARY_PATH": f"{zlib}/lib",
            "NIX_HARDENING_ENABLE": nix_hardening_enable,
            "NIX_LDFLAGS": "",
            "NIX_MAIN_PROGRAM": "gcc",
            "NIX_NO_SELF_RPATH": "1",
            "buildFlags": "",
            "buildInputs": build_inputs,
            "configureFlags": configure_flags,
            "configurePlatforms": "build host target",
            "crossMingw": "",
            "depsBuildBuild": str(gcc_wrapper),
            "depsBuildTarget": f"{binutils_wrapper} {patchelf}",
            "dontDisableStatic": "1",
            "enableMultilib": "",
            "enableParallelBuilding": "1",
            "enableParallelChecking": "1",
            "enableParallelInstalling": "",
            "enableShared": "1",
            "hardeningDisable": "format stackclashprotection",
            "libc_dev": glibc_bf,
            "nativeBuildInputs": f"{texinfo} {which_pkg} {gettext} {perl}",
            "noSysDirs": "1",
            "patches": patches,
            "postConfigure": post_configure,
            "postInstall": post_install,
            "postInstallSaveChecksumPhase": post_install_save_checksum,
            "postPatch": post_patch,
            "preConfigure": pre_configure,
            "preFixup": pre_fixup,
            "preFixupLibGccPhase": pre_fixup_libgcc_phase,
            "preFixupPhases": "preFixupLibGccPhase postInstallSaveChecksumPhase preFixupXgccPhase",
            "preFixupXgccPhase": pre_fixup_xgcc_phase,
            "preInstall": pre_install,
            "preUnpack": pre_unpack,
            "setOutputFlags": "",
            "src": str(src),
            "staticCompiler": "",
            "stripDebugList": "bin libexec",
            "stripDebugListTarget": "x86_64-unknown-linux-gnu",
            "withoutTargetLibc": "",
        },
    )


def _make_pre_unpack() -> str:
    """Build the massive noSysDirs preUnpack shell script.

    This extracts compiler/linker flags from the CC and bintools wrappers
    and sets up makeFlagsArray for the GCC build. It's identical for all
    platforms (the platform-specific parts are handled by conditionals).
    """
    # Note: contains U+2010 (HYPHEN) in "non\u2010GCC"
    return (
        'oldOpts="$(shopt -po nounset)" || true\n'
        "set -euo pipefail\n"
        "\n"
        'export NIX_FIXINC_DUMMY="$NIX_BUILD_TOP/dummy"\n'
        'mkdir "$NIX_FIXINC_DUMMY"\n'
        "\n"
        'if test "$staticCompiler" = "1"; then\n'
        '    EXTRA_LDFLAGS="-static"\n'
        'elif test "${NIX_DONT_SET_RPATH-}" != "1"; then\n'
        '    EXTRA_LDFLAGS="-Wl,-rpath,${!outputLib}/lib"\n'
        "else\n"
        '    EXTRA_LDFLAGS=""\n'
        "fi\n"
        "\n"
        "# GCC interprets empty paths as \".\", which we don't want.\n"
        'if test -z "${CPATH-}"; then unset CPATH; fi\n'
        'if test -z "${LIBRARY_PATH-}"; then unset LIBRARY_PATH; fi\n'
        "echo \"\\$CPATH is \\`${CPATH-}'\"\n"
        "echo \"\\$LIBRARY_PATH is \\`${LIBRARY_PATH-}'\"\n"
        "\n"
        'if test "$noSysDirs" = "1"; then\n'
        "\n"
        "    declare -g \\\n"
        "        EXTRA_FLAGS_FOR_BUILD EXTRA_FLAGS EXTRA_FLAGS_FOR_TARGET \\\n"
        "        EXTRA_LDFLAGS_FOR_BUILD EXTRA_LDFLAGS_FOR_TARGET\n"
        "\n"
        "    # Extract flags from Bintools Wrappers\n"
        "    for post in '_FOR_BUILD' \"\"; do\n"
        '        curBintools="NIX_BINTOOLS${post}"\n'
        "\n"
        "        declare -a extraLDFlags=()\n"
        '        if [[ -e "${!curBintools}/nix-support/orig-libc" ]]; then\n'
        "            # Figure out what extra flags when linking to pass to the gcc\n"
        "            # compilers being generated to make sure that they use our libc.\n"
        '            extraLDFlags=($(< "${!curBintools}/nix-support/libc-ldflags") $(< "${!curBintools}/nix-support/libc-ldflags-before" || true))\n'
        "            if [ -e ${!curBintools}/nix-support/ld-set-dynamic-linker ]; then\n"
        "                extraLDFlags=-dynamic-linker=$(< ${!curBintools}/nix-support/dynamic-linker)\n"
        "            fi\n"
        "\n"
        "            # The path to the Libc binaries such as `crti.o'.\n"
        '            libc_libdir="$(< "${!curBintools}/nix-support/orig-libc")/lib"\n'
        "        else\n"
        "            # Hack: support impure environments.\n"
        '            extraLDFlags=("-L/usr/lib64" "-L/usr/lib")\n'
        '            libc_libdir="/usr/lib"\n'
        "        fi\n"
        "        declare -a prefixExtraLDFlags=()\n"
        '        prefixExtraLDFlags=("-L$libc_libdir")\n'
        "        nixDontSetRpathVar=NIX_DONT_SET_RPATH${post}\n"
        '        if test "${!nixDontSetRpathVar-}" != "1"; then\n'
        '            prefixExtraLDFlags+=("-rpath" "$libc_libdir")\n'
        "        fi\n"
        '        extraLDFlags=("${prefixExtraLDFlags[@]}" "${extraLDFlags[@]}")\n'
        '        for i in "${extraLDFlags[@]}"; do\n'
        '            declare -g EXTRA_LDFLAGS${post}+=" -Wl,$i"\n'
        "        done\n"
        "    done\n"
        "\n"
        "    # Extract flags from CC Wrappers\n"
        "    for post in '_FOR_BUILD' \"\"; do\n"
        '        curCC="NIX_CC${post}"\n'
        '        curFIXINC="NIX_FIXINC_DUMMY${post}"\n'
        "\n"
        "        declare -a extraFlags=()\n"
        '        if [[ -e "${!curCC}/nix-support/orig-libc" ]]; then\n'
        "            # Figure out what extra compiling flags to pass to the gcc compilers\n"
        "            # being generated to make sure that they use our libc.\n"
        '            extraFlags=($(< "${!curCC}/nix-support/libc-crt1-cflags") $(< "${!curCC}/nix-support/libc-cflags"))\n'
        "\n"
        "            # The path to the Libc headers\n"
        '            libc_devdir="$(< "${!curCC}/nix-support/orig-libc-dev")"\n'
        "\n"
        "            # Use *real* header files, otherwise a limits.h is generated that\n"
        "            # does not include Libc's limits.h (notably missing SSIZE_MAX,\n"
        "            # which breaks the build).\n"
        '            declare -g NIX_FIXINC_DUMMY${post}="$libc_devdir/include"\n'
        "        else\n"
        "            # Hack: support impure environments.\n"
        '            extraFlags=("-isystem" "/usr/include")\n'
        "            declare -g NIX_FIXINC_DUMMY${post}=/usr/include\n"
        "        fi\n"
        "\n"
        '        extraFlags=("-I${!curFIXINC}" "${extraFlags[@]}")\n'
        "\n"
        "        # BOOT_CFLAGS defaults to `-g -O2'; since we override it below, make\n"
        "        # sure to explictly add them so that files compiled with the bootstrap\n"
        "        # compiler are optimized and (optionally) contain debugging information\n"
        '        # (info "(gccinstall) Building").\n'
        '        if test -n "${dontStrip-}"; then\n'
        '            extraFlags=("-O2" "-g" "${extraFlags[@]}")\n'
        "        else\n"
        "            # Don't pass `-g' at all; this saves space while building.\n"
        '            extraFlags=("-O2" "${extraFlags[@]}")\n'
        "        fi\n"
        "\n"
        '        declare -g EXTRA_FLAGS${post}="${extraFlags[*]}"\n'
        "    done\n"
        "\n"
        '    if test -z "${targetConfig-}"; then\n'
        "        # host = target, so the flags are the same\n"
        '        EXTRA_FLAGS_FOR_TARGET="$EXTRA_FLAGS"\n'
        '        EXTRA_LDFLAGS_FOR_TARGET="$EXTRA_LDFLAGS"\n'
        "    fi\n"
        "\n"
        "    # We include `-fmacro-prefix-map` in `cc-wrapper` for non\u2010GCC\n"
        "    # platforms only, but they get picked up and passed down to\n"
        "    # e.g. GFortran calls that complain about the option not\n"
        "    # applying to the language. Hack around it by asking GCC not\n"
        "    # to complain.\n"
        "    #\n"
        "    # TODO: Someone please fix this to do things that make sense.\n"
        '    if [[ $EXTRA_FLAGS_FOR_BUILD == *-fmacro-prefix-map* ]]; then\n'
        '        EXTRA_FLAGS_FOR_BUILD+=" -Wno-complain-wrong-lang"\n'
        "    fi\n"
        '    if [[ $EXTRA_FLAGS_FOR_TARGET == *-fmacro-prefix-map* ]]; then\n'
        '        EXTRA_FLAGS_FOR_TARGET+=" -Wno-complain-wrong-lang"\n'
        "    fi\n"
        "\n"
        "    # CFLAGS_FOR_TARGET are needed for the libstdc++ configure script to find\n"
        "    # the startfiles.\n"
        "    # FLAGS_FOR_TARGET are needed for the target libraries to receive the -Bxxx\n"
        "    # for the startfiles.\n"
        "    makeFlagsArray+=(\n"
        '        "BUILD_SYSTEM_HEADER_DIR=$NIX_FIXINC_DUMMY_FOR_BUILD"\n'
        '        "SYSTEM_HEADER_DIR=$NIX_FIXINC_DUMMY_FOR_BUILD"\n'
        '        "NATIVE_SYSTEM_HEADER_DIR=$NIX_FIXINC_DUMMY"\n'
        "\n"
        '        "LDFLAGS_FOR_BUILD=$EXTRA_LDFLAGS_FOR_BUILD"\n'
        '        #"LDFLAGS=$EXTRA_LDFLAGS"\n'
        '        "LDFLAGS_FOR_TARGET=$EXTRA_LDFLAGS_FOR_TARGET"\n'
        "\n"
        '        "CFLAGS_FOR_BUILD=$EXTRA_FLAGS_FOR_BUILD $EXTRA_LDFLAGS_FOR_BUILD"\n'
        '        "CXXFLAGS_FOR_BUILD=$EXTRA_FLAGS_FOR_BUILD $EXTRA_LDFLAGS_FOR_BUILD"\n'
        '        "FLAGS_FOR_BUILD=$EXTRA_FLAGS_FOR_BUILD $EXTRA_LDFLAGS_FOR_BUILD"\n'
        "\n"
        "        # It seems there is a bug in GCC 5\n"
        '        #"CFLAGS=$EXTRA_FLAGS $EXTRA_LDFLAGS"\n'
        '        #"CXXFLAGS=$EXTRA_FLAGS $EXTRA_LDFLAGS"\n'
        "\n"
        '        "CFLAGS_FOR_TARGET=$EXTRA_FLAGS_FOR_TARGET $EXTRA_LDFLAGS_FOR_TARGET"\n'
        '        "CXXFLAGS_FOR_TARGET=$EXTRA_FLAGS_FOR_TARGET $EXTRA_LDFLAGS_FOR_TARGET"\n'
        '        "FLAGS_FOR_TARGET=$EXTRA_FLAGS_FOR_TARGET $EXTRA_LDFLAGS_FOR_TARGET"\n'
        "    )\n"
        "\n"
        '    if test -z "${targetConfig-}"; then\n'
        "        makeFlagsArray+=(\n"
        '            "BOOT_CFLAGS=$EXTRA_FLAGS $EXTRA_LDFLAGS"\n'
        '            "BOOT_LDFLAGS=$EXTRA_FLAGS_FOR_TARGET $EXTRA_LDFLAGS_FOR_TARGET"\n'
        "        )\n"
        "    fi\n"
        "\n"
        '    if test "$withoutTargetLibc" == 1; then\n'
        "        # We don't want the gcc build to assume there will be a libc providing\n"
        "        # limits.h in this stage\n"
        "        makeFlagsArray+=(\n"
        "            'LIMITS_H_TEST=false'\n"
        "        )\n"
        "    else\n"
        "        makeFlagsArray+=(\n"
        "            'LIMITS_H_TEST=true'\n"
        "        )\n"
        "    fi\n"
        "fi\n"
        "\n"
        'eval "$oldOpts"\n'
    )
