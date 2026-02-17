"""High-level derivation constructor.

Wraps pix's low-level Derivation/store_path/hash primitives into a
single drv() call that handles the full pipeline:

    drv(name="hello", builder="/bin/sh", args=["-c", "echo hi > $out"])

This is the Python equivalent of stdenv.mkDerivation — it takes
readable arguments and produces a Package with computed output paths
and a .drv store path, ready to be realized.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any

from pix.derivation import (
    Derivation,
    DerivationOutput,
    hash_derivation_modulo,
    serialize,
)
from pix.store_path import make_output_path, make_text_store_path


def _collect_input_hashes(deps: list[Package], drv_hashes: dict[str, bytes]) -> None:
    """Recursively compute modular hashes for all deps with mask_outputs=False.

    Mirrors Nix's pathDerivationModulo: input derivation hashes include
    their filled output paths (maskOutputs=false), unlike the top-level
    derivation whose outputs are blanked.
    """
    for dep in deps:
        if dep.drv_path in drv_hashes:
            continue
        # Process sub-deps first
        _collect_input_hashes(dep._args.get("deps") or [], drv_hashes)
        drv_hashes[dep.drv_path] = hash_derivation_modulo(
            dep.drv, drv_hashes, mask_outputs=False,
        )


@dataclass(frozen=True)
class Package:
    """A fully resolved derivation with computed output paths.

    Use str(pkg) or f"{pkg}" to get the default output path —
    this mirrors Nix's string interpolation context tracking.
    """

    name: str
    drv: Derivation
    drv_path: str
    outputs: dict[str, str]
    _args: dict[str, Any]  # original drv() kwargs, for override()

    @property
    def out(self) -> str:
        return self.outputs["out"]

    def __str__(self) -> str:
        return self.out

    def override(self, **kw) -> Package:
        """Re-derive with changed arguments. Like pkg.override in Nix."""
        return drv(**{**self._args, **kw})


def drv(
    name: str,
    builder: str,
    system: str = "x86_64-linux",
    args: list[str] | None = None,
    env: dict[str, str] | None = None,
    output_names: list[str] | None = None,
    deps: list[Package] | None = None,
    srcs: list[str] | None = None,
) -> Package:
    """Create a Package with computed output paths and .drv store path.

    Args:
        name:         Package name (becomes the store path suffix).
        builder:      Path to the builder executable.
        system:       Build platform (default: x86_64-linux).
        args:         Arguments to the builder.
        env:          Extra environment variables.
        output_names: Output names (default: ["out"]).
        deps:         Package dependencies (input derivations).
        srcs:         Input source store paths.
    """
    args = args or []
    env = dict(env or {})
    output_names = output_names or ["out"]
    deps = deps or []
    srcs = srcs or []

    # Save original kwargs for override()
    orig_args = dict(
        name=name, builder=builder, system=system, args=args,
        env=env, output_names=output_names, deps=deps, srcs=srcs,
    )

    # Collect input derivations from deps
    input_drvs: dict[str, list[str]] = {}
    for dep in deps:
        input_drvs[dep.drv_path] = list(dep.outputs.keys())

    # Step 1: Create derivation with blank output paths
    outputs = {n: DerivationOutput("", "", "") for n in output_names}
    drv_obj = Derivation(
        outputs=outputs,
        input_drvs=input_drvs,
        input_srcs=sorted(srcs),
        platform=system,
        builder=builder,
        args=args,
        env=env,
    )

    # Auto-add standard env vars (like Nix does)
    drv_obj.env.setdefault("name", name)
    drv_obj.env.setdefault("builder", builder)
    drv_obj.env.setdefault("system", system)
    for n in output_names:
        drv_obj.env.setdefault(n, "")  # placeholder, filled below

    # Step 2: Compute hashDerivationModulo
    # Collect hashes of input derivations with mask_outputs=False.
    # Nix's pathDerivationModulo uses maskOutputs=false: the dep's filled
    # output paths are part of the hash. Only the current derivation's
    # own outputs are blanked (mask_outputs=True) to break circularity.
    drv_hashes: dict[str, bytes] = {}
    _collect_input_hashes(deps, drv_hashes)

    drv_hash = hash_derivation_modulo(drv_obj, drv_hashes)

    # Step 3: Compute output paths
    computed_outputs = {}
    for n in output_names:
        computed_outputs[n] = make_output_path(drv_hash, n, name)

    # Step 4: Fill output paths into derivation
    for n, path in computed_outputs.items():
        drv_obj.outputs[n] = DerivationOutput(path, "", "")
        drv_obj.env[n] = path

    # Step 5-6: Serialize and compute .drv store path
    drv_text = serialize(drv_obj)
    refs = sorted(input_drvs.keys()) + sorted(srcs)
    drv_store_path = make_text_store_path(name + ".drv", drv_text.encode(), refs)

    return Package(
        name=name,
        drv=drv_obj,
        drv_path=drv_store_path,
        outputs=computed_outputs,
        _args=orig_args,
    )
