"""Top-level package set: application packages built with the final stdenv.

Like nixpkgs/pkgs/top-level/all-packages.nix — the end of the bootstrap
chain where user-facing packages are defined.

    Stage0 → Stage1 → StageXgcc → ... → Final → Pkgs

Pkgs will inherit from Final once Stage2-4 are implemented. Each package
is a @cached_property that resolves deps through the inheritance chain
(self.bash, self.stdenv, etc. come from the parent class).
"""

from functools import cached_property

from pixpkgs.drv import Package
from pixpkgs.package_set import PackageSet
from pixpkgs.pkgs.hello import make_hello


class Pkgs(PackageSet):
    """Top-level package set.

    Each @cached_property is a package. Dependencies (bash, stdenv, etc.)
    resolve via class inheritance from the previous stage.
    """

    @cached_property
    def hello(self) -> Package:
        return make_hello(
            bash=self.bash,
            stdenv=self.stdenv,
            src=self.hello_src,
            version_check_hook=self.version_check_hook,
        )
