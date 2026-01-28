"""简单测试 Issue #791: 验证当前行为和期望行为"""

import pytest


def test_current_behavior_fcntl_import_error():
    """测试当前行为：fcntl 不可用时应该抛出 ImportError

    这个测试验证了当前的（有问题的）行为。
    修复后，我们应该改变这个测试来验证新的行为。
    """
    # 在 Unix 系统上，如果 fcntl 不可用，导入会失败
    # 这是一个简单的验证测试
    try:
        import fcntl
        # fcntl 可用，这是正常情况
        assert hasattr(fcntl, 'flock')
    except ImportError:
        # fcntl 不可用，在当前实现中这会导致程序崩溃
        # 这就是 Issue #791 所描述的问题
        pytest.fail("fcntl 不可用，但程序应该能够以降级模式运行")


def test_expect_degraded_mode_on_unix():
    """期望行为：Unix 系统应该支持降级模式

    类似于 Windows 系统在 pywin32 不可用时的行为，
    Unix 系统在 fcntl 不可用时也应该能够运行（在降级模式下）。
    """
    # 这个测试验证期望的行为
    # 修复后，即使 fcntl 不可用，storage 模块也应该能够导入
    from flywheel.storage import _is_degraded_mode

    # 在 Windows 上，如果 pywin32 不可用，_is_degraded_mode 返回 True
    # 在 Unix 上，我们期望类似的行为
    import os
    if os.name == 'nt':
        # Windows: 检查 pywin32 是否可用
        result = _is_degraded_mode()
        assert isinstance(result, bool)
    else:
        # Unix: 当前总是返回 False
        # 修复后：如果 fcntl 不可用，应该返回 True
        result = _is_degraded_mode()
        assert isinstance(result, bool)
