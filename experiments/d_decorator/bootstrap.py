"""Full 7-stage bootstrap using class decorators.

Each stage is a decorated class. The @stage_overlay decorator dynamically
adds the stage's packages as a merged all_packages dict. This combines
class inheritance's readability with dynamic overlay composition.

    class Stage0(PackageSet): ...
    @stage_overlay(1)
    class Stage1(Stage0): pass
    @stage_overlay(2)
    class StageXgcc(Stage1): pass
    ...

Individual packages are reconstructed from .drv files via make_package_from_drv().
"""

from functools import cached_property

from pixpkgs.drv import Package
from experiments.a_class_inherit.pkgset import PackageSet
from experiments.bootstrap_chain import get_chain, HELLO_DRV


def stage_overlay(stage_idx):
    """Class decorator that adds a bootstrap stage's packages.

    Creates a subclass with:
    - _own_packages: packages new in this stage (from chain data)
    - _prev: instance of the base class (previous stage)
    - all_packages: merged dict of prev + own packages
    """
    def decorator(cls):
        base = cls.__bases__[0] if cls.__bases__ else cls

        def _prev(self, _b=base):
            return _b()

        def _own_packages(self):
            chain = get_chain()
            return {dp: chain.packages[dp] for dp in chain.stages[stage_idx]}

        def _all_packages(self):
            return {**self._prev.all_packages, **self._own_packages}

        attrs = {
            '_prev': cached_property(_prev),
            '_own_packages': cached_property(_own_packages),
            'all_packages': cached_property(_all_packages),
        }
        return type(cls.__name__, (cls,), attrs)
    return decorator


class Stage0(PackageSet):
    """Bootstrap seed: 4 packages."""

    @cached_property
    def _own_packages(self) -> dict[str, Package]:
        chain = get_chain()
        return {dp: chain.packages[dp] for dp in chain.stages[0]}

    @cached_property
    def all_packages(self) -> dict[str, Package]:
        return dict(self._own_packages)


@stage_overlay(1)
class Stage1(Stage0):
    """Binutils wrapper, gcc wrapper, gnu-config (8 new → 12 total)."""
    pass


@stage_overlay(2)
class StageXgcc(Stage1):
    """First real GCC (xgcc), gmp, mpfr, isl (6 new → 18 total)."""
    pass


@stage_overlay(3)
class Stage2(StageXgcc):
    """Glibc transition (44 new → 62 total)."""
    pass


@stage_overlay(4)
class Stage3(Stage2):
    """Compiler transition: final gcc (23 new → 85 total)."""
    pass


@stage_overlay(5)
class Stage4(Stage3):
    """Tools transition: coreutils, bash, etc. (19 new → 104 total)."""
    pass


@stage_overlay(6)
class Final(Stage4):
    """Production stdenv (63 new → 167 total)."""
    pass


@stage_overlay(7)
class Pkgs(Final):
    """Complete set with hello (29 new → 196 total)."""
    pass


# Add hello convenience accessor after decoration
_original_pkgs = Pkgs


def _make_pkgs_with_hello():
    """Create Pkgs instance with hello property."""
    p = _original_pkgs()
    return p


class PkgsWithHello(_original_pkgs):
    @cached_property
    def hello(self) -> Package:
        return self.all_packages[HELLO_DRV]


# Re-export
Pkgs = PkgsWithHello
