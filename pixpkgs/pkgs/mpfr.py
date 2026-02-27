"""mpfr — GNU Multiple Precision Floating-Point Reliable Library.

Like nixpkgs/pkgs/by-name/mp/mpfr/package.nix — multi-precision
floating-point arithmetic with correct rounding, built on GMP.

Source (nixpkgs master)::

    { lib, stdenv, fetchurl, gmp, writeScript, updateAutotoolsGnuConfigScriptsHook }:
    stdenv.mkDerivation rec {
      version = "4.2.2";
      pname = "mpfr";
      src = fetchurl { urls = ["https://www.mpfr.org/..."  "mirror://gnu/mpfr/..."]; hash = "sha256-..."; };
      outputs = ["out" "dev" "doc" "info"];
      strictDeps = true;
      nativeBuildInputs = [ updateAutotoolsGnuConfigScriptsHook ];
      propagatedBuildInputs = [ gmp ];
      hardeningDisable = [ "trivialautovarinit" ];  # causes test failures
      configureFlags = lib.optional stdenv.hostPlatform.is64bit "--with-pic";
      doCheck = true;
      enableParallelBuilding = true;
    }

How make-derivation.nix transforms these attrs:
  - outputs = ["out" "dev" "doc" "info"] → env "outputs" = "out dev doc info"
  - hardeningDisable = ["trivialautovarinit"] → triggers NIX_HARDENING_ENABLE
    Since trivialautovarinit is NOT in the 12 default hardening flags (from
    bintools-wrapper), subtractLists is a no-op. NIX_HARDENING_ENABLE = all 12.
  - propagatedBuildInputs = [gmp] → getDev applied by make-derivation.nix →
    env "propagatedBuildInputs" = gmp.dev path (not gmp.out!).
    make-derivation.nix applies getDev to ALL dependency lists.
  - hardeningDisable = ["trivialautovarinit"] → env "hardeningDisable" = "trivialautovarinit"
    (the list is stringified; the attr also passes through to the env)
  - configureFlags on x86_64-linux (is64bit, not SunOS, not Power64): ["--with-pic"]
  - configurePlatforms: empty for native builds → no auto --build=/--host=
  - enableParallelBuilding = true → null-key pattern → "1" for all three
"""

from pixpkgs.drv import Package
from pixpkgs.mk_derivation import mk_derivation

# 12 default hardening flags from bintools-wrapper/default.nix.
# hardeningDisable = ["trivialautovarinit"] triggers NIX_HARDENING_ENABLE,
# but trivialautovarinit isn't in these defaults so nothing is subtracted.
DEFAULT_HARDENING_FLAGS = (
    "bindnow format fortify fortify3"
    " libcxxhardeningextensive libcxxhardeningfast"
    " pic relro stackclashprotection stackprotector"
    " strictoverflow zerocallusedregs"
)


def make_mpfr(
    bootstrap_tools: Package,
    stdenv: Package,
    src: Package,
    gmp: Package,
    update_autotools_hook: Package,
) -> Package:
    """Build MPFR 4.2.2 (multi-precision floating-point).

    Args:
        bootstrap_tools: Bootstrap-tools (provides builder shell).
        stdenv: The xgcc stdenv.
        src: mpfr-4.2.2.tar.xz (fetchurl).
        gmp: GMP library (propagated build input).
        update_autotools_hook: updateAutotoolsGnuConfigScriptsHook.
    """
    bt = str(bootstrap_tools)

    # make-derivation.nix applies getDev to all dependency lists.
    # For gmp (outputs: out/dev/info), getDev returns gmp.dev.
    # So propagatedBuildInputs references gmp's "dev" output, and
    # input_drvs should list only ["dev"] for gmp.
    gmp_dev = gmp.outputs["dev"]
    input_drvs = {gmp.drv_path: ["dev"]}

    return mk_derivation(
        pname="mpfr",
        version="4.2.2",
        builder=f"{bt}/bin/bash",
        stdenv=stdenv,
        output_names=["out", "dev", "doc", "info"],
        deps=[bootstrap_tools, src, gmp, update_autotools_hook],
        input_drvs=input_drvs,
        env={
            "NIX_HARDENING_ENABLE": DEFAULT_HARDENING_FLAGS,
            "configureFlags": "--with-pic",
            "doCheck": "1",
            "enableParallelBuilding": "1",
            "enableParallelChecking": "1",
            "enableParallelInstalling": "1",
            "hardeningDisable": "trivialautovarinit",
            "nativeBuildInputs": str(update_autotools_hook),
            "propagatedBuildInputs": gmp_dev,
            "src": str(src),
            "strictDeps": "1",
        },
    )
