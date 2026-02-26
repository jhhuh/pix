"""Tests for class-inheritance overlay pattern.

Verifies that late binding (open recursion via `self`) correctly
propagates overrides through the bootstrap stage chain.
"""

from experiments.a_class_inherit.bootstrap import Stage0, Stage1, Stage2


def test_stage0_self_consistent():
    """Stage0 packages use stage0's own shell and tools."""
    s = Stage0()
    assert s.shell.name == "shell"
    assert s.tools.name == "tools"
    assert s.app.name == "app"
    # app depends on stage0's shell and tools
    assert s.shell.drv_path in s.app.drv.input_drvs
    assert s.tools.drv_path in s.app.drv.input_drvs


def test_stage1_overrides_tools():
    """Stage1 replaces tools but inherits shell."""
    s = Stage1()
    assert s.shell.name == "shell"       # inherited from Stage0
    assert s.tools.name == "tools-v1"    # overridden


def test_stage1_app_uses_new_tools():
    """Late binding: Stage1.app picks up the overridden tools."""
    s0 = Stage0()
    s1 = Stage1()
    # app is inherited from Stage0 but self.tools resolves to Stage1.tools
    assert s1.tools.drv_path in s1.app.drv.input_drvs
    # Different tools → different app
    assert s1.app.out != s0.app.out


def test_stage1_shell_unchanged():
    """Stage1 inherits Stage0's shell — same output path."""
    s0 = Stage0()
    s1 = Stage1()
    assert s1.shell.out == s0.shell.out


def test_stage2_overrides_shell():
    """Stage2 replaces shell, inherits stage1's tools."""
    s = Stage2()
    assert s.shell.name == "shell-v1"    # overridden
    assert s.tools.name == "tools-v1"    # inherited from Stage1


def test_stage2_app_uses_new_shell():
    """Late binding: Stage2.app picks up the overridden shell."""
    s1 = Stage1()
    s2 = Stage2()
    assert s2.shell.drv_path in s2.app.drv.input_drvs
    assert s2.tools.drv_path in s2.app.drv.input_drvs
    # Different shell → different app
    assert s2.app.out != s1.app.out


def test_all_stages_different_app():
    """Each stage produces a different app (different output paths)."""
    s0, s1, s2 = Stage0(), Stage1(), Stage2()
    assert s0.app.out != s1.app.out
    assert s1.app.out != s2.app.out
    assert s0.app.out != s2.app.out


def test_stage2_tools_same_as_stage1():
    """Stage2 doesn't rebuild tools — same as Stage1."""
    s1 = Stage1()
    s2 = Stage2()
    assert s2.tools.out == s1.tools.out


def test_cached_property_memoization():
    """Accessing a package twice returns the same object."""
    s = Stage2()
    first = s.app
    second = s.app
    assert first is second
