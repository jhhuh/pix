"""Tests for pixpkgs.drv — derivation construction and output path computation."""

from pixpkgs.drv import drv


def test_drv_produces_store_path():
    """drv() should produce a valid /nix/store path."""
    pkg = drv(name="test", builder="/bin/sh", args=["-c", "echo > $out"])
    assert pkg.out.startswith("/nix/store/")
    assert pkg.out.endswith("-test")


def test_drv_path_is_store_path():
    """.drv_path should be a .drv file in /nix/store."""
    pkg = drv(name="test", builder="/bin/sh", args=["-c", "echo > $out"])
    assert pkg.drv_path.startswith("/nix/store/")
    assert pkg.drv_path.endswith("-test.drv")


def test_drv_deterministic():
    """Same inputs should produce the same output path."""
    a = drv(name="det", builder="/bin/sh", args=["-c", "echo > $out"])
    b = drv(name="det", builder="/bin/sh", args=["-c", "echo > $out"])
    assert a.out == b.out
    assert a.drv_path == b.drv_path


def test_drv_name_changes_path():
    """Different names should produce different output paths."""
    a = drv(name="alpha", builder="/bin/sh", args=["-c", "echo > $out"])
    b = drv(name="beta", builder="/bin/sh", args=["-c", "echo > $out"])
    assert a.out != b.out


def test_drv_content_changes_path():
    """Different build commands should produce different output paths."""
    a = drv(name="pkg", builder="/bin/sh", args=["-c", "echo a > $out"])
    b = drv(name="pkg", builder="/bin/sh", args=["-c", "echo b > $out"])
    assert a.out != b.out


def test_drv_str_is_out():
    """str(pkg) should return the default output path."""
    pkg = drv(name="test", builder="/bin/sh", args=["-c", "echo > $out"])
    assert str(pkg) == pkg.out


def test_drv_env_has_standard_vars():
    """The derivation env should include name, builder, system, out."""
    pkg = drv(name="test", builder="/bin/sh", args=["-c", "echo > $out"])
    assert pkg.drv.env["name"] == "test"
    assert pkg.drv.env["builder"] == "/bin/sh"
    assert pkg.drv.env["system"] == "x86_64-linux"
    assert pkg.drv.env["out"] == pkg.out


def test_drv_with_dep():
    """A package with a dependency should include it as inputDrv."""
    dep = drv(name="dep", builder="/bin/sh", args=["-c", "echo > $out"])
    pkg = drv(name="pkg", builder="/bin/sh", args=["-c", "cat $dep/file > $out"], deps=[dep])
    assert dep.drv_path in pkg.drv.input_drvs


def test_drv_dep_changes_path():
    """Changing a dependency should change the output path."""
    dep_a = drv(name="dep", builder="/bin/sh", args=["-c", "echo a > $out"])
    dep_b = drv(name="dep", builder="/bin/sh", args=["-c", "echo b > $out"])
    pkg_a = drv(name="pkg", builder="/bin/sh", args=["-c", "cat > $out"], deps=[dep_a])
    pkg_b = drv(name="pkg", builder="/bin/sh", args=["-c", "cat > $out"], deps=[dep_b])
    assert pkg_a.out != pkg_b.out


def test_override():
    """override() should re-derive with changed args."""
    pkg = drv(name="hello", builder="/bin/sh", args=["-c", "echo hi > $out"])
    pkg2 = pkg.override(name="world")
    assert pkg2.name == "world"
    assert pkg2.out != pkg.out
    assert pkg2.out.endswith("-world")
