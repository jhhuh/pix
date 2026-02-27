"""libmpc — GNU MPC (Multiple Precision Complex arithmetic).

Like nixpkgs/pkgs/by-name/li/libmpc/package.nix — complex arithmetic
with correct rounding, built on GMP and MPFR.

Source (nixpkgs master)::

    { lib, stdenv, fetchurl, gmp, mpfr, updateAutotoolsGnuConfigScriptsHook }:
    stdenv.mkDerivation rec {
      pname = "libmpc";
      version = "1.3.1";
      src = fetchurl { url = "mirror://gnu/mpc/mpc-1.3.1.tar.gz"; sha256 = "..."; };
      strictDeps = true;
      enableParallelBuilding = true;
      buildInputs = [ gmp mpfr ];
      nativeBuildInputs = [ updateAutotoolsGnuConfigScriptsHook ];
      doCheck = true;
    }

How make-derivation.nix transforms these attrs:
  - buildInputs = [gmp mpfr] → getDev applied → gmp.dev + mpfr.dev paths
  - input_drvs: gmp["dev"], mpfr["dev"]
  - Single output ("out")
  - No hardeningDisable → no NIX_HARDENING_ENABLE
"""

from pixpkgs.drv import Package
from pixpkgs.mk_derivation import mk_derivation


def make_libmpc(
    bootstrap_tools: Package,
    stdenv: Package,
    src: Package,
    gmp: Package,
    mpfr: Package,
    update_autotools_hook: Package,
) -> Package:
    """Build libmpc 1.3.1 (multiprecision complex arithmetic).

    Args:
        bootstrap_tools: Bootstrap-tools (provides builder shell).
        stdenv: The xgcc stdenv.
        src: mpc-1.3.1.tar.gz (fetchurl).
        gmp: GMP library (build input — getDev yields gmp.dev).
        mpfr: MPFR library (build input — getDev yields mpfr.dev).
        update_autotools_hook: updateAutotoolsGnuConfigScriptsHook.
    """
    bt = str(bootstrap_tools)

    # make-derivation.nix applies getDev to ALL dependency lists.
    # Both gmp and mpfr are multi-output; getDev returns their "dev" output.
    gmp_dev = gmp.outputs["dev"]
    mpfr_dev = mpfr.outputs["dev"]
    input_drvs = {
        gmp.drv_path: ["dev"],
        mpfr.drv_path: ["dev"],
    }

    return mk_derivation(
        pname="libmpc",
        version="1.3.1",
        builder=f"{bt}/bin/bash",
        stdenv=stdenv,
        output_names=["out"],
        deps=[bootstrap_tools, src, gmp, mpfr, update_autotools_hook],
        input_drvs=input_drvs,
        env={
            "buildInputs": f"{gmp_dev} {mpfr_dev}",
            "doCheck": "1",
            "enableParallelBuilding": "1",
            "enableParallelChecking": "1",
            "enableParallelInstalling": "1",
            "nativeBuildInputs": str(update_autotools_hook),
            "src": str(src),
            "strictDeps": "1",
        },
    )
