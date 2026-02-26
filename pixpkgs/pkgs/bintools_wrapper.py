"""Wrap bootstrap-tools binutils with nix-support files.

Like nixpkgs/pkgs/build-support/bintools-wrapper/default.nix.
Wraps ld, ar, nm, strip, etc. with dynamic linker and libc paths.
"""

from pixpkgs.drv import Package
from pixpkgs.mk_derivation import mk_derivation
from pixpkgs.vendor import (
    BINTOOLS_ADD_FLAGS, BINTOOLS_ADD_HARDENING, BINTOOLS_SETUP_HOOK,
    DARWIN_SDK_SETUP_BASH, LD_WRAPPER_SH, ROLE_BASH,
    STRIP_WRAPPER_SH, UTILS_BASH,
)

HARDENING_FLAGS = (
    "bindnow format fortify fortify3 "
    "libcxxhardeningextensive libcxxhardeningfast "
    "pic relro stackclashprotection stackprotector "
    "strictoverflow zerocallusedregs"
)


def make_binutils_wrapper(
    bootstrap_tools: Package, glibc_bf: Package, stdenv: Package,
) -> Package:
    bt = str(bootstrap_tools)
    libc = str(glibc_bf)
    return mk_derivation(
        pname="bootstrap-stage0-binutils-wrapper",
        version="",
        builder=f"{bt}/bin/bash",
        stdenv=stdenv,
        deps=[bootstrap_tools, glibc_bf],
        srcs=[
            BINTOOLS_SETUP_HOOK, UTILS_BASH, DARWIN_SDK_SETUP_BASH,
            BINTOOLS_ADD_HARDENING, STRIP_WRAPPER_SH,
            BINTOOLS_ADD_FLAGS, LD_WRAPPER_SH, ROLE_BASH,
        ],
        env={
            "bintools_bin": bt,
            "coreutils_bin": bt,
            "darwinMinVersion": "",
            "darwinMinVersionVariable": "",
            "darwinPlatform": "",
            "darwinSdkVersion": "",
            "default_hardening_flags_str": HARDENING_FLAGS,
            "dontBuild": "1",
            "dontConfigure": "1",
            "dynamicLinker": f"{libc}/lib/ld-linux-x86-64.so.2",
            "enableParallelBuilding": "1",
            "enableParallelChecking": "1",
            "enableParallelInstalling": "1",
            "expandResponseParams": "/bin/expand-response-params",
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
echo $bintools_bin > $out/nix-support/orig-bintools

ldPath="{bt}/bin"
for binary in objdump objcopy size strings as ar nm gprof dwp c++filt addr2line \\
    ranlib readelf elfedit dlltool dllwrap windmc windres; do
  if [ -e $ldPath/${{binary}} ]; then
    ln -s $ldPath/${{binary}} $out/bin/${{binary}}
  fi
done

if [ -e ${{ld:-$ldPath/ld}} ]; then
  wrap ld {LD_WRAPPER_SH} ${{ld:-$ldPath/ld}}
fi

for variant in $ldPath/ld.*; do
  basename=$(basename "$variant")
  wrap $basename {LD_WRAPPER_SH} $variant
done
""",
            "libc_bin": libc,
            "libc_dev": libc,
            "libc_lib": libc,
            "mktemp": f"{bt}/bin/mktemp",
            "postFixup": f"""\
touch "$out/nix-support/libc-ldflags"
echo "-L{libc}/lib" >> $out/nix-support/libc-ldflags

echo "{libc}" > $out/nix-support/orig-libc
echo "{libc}" > $out/nix-support/orig-libc-dev
if [[ -z ${{dynamicLinker+x}} ]]; then
  echo "Don't know the name of the dynamic linker for platform 'x86_64-unknown-linux-gnu', so guessing instead." >&2
  local dynamicLinker="{libc}/lib/ld*.so.?"
fi
dynamicLinker=($dynamicLinker)

case ${{#dynamicLinker[@]}} in
  0) echo "No dynamic linker found for platform 'x86_64-unknown-linux-gnu'." >&2;;
  1) echo "Using dynamic linker: '$dynamicLinker'" >&2;;
  *) echo "Multiple dynamic linkers found for platform 'x86_64-unknown-linux-gnu'." >&2;;
esac

if [ -n "${{dynamicLinker-}}" ]; then
  echo $dynamicLinker > $out/nix-support/dynamic-linker

  if [ -e {libc}/lib/32/ld-linux.so.2 ]; then
  echo {libc}/lib/32/ld-linux.so.2 > $out/nix-support/dynamic-linker-m32
fi
touch $out/nix-support/ld-set-dynamic-linker

fi
printWords {bt} {libc} > $out/nix-support/propagated-user-env-packages
export hardening_unsupported_flags=""
if [[ "$($ldPath/ld -z now 2>&1 || true)" =~ un(recognized|known)\\ option ]]; then
  hardening_unsupported_flags+=" bindnow"
fi
if [[ "$($ldPath/ld -z relro 2>&1 || true)" =~ un(recognized|known)\\ option ]]; then
  hardening_unsupported_flags+=" relro"
fi
wrap strip {STRIP_WRAPPER_SH} \\
  "{bt}/bin/strip"
for flags in "$out/nix-support"/*flags*; do
  substituteInPlace "$flags" --replace $'\\n' ' '
done

substituteAll {BINTOOLS_ADD_FLAGS} $out/nix-support/add-flags.sh
substituteAll {BINTOOLS_ADD_HARDENING} $out/nix-support/add-hardening.sh
substituteAll {UTILS_BASH} $out/nix-support/utils.bash
substituteAll {DARWIN_SDK_SETUP_BASH} $out/nix-support/darwin-sdk-setup.bash
""",
            "preferLocalBuild": "1",
            "rm": f"{bt}/bin/rm",
            "setupHooks": f"{ROLE_BASH} {BINTOOLS_SETUP_HOOK}",
            "shell": f"{bt}/bin/bash",
            "strictDeps": "1",
            "suffixSalt": "x86_64_unknown_linux_gnu",
            "targetPrefix": "",
            "unpackPhase": "src=$PWD\n",
            "version": "",
            "wrapperName": "BINTOOLS_WRAPPER",
        },
    )
