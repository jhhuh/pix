"""End-to-end tests: build packages via the Nix daemon."""

import os
import pytest

from pixpkgs import drv, realize, PackageSet
from pix.daemon import DaemonConnection
from functools import cached_property

needs_daemon = pytest.mark.skipif(
    not os.path.exists("/nix/var/nix/daemon-socket/socket"),
    reason="nix daemon not available",
)


@needs_daemon
def test_realize_trivial():
    """Build a trivial package that writes to $out."""
    pkg = drv(
        name="pixpkgs-test",
        builder="/bin/sh",
        args=["-c", "echo pixpkgs-works > $out"],
    )
    out = realize(pkg)
    assert out == pkg.out
    assert os.path.exists(out)
    assert open(out).read().strip() == "pixpkgs-works"


@needs_daemon
def test_realize_with_dep():
    """Build a package that depends on another."""
    dep = drv(
        name="pixpkgs-dep",
        builder="/bin/sh",
        args=["-c", "echo dependency > $out"],
    )
    realize(dep)

    pkg = drv(
        name="pixpkgs-consumer",
        builder="/bin/sh",
        # Use shell builtin: 'read' + 'echo' instead of 'cat' (not in sandbox)
        args=["-c", f"read line < {dep.out}; echo $line > $out"],
        deps=[dep],
    )
    out = realize(pkg)
    assert open(out).read().strip() == "dependency"


@needs_daemon
def test_package_set():
    """PackageSet with auto-injection should build correctly."""

    class TestPkgs(PackageSet):
        @cached_property
        def greeting(self):
            return drv(
                name="pixpkgs-greeting",
                builder="/bin/sh",
                args=["-c", "echo hello-from-package-set > $out"],
            )

        @cached_property
        def shouter(self):
            return self.call(lambda greeting: drv(
                name="pixpkgs-shouter",
                builder="/bin/sh",
                # Use shell builtin instead of 'tr' (not in sandbox)
                args=["-c", f"read line < {greeting}; echo shouted-$line > $out"],
                deps=[greeting],
            ))

    pkgs = TestPkgs()
    out = realize(pkgs.shouter)
    assert open(out).read().strip() == "shouted-hello-from-package-set"
