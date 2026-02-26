"""Build all 196 derivations in nixpkgs#hello's closure from .drv files.

The nixpkgs bootstrap rebuilds many packages across 7 stages (bash 5x,
gnu-config 6x, etc.). Rather than hand-writing Python for each stage variant,
this module reads the real .drv files and reconstructs Package objects using
``drv()`` directly. The test suite proves byte-identical ATerm output.

Usage::

    from pixpkgs.bootstrap.closure import load_hello_closure, load_by_stage

    pkgs = load_hello_closure()          # {drv_path: Package}
    stages = load_by_stage(pkgs)         # {stage_name: {drv_path: Package}}
"""

import subprocess

from pix.derivation import parse, serialize
from pixpkgs.drv import Package, drv


def package_from_drv(drv_path: str, dep_packages: dict[str, Package]) -> Package:
    """Reconstruct a Package from a .drv file.

    Parses the .drv, extracts all metadata, and calls ``drv()`` with the
    correct args. Works for all derivation types: fetchurl, multi-output,
    fixed-output, setup hooks, stdenvs, and compiled packages.

    Args:
        drv_path: Nix store path of the .drv file.
        dep_packages: Already-built packages, keyed by drv_path.
            Only input_drvs present in this dict are included as deps.
    """
    parsed = parse(open(drv_path).read())
    is_fixed = (
        len(parsed.outputs) == 1
        and "out" in parsed.outputs
        and parsed.outputs["out"].hash_algo != ""
    )
    name = drv_path.rsplit("/", 1)[1].split("-", 1)[1][:-4]
    deps = [
        dep_packages[dp]
        for dp in sorted(parsed.input_drvs)
        if dp in dep_packages
    ]
    env = dict(parsed.env)
    for k in {"name", "builder", "system"}:
        env.pop(k, None)
    for oname in parsed.outputs:
        env.pop(oname, None)

    kwargs: dict = dict(
        name=name,
        builder=parsed.builder,
        system=parsed.platform,
        args=parsed.args if parsed.args else None,
        env=env if env else None,
        output_names=(
            sorted(parsed.outputs)
            if sorted(parsed.outputs) != ["out"]
            else None
        ),
        deps=deps if deps else None,
        srcs=parsed.input_srcs if parsed.input_srcs else None,
        input_drvs={dp: outs for dp, outs in parsed.input_drvs.items()},
    )
    if is_fixed:
        o = parsed.outputs["out"]
        algo = o.hash_algo
        if algo.startswith("r:"):
            kwargs["output_hash_mode"] = "recursive"
            algo = algo[2:]
        else:
            kwargs["output_hash_mode"] = "flat"
        kwargs["output_hash_algo"] = algo
        kwargs["output_hash"] = o.hash_value

    return drv(**kwargs)


def load_hello_closure() -> dict[str, Package]:
    """Build all derivations in nixpkgs#hello's closure.

    Uses ``nix-store --query --requisites`` for topological order (deps
    before dependents), then reconstructs each derivation with
    ``package_from_drv()``. Verifies byte-identical ATerm output.

    Returns:
        Dict mapping drv_path → Package for all ~196 derivations.

    Raises:
        RuntimeError: If any derivation fails to reconstruct or ATerm mismatches.
    """
    hello_drv = subprocess.run(
        ["nix", "eval", "nixpkgs#hello.drvPath", "--raw"],
        capture_output=True, text=True, check=True,
    ).stdout
    all_drvs = [
        line
        for line in subprocess.run(
            ["nix-store", "--query", "--requisites", hello_drv],
            capture_output=True, text=True, check=True,
        ).stdout.strip().split("\n")
        if line.endswith(".drv")
    ]

    packages: dict[str, Package] = {}
    failures: list[str] = []
    for drv_path in all_drvs:
        try:
            pkg = package_from_drv(drv_path, packages)
            actual = serialize(pkg.drv)
            expected = open(drv_path).read()
            if actual == expected:
                packages[drv_path] = pkg
            else:
                name = drv_path.rsplit("/", 1)[1]
                failures.append(f"ATerm mismatch: {name}")
        except Exception as e:
            name = drv_path.rsplit("/", 1)[1]
            failures.append(f"{name}: {e}")

    if failures:
        raise RuntimeError(
            f"{len(failures)}/{len(all_drvs)} derivations failed:\n"
            + "\n".join(failures[:10])
        )
    return packages


def load_by_stage(
    pkgs: dict[str, Package],
) -> dict[str, dict[str, Package]]:
    """Classify packages by which bootstrap stage built them.

    Groups by the ``stdenv`` env var path. Fetchurl derivations (builder
    ``builtin:fetchurl``) get their own bucket.
    """
    stages: dict[str, dict[str, Package]] = {}
    for drv_path, pkg in pkgs.items():
        env = pkg.drv.env
        builder = pkg.drv.builder
        stdenv = env.get("stdenv", "")

        if builder == "builtin:fetchurl":
            stage = "fetchurl"
        elif "stage0-stdenv" in stdenv:
            stage = "built-by-stage0"
        elif "stage1-stdenv" in stdenv and "stage1-stdenv" not in drv_path:
            stage = "built-by-stage1"
        elif "stage-xgcc-stdenv" in stdenv:
            stage = "built-by-xgcc"
        elif "stage2-stdenv" in stdenv:
            stage = "built-by-stage2"
        elif "stage3-stdenv" in stdenv:
            stage = "built-by-stage3"
        elif "stage4-stdenv" in stdenv:
            stage = "built-by-stage4"
        elif "stdenv-linux" in stdenv and "bootstrap" not in stdenv:
            stage = "built-by-final"
        else:
            # Infrastructure: stdenvs themselves, bootstrap-tools, busybox
            name = drv_path.rsplit("/", 1)[1].split("-", 1)[1][:-4]
            if "stdenv" in name:
                stage = "infra-stdenv"
            else:
                stage = "infra-other"

        stages.setdefault(stage, {})[drv_path] = pkg
    return stages
