"""Tests for __getattr__ overlay chain pattern.

Same test scenarios as Experiment A to enable direct comparison.
"""

from experiments.b_getattr_chain.bootstrap import make_stage0, make_stage1, make_stage2


def test_stage0_self_consistent():
    s = make_stage0()
    assert s.shell.name == "shell"
    assert s.tools.name == "tools"
    assert s.app.name == "app"
    assert s.shell.drv_path in s.app.drv.input_drvs
    assert s.tools.drv_path in s.app.drv.input_drvs


def test_stage1_overrides_tools():
    s = make_stage1()
    assert s.shell.name == "shell"       # inherited from base
    assert s.tools.name == "tools-v1"    # overridden


def test_stage1_app_uses_new_tools():
    """Late binding: app's thunk sees final.tools = stage1's tools."""
    s0 = make_stage0()
    s1 = make_stage1()
    assert s1.tools.drv_path in s1.app.drv.input_drvs
    assert s1.app.out != s0.app.out


def test_stage1_shell_unchanged():
    s0 = make_stage0()
    s1 = make_stage1()
    assert s1.shell.out == s0.shell.out


def test_stage2_overrides_shell():
    s = make_stage2()
    assert s.shell.name == "shell-v1"    # overridden
    assert s.tools.name == "tools-v1"    # inherited from stage1


def test_stage2_app_uses_new_shell():
    """Late binding: app sees final.shell = stage2's shell."""
    s1 = make_stage1()
    s2 = make_stage2()
    assert s2.shell.drv_path in s2.app.drv.input_drvs
    assert s2.tools.drv_path in s2.app.drv.input_drvs
    assert s2.app.out != s1.app.out


def test_all_stages_different_app():
    s0, s1, s2 = make_stage0(), make_stage1(), make_stage2()
    assert s0.app.out != s1.app.out
    assert s1.app.out != s2.app.out
    assert s0.app.out != s2.app.out


def test_stage2_tools_same_as_stage1():
    """Stage2 doesn't override tools — same output path as stage1."""
    s1 = make_stage1()
    s2 = make_stage2()
    assert s2.tools.out == s1.tools.out


def test_caching():
    """Accessing a package twice returns the same object."""
    s = make_stage2()
    first = s.app
    second = s.app
    assert first is second
