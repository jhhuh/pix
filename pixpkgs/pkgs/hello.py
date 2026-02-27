"""hello — GNU Hello.

Like nixpkgs/pkgs/by-name/he/hello/package.nix — the simplest GNU
autotools package. Uses the final stdenv (after all bootstrap stages).

Source (nixpkgs)::

    { stdenv, fetchurl, versionCheckHook, ... }:
    stdenv.mkDerivation (finalAttrs: {
      pname = "hello"; version = "2.12.2";
      src = fetchurl { url = "mirror://gnu/hello/..."; hash = "sha256-..."; };
      doCheck = true;
      doInstallCheck = true;
      nativeInstallCheckInputs = [ versionCheckHook ];
      postInstallCheck = 'stat "''${!outputBin}/bin/hello"';
      meta.mainProgram = "hello";
    })

How make-derivation.nix transforms these attrs:
  - doCheck = true → env "doCheck" = "1"  (lib.boolToString)
  - doInstallCheck = true → env "doInstallCheck" = "1"
  - nativeInstallCheckInputs → folded into nativeBuildInputs (when doInstallCheck)
  - meta.mainProgram → env "NIX_MAIN_PROGRAM" = "hello"
  - strictDeps not set → env "strictDeps" = ""  (null default)
  - env = {} on Linux (isDarwin guard) → no extra env vars
"""

from pixpkgs.drv import Package
from pixpkgs.mk_derivation import mk_derivation


def make_hello(
    bash: Package,
    stdenv: Package,
    src: Package,
    version_check_hook: Package,
) -> Package:
    """Build GNU Hello 2.12.2.

    Args:
        bash: Final bash (used as builder).
        stdenv: Final stdenv.
        src: hello-2.12.2.tar.gz (fetchurl).
        version_check_hook: Setup hook that adds installCheck.
    """
    # bash is multi-output (out, dev, man, doc, info, debug) but hello
    # only depends on bash's "out" output (for the builder binary).
    # Without this override, drv() would list all 6 outputs in input_drvs.
    input_drvs = {bash.drv_path: ["out"]}

    return mk_derivation(
        pname="hello",
        version="2.12.2",
        builder=f"{bash}/bin/bash",
        stdenv=stdenv,
        deps=[bash, src, version_check_hook],
        input_drvs=input_drvs,
        env={
            # meta.mainProgram = "hello" → make-derivation adds NIX_MAIN_PROGRAM
            "NIX_MAIN_PROGRAM": "hello",
            # doCheck = true → lib.boolToString → "1"
            "doCheck": "1",
            # doInstallCheck = true → lib.boolToString → "1"
            "doInstallCheck": "1",
            # nativeInstallCheckInputs = [ versionCheckHook ]
            # make-derivation folds into nativeBuildInputs when doInstallCheck
            "nativeBuildInputs": str(version_check_hook),
            # postInstallCheck = ''stat "''${!outputBin}/bin/${finalAttrs.meta.mainProgram}"'';
            # Nix '' '' strips indentation; finalAttrs.meta.mainProgram = "hello"
            "postInstallCheck": 'stat "${!outputBin}/bin/hello"\n',
            "src": str(src),
            # strictDeps not set → make-derivation defaults to ""
            "strictDeps": "",
        },
    )
