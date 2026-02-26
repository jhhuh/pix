"""Full 7-stage bootstrap using class inheritance.

Each stage is a class inheriting from the previous. Packages within each
stage are reconstructed from real nixpkgs .drv files. The class hierarchy
manages stage composition:

    Stage0 → Stage1 → StageXgcc → Stage2 → Stage3 → Stage4 → Final → Pkgs

Key mechanics:
    self        = final (late-bound via MRO — packages see the latest overrides)
    self._prev  = prev stage instance (breaks cycles for build dependencies)
    all_packages = accumulated dict of all packages up to this stage

Stage grouping uses closure set-differences: new packages in stage N are
those in closure(stdenv_N) but not in closure(stdenv_{N-1}).

The overlay pattern is demonstrated by the class hierarchy structure.
Individual package construction uses make_package_from_drv() — reading
.drv files from the Nix store ensures hash-perfect match with nixpkgs.
"""

from functools import cached_property

from pixpkgs.drv import Package
from experiments.a_class_inherit.pkgset import PackageSet
from experiments.bootstrap_chain import get_chain, HELLO_DRV


class Stage0(PackageSet):
    """Bootstrap seed: busybox, tarball, bootstrap-tools, stage0-stdenv (4 packages)."""

    @cached_property
    def _own_packages(self) -> dict[str, Package]:
        chain = get_chain()
        return {dp: chain.packages[dp] for dp in chain.stages[0]}

    @cached_property
    def all_packages(self) -> dict[str, Package]:
        return dict(self._own_packages)


class Stage1(Stage0):
    """Binutils wrapper, glibc bootstrapFiles, gcc wrapper, gnu-config (8 packages)."""

    @cached_property
    def _prev(self) -> Stage0:
        return Stage0()

    @cached_property
    def _own_packages(self) -> dict[str, Package]:
        chain = get_chain()
        return {dp: chain.packages[dp] for dp in chain.stages[1]}

    @cached_property
    def all_packages(self) -> dict[str, Package]:
        return {**self._prev.all_packages, **self._own_packages}


class StageXgcc(Stage1):
    """First real GCC (xgcc), gmp, mpfr, isl, libmpc (6 packages)."""

    @cached_property
    def _prev(self) -> Stage1:
        return Stage1()

    @cached_property
    def _own_packages(self) -> dict[str, Package]:
        chain = get_chain()
        return {dp: chain.packages[dp] for dp in chain.stages[2]}

    @cached_property
    def all_packages(self) -> dict[str, Package]:
        return {**self._prev.all_packages, **self._own_packages}


class Stage2(StageXgcc):
    """Glibc transition: glibc-2.40, binutils, bison, perl, xgcc rebuild (44 packages)."""

    @cached_property
    def _prev(self) -> StageXgcc:
        return StageXgcc()

    @cached_property
    def _own_packages(self) -> dict[str, Package]:
        chain = get_chain()
        return {dp: chain.packages[dp] for dp in chain.stages[3]}

    @cached_property
    def all_packages(self) -> dict[str, Package]:
        return {**self._prev.all_packages, **self._own_packages}


class Stage3(Stage2):
    """Compiler transition: final gcc-14.3.0, glibc-iconv, linux-headers (23 packages)."""

    @cached_property
    def _prev(self) -> Stage2:
        return Stage2()

    @cached_property
    def _own_packages(self) -> dict[str, Package]:
        chain = get_chain()
        return {dp: chain.packages[dp] for dp in chain.stages[4]}

    @cached_property
    def all_packages(self) -> dict[str, Package]:
        return {**self._prev.all_packages, **self._own_packages}


class Stage4(Stage3):
    """Tools transition: coreutils, bash, sed, grep, etc. (19 packages)."""

    @cached_property
    def _prev(self) -> Stage3:
        return Stage3()

    @cached_property
    def _own_packages(self) -> dict[str, Package]:
        chain = get_chain()
        return {dp: chain.packages[dp] for dp in chain.stages[5]}

    @cached_property
    def all_packages(self) -> dict[str, Package]:
        return {**self._prev.all_packages, **self._own_packages}


class Final(Stage4):
    """Production stdenv: all coreutils/findutils/gcc-wrapper rebuilt (63 packages)."""

    @cached_property
    def _prev(self) -> Stage4:
        return Stage4()

    @cached_property
    def _own_packages(self) -> dict[str, Package]:
        chain = get_chain()
        return {dp: chain.packages[dp] for dp in chain.stages[6]}

    @cached_property
    def all_packages(self) -> dict[str, Package]:
        return {**self._prev.all_packages, **self._own_packages}


class Pkgs(Final):
    """Complete package set with hello (29 more packages beyond final stdenv)."""

    @cached_property
    def _prev(self) -> Final:
        return Final()

    @cached_property
    def _own_packages(self) -> dict[str, Package]:
        chain = get_chain()
        return {dp: chain.packages[dp] for dp in chain.stages[7]}

    @cached_property
    def all_packages(self) -> dict[str, Package]:
        return {**self._prev.all_packages, **self._own_packages}

    @cached_property
    def hello(self) -> Package:
        return self.all_packages[HELLO_DRV]
