"""Wrap bootstrap-tools GCC with nix-support files.

Like nixpkgs/pkgs/build-support/cc-wrapper/default.nix.
Wraps gcc, g++, cpp with libc paths, hardening flags, and bintools link.
"""

from pixpkgs.drv import Package
from pixpkgs.mk_derivation import mk_derivation
from pixpkgs.vendor import (
    CC_ADD_FLAGS, CC_ADD_HARDENING, CC_SETUP_HOOK, CC_WRAPPER_SH,
    DARWIN_SDK_SETUP_BASH, ROLE_BASH, UTILS_BASH,
)

HARDENING_FLAGS = (
    "bindnow format fortify fortify3 "
    "libcxxhardeningextensive libcxxhardeningfast "
    "pic relro stackclashprotection stackprotector "
    "strictoverflow zerocallusedregs"
)


def make_gcc_wrapper(
    bootstrap_tools: Package, binutils_wrapper: Package,
    glibc_bf: Package, stdenv: Package,
    *,
    pname: str = "bootstrap-stage1-gcc-wrapper",
    expand_response_params: str = "",
    expand_response_params_pkg: Package | None = None,
) -> Package:
    bt = str(bootstrap_tools)
    bintools = str(binutils_wrapper)
    libc = str(glibc_bf)
    deps = [bootstrap_tools, binutils_wrapper, glibc_bf]
    if expand_response_params_pkg is not None:
        deps.append(expand_response_params_pkg)
    return mk_derivation(
        pname=pname,
        version="",
        builder=f"{bt}/bin/bash",
        stdenv=stdenv,
        deps=deps,
        srcs=[
            UTILS_BASH, DARWIN_SDK_SETUP_BASH, CC_WRAPPER_SH,
            CC_ADD_HARDENING, ROLE_BASH, CC_ADD_FLAGS, CC_SETUP_HOOK,
        ],
        env={
            "NIX_MAIN_PROGRAM": pname,
            "bintools": bintools,
            "cc": bt,
            "coreutils_bin": bt,
            "darwinMinVersion": "",
            "darwinMinVersionVariable": "",
            "darwinPlatformForCC": "",
            "default_hardening_flags_str": HARDENING_FLAGS,
            "dontBuild": "1",
            "dontCheckForBrokenSymlinks": "1",
            "dontConfigure": "1",
            "enableParallelBuilding": "1",
            "enableParallelChecking": "1",
            "enableParallelInstalling": "1",
            "expandResponseParams": expand_response_params,
            "gnugrep_bin": bt,
            "installPhase": f"""\
mkdir -p $out/bin $out/nix-support

wrap() {{
  local dst="$1"
  local wrapper="$2"
  export prog="$3"
  export use_response_file_by_default=0
  substituteAll "$wrapper" "$out/bin/$dst"
  chmod +x "$out/bin/$dst"
}}

include() {{
  printf -- '%s %s\\n' "$1" "$2"
  \n\
}}
echo $cc > $out/nix-support/orig-cc

ccPath="{bt}/bin"
for bbin in $bintools/bin/*; do
  mkdir -p "$out/bin"
  ln -s "$bbin" "$out/bin/$(basename $bbin)"
done
export named_cc=cc
export named_cxx=c++

if [ -e $ccPath/gcc ]; then
  wrap gcc $wrapper $ccPath/gcc
  ln -s gcc $out/bin/cc
  export named_cc=gcc
  export named_cxx=g++
elif [ -e $ccPath/clang ]; then
  wrap clang $wrapper $ccPath/clang
  ln -s clang $out/bin/cc
  export named_cc=clang
  export named_cxx=clang++
elif [ -e $ccPath/arocc ]; then
  wrap arocc $wrapper $ccPath/arocc
  ln -s arocc $out/bin/cc
  export named_cc=arocc
fi

if [ -e $ccPath/g++ ]; then
  wrap g++ $wrapper $ccPath/g++
  ln -s g++ $out/bin/c++
elif [ -e $ccPath/clang++ ]; then
  wrap clang++ $wrapper $ccPath/clang++
  ln -s clang++ $out/bin/c++
fi

if [ -e $ccPath/cpp ]; then
  wrap cpp $wrapper $ccPath/cpp
elif [ -e $ccPath/cpp ]; then
  wrap cpp $wrapper $ccPath/cpp
fi
""",
            "isArocc": "",
            "isClang": "",
            "libc_bin": libc,
            "libc_dev": libc,
            "libc_lib": libc,
            "mktemp": f"{bt}/bin/mktemp",
            "postFixup": f"""\
touch "$out/nix-support/cc-cflags"
touch "$out/nix-support/cc-ldflags"
if [[ -f "$bintools/nix-support/dynamic-linker" ]]; then
  ln -s "$bintools/nix-support/dynamic-linker" "$out/nix-support"
fi
if [[ -f "$bintools/nix-support/dynamic-linker-m32" ]]; then
  ln -s "$bintools/nix-support/dynamic-linker-m32" "$out/nix-support"
fi
touch "$out/nix-support/libc-cflags"
touch "$out/nix-support/libc-ldflags"
echo "-B{libc}/lib/" >> $out/nix-support/libc-crt1-cflags
include "-idirafter" "{libc}/include" >> $out/nix-support/libc-cflags
for dir in "{bt}"/lib/gcc/*/*/include-fixed; do
  include '-idirafter' ${{dir}} >> $out/nix-support/libc-cflags
done

echo "{libc}" > $out/nix-support/orig-libc
echo "{libc}" > $out/nix-support/orig-libc-dev
touch "$out/nix-support/libcxx-cxxflags"
touch "$out/nix-support/libcxx-ldflags"
if [ -e "{bt}/lib64" -a ! -L "{bt}/lib64" ]; then
  ccLDFlags+=" -L{bt}/lib64"
  ccCFlags+=" -B{bt}/lib64"
fi
ccLDFlags+=" -L{bt}/lib"
ccCFlags+=" -B{bt}/lib"

echo "$ccLDFlags" >> $out/nix-support/cc-ldflags
echo "$ccCFlags" >> $out/nix-support/cc-cflags
export hardening_unsupported_flags="fortify3 shadowstack pacret stackclashprotection trivialautovarinit zerocallusedregs"
echo " -fno-omit-frame-pointer -mno-omit-leaf-frame-pointer " >> $out/nix-support/cc-cflags-before
for flags in "$out/nix-support"/*flags*; do
  substituteInPlace "$flags" --replace $'\\n' ' '
done

substituteAll {CC_ADD_FLAGS} $out/nix-support/add-flags.sh
substituteAll {CC_ADD_HARDENING} $out/nix-support/add-hardening.sh
substituteAll {UTILS_BASH} $out/nix-support/utils.bash
substituteAll {DARWIN_SDK_SETUP_BASH} $out/nix-support/darwin-sdk-setup.bash
""",
            "preferLocalBuild": "1",
            "propagatedBuildInputs": bintools,
            "rm": f"{bt}/bin/rm",
            "setupHooks": f"{ROLE_BASH} {CC_SETUP_HOOK}",
            "shell": f"{bt}/bin/bash",
            "strictDeps": "1",
            "suffixSalt": "x86_64_unknown_linux_gnu",
            "unpackPhase": "src=$PWD\n",
            "useMacroPrefixMap": "",
            "version": "",
            "wrapper": CC_WRAPPER_SH,
            "wrapperName": "CC_WRAPPER",
        },
    )
