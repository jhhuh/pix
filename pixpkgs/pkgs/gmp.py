"""gmp — GNU Multiple Precision Arithmetic Library.

Like nixpkgs/pkgs/development/libraries/gmp/6.x.nix with cxx=false
(bootstrap variant, no C++ bindings to avoid libstdc++ dependency).

Source (nixpkgs master)::

    { stdenv, fetchurl, m4, cxx ? ..., buildPackages, withStatic ? ... }:
    stdenv.mkDerivation rec {
      pname = "gmp";  # cxx=false → no "-with-cxx" suffix
      version = "6.3.0";
      src = fetchurl { urls = ["mirror://gnu/gmp/..."]; hash = "sha256-..."; };
      outputs = ["out" "dev" "info"];
      strictDeps = true;
      depsBuildBuild = [ buildPackages.stdenv.cc ];
      nativeBuildInputs = [ m4 ];
      configureFlags = [
        "--with-pic"
        # gcc-15 has c23 standard by default, where "void foo()" now means
        # "void foo(void)". The configure script relies on c17-and-below
        # semantics for "long long reliability test 1" (aclocal.m4).
        "CFLAGS=-std=c99"
        "--disable-cxx"  # lib.enableFeature false "cxx"
        "--enable-fat"   # x86_64, not SunOS, not Darwin
        "--build=x86_64-unknown-linux-gnu"
      ];
      doCheck = true;
      dontDisableStatic = withStatic;  # false on x86_64-linux
      enableParallelBuilding = true;
    }

How make-derivation.nix transforms these attrs:
  - outputs = ["out" "dev" "info"] → env "outputs" = "out dev info"
  - strictDeps = true → env "strictDeps" = "1"
  - depsBuildBuild = [cc] → env "depsBuildBuild" = cc store path
  - nativeBuildInputs = [m4] → env "nativeBuildInputs" = m4 store path
  - configureFlags list → env "configureFlags" = space-separated string
  - doCheck = true → env "doCheck" = "1"
  - dontDisableStatic = false → env "dontDisableStatic" = ""
  - enableParallelBuilding = true → null-key pattern → env "1" for all three
  - no meta.mainProgram → no NIX_MAIN_PROGRAM
"""

from pixpkgs.drv import Package
from pixpkgs.mk_derivation import mk_derivation


def make_gmp(
    bootstrap_tools: Package,
    stdenv: Package,
    src: Package,
    gcc_wrapper: Package,
    gnum4: Package,
) -> Package:
    """Build GMP 6.3.0 (cxx=false for bootstrap).

    Args:
        bootstrap_tools: Bootstrap-tools (provides builder shell).
        stdenv: The xgcc stdenv.
        src: gmp-6.3.0.tar.bz2 (fetchurl).
        gcc_wrapper: buildPackages.stdenv.cc (the xgcc gcc wrapper).
        gnum4: GNU m4 (nativeBuildInput).
    """
    bt = str(bootstrap_tools)

    return mk_derivation(
        pname="gmp",
        version="6.3.0",
        builder=f"{bt}/bin/bash",
        stdenv=stdenv,
        output_names=["out", "dev", "info"],
        deps=[bootstrap_tools, src, gcc_wrapper, gnum4],
        env={
            "configureFlags": "--with-pic CFLAGS=-std=c99 --disable-cxx --enable-fat --build=x86_64-unknown-linux-gnu",
            "depsBuildBuild": str(gcc_wrapper),
            "doCheck": "1",
            "dontDisableStatic": "",
            "enableParallelBuilding": "1",
            "enableParallelChecking": "1",
            "enableParallelInstalling": "1",
            "nativeBuildInputs": str(gnum4),
            "src": str(src),
            "strictDeps": "1",
        },
    )
