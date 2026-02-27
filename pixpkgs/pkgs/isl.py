"""isl — Integer Set Library (for GCC Graphite optimization).

Like nixpkgs/pkgs/development/libraries/isl/generic.nix + 0.20.0.nix:
GCC uses isl 0.20 for its Graphite loop optimization framework.
The bootstrap variant has no depsBuildBuild (version 0.20 < 0.23).

Source (nixpkgs, generic.nix called from 0.20.0.nix)::

    stdenv.mkDerivation {
      pname = "isl";
      version = "0.20";
      src = fetchurl { urls = [...]; sha256 = "1akpgq0rbqbah5517blg2zlnfvjxfcl9cjrfc75nbcx5p2gnlnd5"; };
      strictDeps = true;
      # depsBuildBuild = []; # version 0.20 < 0.23 threshold
      nativeBuildInputs = [ updateAutotoolsGnuConfigScriptsHook ];
      buildInputs = [ gmp ];
      configureFlags = [ "--with-gcc-arch=generic" ];
      enableParallelBuilding = true;
    }

How make-derivation.nix transforms these attrs:
  - outputs defaults to ["out"] → single output
  - buildInputs = [gmp] → getDev applied → env "buildInputs" = gmp.dev path
  - enableParallelBuilding = true → null-key pattern → "1" for all three
  - no doCheck → default "" (unlike gmp/mpfr which set doCheck = true)
  - no hardeningDisable → no NIX_HARDENING_ENABLE env var
"""

from pixpkgs.drv import Package
from pixpkgs.mk_derivation import mk_derivation


def make_isl(
    bootstrap_tools: Package,
    stdenv: Package,
    src: Package,
    gmp: Package,
    update_autotools_hook: Package,
) -> Package:
    """Build isl 0.20 (integer set library for GCC Graphite).

    Args:
        bootstrap_tools: Bootstrap-tools (provides builder shell).
        stdenv: The xgcc stdenv.
        src: isl-0.20.tar.xz (fetchurl).
        gmp: GMP library (build input — getDev yields gmp.dev).
        update_autotools_hook: updateAutotoolsGnuConfigScriptsHook.
    """
    bt = str(bootstrap_tools)

    # make-derivation.nix applies getDev to ALL dependency lists.
    # For gmp (outputs: out/dev/info), getDev returns gmp.dev.
    # So buildInputs references gmp's "dev" output.
    gmp_dev = gmp.outputs["dev"]
    input_drvs = {gmp.drv_path: ["dev"]}

    return mk_derivation(
        pname="isl",
        version="0.20",
        builder=f"{bt}/bin/bash",
        stdenv=stdenv,
        output_names=["out"],
        deps=[bootstrap_tools, src, gmp, update_autotools_hook],
        input_drvs=input_drvs,
        env={
            "buildInputs": gmp_dev,
            "configureFlags": "--with-gcc-arch=generic",
            "enableParallelBuilding": "1",
            "enableParallelChecking": "1",
            "enableParallelInstalling": "1",
            "nativeBuildInputs": str(update_autotools_hook),
            "src": str(src),
            "strictDeps": "1",
        },
    )
