"""nixpkgs bootstrap chain: 7 stages → stdenv → hello.

Like nixpkgs/pkgs/stdenv/linux/default.nix, this package defines the bootstrap
as a chain of stages. Each stage is a class that overrides specific packages,
rebuilding them with the improved toolchain from the previous stage.

    Stage0 → Stage1 → StageXgcc → Stage2 → Stage3 → Stage4 → Final → Pkgs

Package definitions live in ``pixpkgs.pkgs.*`` (like nixpkgs ``pkgs/`` files).
Stage classes compose them via class inheritance (Pattern A from overlays.md).
"""

from pixpkgs.bootstrap.pkgs import Pkgs
from pixpkgs.bootstrap.stage0 import EXPECTED_STAGE0, Stage0
from pixpkgs.bootstrap.stage1 import EXPECTED_STAGE1, Stage1
from pixpkgs.bootstrap.stage_xgcc import EXPECTED_STAGE_XGCC, StageXgcc

__all__ = [
    "Stage0", "EXPECTED_STAGE0",
    "Stage1", "EXPECTED_STAGE1",
    "StageXgcc", "EXPECTED_STAGE_XGCC",
    "Pkgs",
]
