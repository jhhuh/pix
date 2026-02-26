"""Tests for decorator overlay pattern.

Same test scenarios as Experiments A, B, C for direct comparison.
"""

from experiments.d_decorator.bootstrap import Stage0, Stage1, Stage2


def test_stage0_self_consistent():
    s = Stage0()
    assert s.shell.name == "shell"
    assert s.tools.name == "tools"
    assert s.app.name == "app"
    assert s.shell.drv_path in s.app.drv.input_drvs
    assert s.tools.drv_path in s.app.drv.input_drvs


def test_stage1_overrides_tools():
    s = Stage1()
    assert s.shell.name == "shell"       # inherited
    assert s.tools.name == "tools-v1"    # overridden by decorator


def test_stage1_app_uses_new_tools():
    s0 = Stage0()
    s1 = Stage1()
    assert s1.tools.drv_path in s1.app.drv.input_drvs
    assert s1.app.out != s0.app.out


def test_stage1_shell_unchanged():
    s0 = Stage0()
    s1 = Stage1()
    assert s1.shell.out == s0.shell.out


def test_stage2_overrides_shell():
    s = Stage2()
    assert s.shell.name == "shell-v1"    # overridden by decorator
    assert s.tools.name == "tools-v1"    # inherited from Stage1


def test_stage2_app_uses_new_shell():
    s1 = Stage1()
    s2 = Stage2()
    assert s2.shell.drv_path in s2.app.drv.input_drvs
    assert s2.tools.drv_path in s2.app.drv.input_drvs
    assert s2.app.out != s1.app.out


def test_all_stages_different_app():
    s0, s1, s2 = Stage0(), Stage1(), Stage2()
    assert s0.app.out != s1.app.out
    assert s1.app.out != s2.app.out
    assert s0.app.out != s2.app.out


def test_stage2_tools_same_as_stage1():
    s1 = Stage1()
    s2 = Stage2()
    assert s2.tools.out == s1.tools.out


def test_caching():
    s = Stage2()
    first = s.app
    second = s.app
    assert first is second
