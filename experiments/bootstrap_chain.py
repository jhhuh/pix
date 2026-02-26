"""Reconstruct the full nixpkgs bootstrap chain (196 derivations → hello).

Reads .drv files from the Nix store, reconstructs hash-identical Package
objects via drv(), and groups them by bootstrap stage. This is the shared
infrastructure for all overlay experiments.

Stage grouping uses closure set-differences:
  stage_N_new = closure(stdenv_N) - closure(stdenv_{N-1})
This correctly handles packages that are rebuilt in later stages.

Usage:
    chain = load_chain()
    chain.packages["/nix/store/...-hello-2.12.2.drv"]  # any of 196 packages
    chain.stages[0]  # list of drv_paths new in stage0
    chain.hello       # the hello Package
"""

import subprocess
from dataclasses import dataclass

from pix.derivation import parse, serialize
from pixpkgs.drv import drv, Package


# --- Stage stdenv .drv paths (from nixpkgs master, Nix 2.28) ---

STAGE_STDENVS = [
    ("stage0", "/nix/store/ydld0fh638kgppqrfx30fr205wiab9ja-bootstrap-stage0-stdenv-linux.drv"),
    ("stage1", "/nix/store/df3ibqm3m62scbv1j0yahsrydfhmdslj-bootstrap-stage1-stdenv-linux.drv"),
    ("stage_xgcc", "/nix/store/kpb871v49izkzs3z4pbd6ayrg1x3q0ak-bootstrap-stage-xgcc-stdenv-linux.drv"),
    ("stage2", "/nix/store/nl1yq6cf36l9f3y2y13zjfv89j89rf0r-bootstrap-stage2-stdenv-linux.drv"),
    ("stage3", "/nix/store/q9fp5if7d83spgfchn5gl20l6j7gynkk-bootstrap-stage3-stdenv-linux.drv"),
    ("stage4", "/nix/store/zz73z016vvf26mz6sxvxsbwa43s2ghw2-bootstrap-stage4-stdenv-linux.drv"),
    ("final", "/nix/store/gcm3x4yxwc0wzcgvhb6msyqnbd6afh2w-stdenv-linux.drv"),
]

HELLO_DRV = "/nix/store/8vsr43y1hyqahxxrphgrcg2039jjzjq0-hello-2.12.2.drv"
HELLO_OUT = "/nix/store/bgcw8smdrjxcgv1g32nhpip31nk7x9mj-hello-2.12.2"


@dataclass
class Chain:
    """The full bootstrap chain: 196 derivations grouped by stage."""
    packages: dict[str, Package]   # drv_path -> Package (all 196)
    stages: list[list[str]]        # 8 lists of drv_paths (7 stages + hello-only)
    stage_names: list[str]         # ["stage0", "stage1", ..., "final", "hello"]

    @property
    def hello(self) -> Package:
        return self.packages[HELLO_DRV]


def make_package_from_drv(drv_path: str, dep_packages: dict[str, Package]) -> Package:
    """Read a .drv file and reconstruct a matching Package using drv().

    This is the generic reconstruction engine. Given a .drv path and a dict
    of already-reconstructed dependency Packages, it parses the ATerm,
    extracts all parameters, and calls drv() to produce a hash-identical Package.

    The dep_packages dict must contain all input derivations that have already
    been processed (topological order guarantees this).
    """
    drv_text = open(drv_path).read()
    parsed = parse(drv_text)
    is_fixed = (len(parsed.outputs) == 1 and "out" in parsed.outputs
                and parsed.outputs["out"].hash_algo != "")
    name = drv_path.rsplit("/", 1)[1].split("-", 1)[1][:-4]
    deps = [dep_packages[dp] for dp in sorted(parsed.input_drvs) if dp in dep_packages]
    env = dict(parsed.env)
    for k in {"name", "builder", "system"}:
        env.pop(k, None)
    for oname in parsed.outputs:
        env.pop(oname, None)
    kwargs = dict(
        name=name, builder=parsed.builder, system=parsed.platform,
        args=parsed.args if parsed.args else None,
        env=env if env else None,
        output_names=sorted(parsed.outputs) if sorted(parsed.outputs) != ["out"] else None,
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


def _get_closure(drv_path: str) -> set[str]:
    """Get the .drv closure of a store path via nix-store --requisites."""
    result = subprocess.run(
        ["nix-store", "--query", "--requisites", drv_path],
        capture_output=True, text=True, check=True,
    )
    return set(l for l in result.stdout.strip().split("\n") if l.endswith(".drv"))


def _get_hello_drv_paths() -> list[str]:
    """Get all 196 .drv paths in hello's closure, topologically ordered."""
    result = subprocess.run(
        ["nix-store", "--query", "--requisites", HELLO_DRV],
        capture_output=True, text=True, check=True,
    )
    return [l for l in result.stdout.strip().split("\n") if l.endswith(".drv")]


def _group_by_stage(all_drv_paths: list[str]) -> tuple[list[list[str]], list[str]]:
    """Group drv_paths by bootstrap stage using closure set-differences.

    Returns (stages, stage_names) where stages is a list of 8 drv_path lists
    and stage_names is ["stage0", "stage1", ..., "final", "hello"].
    """
    # Compute closure for each stage's stdenv
    stage_closures = []
    for name, stdenv_drv in STAGE_STDENVS:
        stage_closures.append((name, _get_closure(stdenv_drv)))

    # Compute hello closure
    hello_closure = set(all_drv_paths)

    # Group by set difference: new_in_stage_N = closure(N) - closure(N-1)
    stages = []
    stage_names = []
    prev_closure = set()
    for name, closure in stage_closures:
        new_drvs = closure - prev_closure
        # Preserve topological order from the original list
        ordered = [dp for dp in all_drv_paths if dp in new_drvs]
        stages.append(ordered)
        stage_names.append(name)
        prev_closure = closure

    # hello-only: derivations beyond the final stdenv's closure
    hello_only = hello_closure - prev_closure
    ordered = [dp for dp in all_drv_paths if dp in hello_only]
    stages.append(ordered)
    stage_names.append("hello")

    return stages, stage_names


def load_chain() -> Chain:
    """Load the full bootstrap chain from the Nix store.

    Reconstructs all 196 derivations in nixpkgs#hello's closure using
    make_package_from_drv(), groups them by bootstrap stage, and returns
    a Chain object.

    Requires: .drv files present in /nix/store (run `nix eval nixpkgs#hello`
    to ensure they're available).
    """
    all_drv_paths = _get_hello_drv_paths()
    assert len(all_drv_paths) > 100, f"Expected 100+ derivations, got {len(all_drv_paths)}"

    # Reconstruct all packages in topological order
    packages = {}
    for drv_path in all_drv_paths:
        pkg = make_package_from_drv(drv_path, packages)
        # Verify byte-identical ATerm
        assert serialize(pkg.drv) == open(drv_path).read(), \
            f"ATerm mismatch: {drv_path.rsplit('/', 1)[1]}"
        packages[drv_path] = pkg

    # Group by stage
    stages, stage_names = _group_by_stage(all_drv_paths)

    return Chain(packages=packages, stages=stages, stage_names=stage_names)


# Cached singleton — loading is expensive (~2s), reuse across tests
_cached_chain: Chain | None = None


def get_chain() -> Chain:
    """Get the cached bootstrap chain (loads on first call)."""
    global _cached_chain
    if _cached_chain is None:
        _cached_chain = load_chain()
    return _cached_chain
