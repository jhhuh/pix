"""Write .drv to the Nix store and build it.

This is the Python equivalent of nix-instantiate + nix-store --realize:
it registers the derivation file in the store, then asks the daemon
to build it.
"""

from pix.daemon import DaemonConnection
from pix.derivation import serialize
from pixpkgs.drv import Package


def _register_drv(pkg: Package, conn: DaemonConnection, seen: set[str]) -> None:
    """Recursively register pkg and all its dependency .drv files in the store."""
    if pkg.drv_path in seen:
        return
    seen.add(pkg.drv_path)

    # Register dependencies first
    for dep in (pkg._args.get("deps") or []):
        _register_drv(dep, conn, seen)

    drv_content = serialize(pkg.drv)
    refs = sorted(pkg.drv.input_drvs.keys()) + sorted(pkg.drv.input_srcs)
    conn.add_text_to_store(pkg.name + ".drv", drv_content, refs)


def realize(pkg: Package, conn: DaemonConnection | None = None) -> str:
    """Register pkg's .drv in the store and build it. Returns output path.

    If conn is provided, uses that connection. Otherwise opens a new one.
    """
    def _do(c: DaemonConnection) -> str:
        _register_drv(pkg, c, set())
        # Wire protocol uses "!" separator (legacy DerivedPath format),
        # not "^" which is the CLI format.
        c.build_paths([f"{pkg.drv_path}!out"])
        return pkg.out

    if conn is not None:
        return _do(conn)

    with DaemonConnection() as c:
        return _do(c)
