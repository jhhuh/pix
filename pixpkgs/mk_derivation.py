"""Python equivalent of stdenv.mkDerivation.

Like nixpkgs/pkgs/stdenv/generic/make-derivation.nix — wraps the raw
``drv()`` primitive with the standard env vars and builder pattern
that mkDerivation provides.

Every mkDerivation package uses:
    builder: <shell> -e source-stdenv.sh default-builder.sh
    source-stdenv.sh: sources $stdenv/setup then executes arg $1
    default-builder.sh: calls genericBuild

Usage::

    pkg = mk_derivation(
        pname="hello", version="2.12.2",
        builder=f"{bt}/bin/bash", stdenv=my_stdenv,
        deps=[my_stdenv], env={"src": str(some_source)},
    )
"""

from pixpkgs.drv import Package, drv
from pixpkgs.vendor import DEFAULT_BUILDER_SH, SOURCE_STDENV_SH

# Standard env vars that mkDerivation always sets.
# These are the "schema" — most are empty by default.
MKDERIVATION_DEFAULTS = {
    "__structuredAttrs": "",
    "buildInputs": "",
    "cmakeFlags": "",
    "configureFlags": "",
    "depsBuildBuild": "",
    "depsBuildBuildPropagated": "",
    "depsBuildTarget": "",
    "depsBuildTargetPropagated": "",
    "depsHostHost": "",
    "depsHostHostPropagated": "",
    "depsTargetTarget": "",
    "depsTargetTargetPropagated": "",
    "doCheck": "",
    "doInstallCheck": "",
    "mesonFlags": "",
    "nativeBuildInputs": "",
    "patches": "",
    "propagatedBuildInputs": "",
    "propagatedNativeBuildInputs": "",
}


def mk_derivation(
    *,
    builder: str,
    stdenv: Package,
    pname: str | None = None,
    version: str | None = None,
    name: str | None = None,
    deps: list[Package] | None = None,
    srcs: list[str] | None = None,
    env: dict[str, str] | None = None,
) -> Package:
    """Create a package using the stdenv mkDerivation pattern.

    Supports two naming conventions (like real mkDerivation):
      - ``pname`` + ``version``: name = "pname-version", both added to env
      - ``name`` directly: no pname/version env vars

    Args:
        builder: Path to the shell (e.g. "/nix/store/.../bin/bash").
        stdenv: The stdenv Package for this stage.
        pname: Package name (e.g. "hello"). Mutually exclusive with name.
        version: Package version (e.g. "2.12.2"). Requires pname.
        name: Direct derivation name. Mutually exclusive with pname.
        deps: Additional Package dependencies beyond stdenv.
        srcs: Additional input source store paths.
        env: Package-specific env vars (override defaults).
    """
    if name is not None:
        drv_name = name
    elif pname is not None:
        drv_name = f"{pname}-{version or ''}"
    else:
        raise ValueError("either name or pname is required")

    all_srcs = sorted({SOURCE_STDENV_SH, DEFAULT_BUILDER_SH, *(srcs or [])})
    all_deps = [stdenv] + (deps or [])

    merged_env = dict(MKDERIVATION_DEFAULTS)
    merged_env["outputs"] = "out"
    merged_env["stdenv"] = str(stdenv)
    if pname is not None:
        merged_env["pname"] = pname
        merged_env["version"] = version or ""
    if env:
        merged_env.update(env)

    return drv(
        name=drv_name,
        builder=builder,
        system="x86_64-linux",
        args=["-e", SOURCE_STDENV_SH, DEFAULT_BUILDER_SH],
        deps=all_deps,
        srcs=all_srcs,
        env=merged_env,
    )
