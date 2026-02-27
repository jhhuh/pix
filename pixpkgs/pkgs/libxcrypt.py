"""libxcrypt — Extended crypt library.

Like nixpkgs/pkgs/development/libraries/libxcrypt/default.nix — provides
crypt(3) implementations (yescrypt, bcrypt, sha512crypt, etc.) as a
replacement for glibc's libcrypt.

Source (nixpkgs, bootstrap version 4.5.2)::

    stdenv.mkDerivation {
      pname = "libxcrypt";
      version = "4.5.2";
      src = fetchurl { ... };
      postPatch = ''
        substituteInPlace ./build-aux/m4-autogen/config.guess --replace-fail /usr/bin/uname uname
      '';
      outputs = [ "out" "man" ];
      configureFlags = [
        "--enable-hashes=strong" "--enable-obsolete-api=glibc"
        "--disable-failure-tokens" "--disable-werror"
      ];
      makeFlags = [];  # empty on x86_64-linux (non-windows, non-lld17+)
      nativeBuildInputs = [ perl ];
      enableParallelBuilding = true;
      doCheck = true;
    }

Note: uses postPatch instead of updateAutotoolsGnuConfigScriptsHook
(the comment says "that causes infinite recursion").
No strictDeps (empty, not "1").
"""

from pixpkgs.drv import Package
from pixpkgs.mk_derivation import mk_derivation


def make_libxcrypt(
    bootstrap_tools: Package,
    stdenv: Package,
    src: Package,
    perl: Package,
) -> Package:
    """Build libxcrypt 4.5.2 (extended crypt library).

    Args:
        bootstrap_tools: Bootstrap-tools (provides builder shell).
        stdenv: The xgcc stdenv.
        src: libxcrypt-4.5.2.tar.xz (fetchurl).
        perl: Perl (nativeBuildInput, for build scripts).
    """
    bt = str(bootstrap_tools)

    # Perl is multi-output (out/man/devdoc), but nativeBuildInputs
    # references only perl.out (getDev returns perl itself since there's
    # no "dev" output). Override input_drvs to select only ["out"].
    input_drvs = {perl.drv_path: ["out"]}

    return mk_derivation(
        pname="libxcrypt",
        version="4.5.2",
        builder=f"{bt}/bin/bash",
        stdenv=stdenv,
        output_names=["out", "man"],
        deps=[bootstrap_tools, src, perl],
        input_drvs=input_drvs,
        env={
            "configureFlags": "--enable-hashes=strong --enable-obsolete-api=glibc --disable-failure-tokens --disable-werror",
            "doCheck": "1",
            "enableParallelBuilding": "1",
            "enableParallelChecking": "1",
            "enableParallelInstalling": "1",
            "makeFlags": "",
            "nativeBuildInputs": str(perl),
            "postPatch": "substituteInPlace ./build-aux/m4-autogen/config.guess --replace-fail /usr/bin/uname uname\n",
            "src": str(src),
        },
    )
