"""测试 Issue #559: Windows 降级模式的安全风险

问题描述：
在 Windows 上，如果 pywin32 缺失，程序会回退到"降级模式"运行，
该模式没有文件锁定功能。在多用户系统（如 Windows Terminal Server
或持久化 CI worker）上，这可能导致并发实例运行时数据损坏。

修复建议：
在 Windows 上应该强制要求 pywin32，而不是静默回退到降级模式，
因为降级模式在并发情况下会保证数据损坏。

更安全的做法是：Windows 上如果 pywin32 缺失，应该抛出错误，
而不是允许在不安全的状态下运行。
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
import pytest


def test_windows_requires_pywin32_no_degraded_mode():
    """
    测试 Windows 在 pywin32 缺失时应该抛出错误，而不是进入降级模式。

    安全性原则：
    - 降级模式缺少文件锁定，在多实例并发时会导致数据损坏
    - 在多用户系统（Windows Terminal Server、CI worker）上风险更高
    - 宁可拒绝启动，也不能在不安全的状态下运行

    预期行为：
    - Windows + pywin32 缺失 → 抛出 ImportError
    - Windows + pywin32 存在 → 正常运行
    - 非 Windows → 不需要 pywin32
    """
    # 只在 Windows 上测试
    if os.name != 'nt':
        pytest.skip("此测试仅在 Windows 上运行")

    # 模拟 pywin32 不可用
    with patch.dict(sys.modules, {
        'win32security': None,
        'win32con': None,
        'win32api': None,
        'win32file': None,
        'pywintypes': None
    }):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            # 导入 storage 模块（此时会触发 Windows 导入检查）
            # 由于我们 mock 了 sys.modules，import 会失败
            # 修复后：应该抛出 ImportError，而不是允许降级模式
            with pytest.raises(ImportError) as exc_info:
                # 重新导入模块以触发导入检查
                import importlib
                from flywheel import storage
                importlib.reload(storage)
                from flywheel.storage import Storage

                # 尝试创建 Storage 实例
                Storage(str(storage_path))

            # 验证错误消息清晰说明了 pywin32 的必要性
            error_msg = str(exc_info.value).lower()
            assert "pywin32" in error_msg, (
                f"错误消息应该提到 pywin32，实际得到: {exc_info.value}"
            )
            assert "windows" in error_msg or "required" in error_msg, (
                f"错误消息应该说明这是 Windows 系统的必要依赖"
            )


def test_windows_with_pywin32_works_fine():
    """
    测试 Windows 在 pywin32 可用时正常工作。

    这确保修复不会破坏正常情况下的功能。
    """
    # 只在 Windows 上测试
    if os.name != 'nt':
        pytest.skip("此测试仅在 Windows 上运行")

    # 尝试导入 pywin32
    try:
        import win32security  # noqa: F401
        import win32file  # noqa: F401
    except ImportError:
        pytest.skip("pywin32 未安装，跳过测试")

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        from flywheel.storage import Storage

        # 应该正常工作
        storage = Storage(str(storage_path))
        assert storage is not None
        storage.close()


def test_non_windows_no_pywin32_required():
    """
    测试非 Windows 系统不需要 pywin32。

    确保修复不会影响非 Windows 系统的正常运行。
    """
    # 只在非 Windows 系统上测试
    if os.name == 'nt':
        pytest.skip("此测试仅在非 Windows 系统上运行")

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        from flywheel.storage import Storage

        # 应该在没有 pywin32 的情况下正常工作
        storage = Storage(str(storage_path))
        assert storage is not None
        storage.close()


def test_degraded_mode_should_not_exist_on_windows():
    """
    测试 Windows 上不应该存在降级模式。

    这是安全性验证：降级模式在 Windows 上是危险的，
    因为它会静默地移除文件锁定保护，导致数据损坏风险。
    """
    # 只在 Windows 上测试
    if os.name != 'nt':
        pytest.skip("此测试仅在 Windows 上运行")

    from flywheel.storage import _is_degraded_mode

    # 在 Windows 上，如果程序能运行到这里，说明要么：
    # 1. pywin32 已安装（正常）
    # 2. 存在降级模式（不安全，应该被移除）

    # 如果 pywin32 已安装，_is_degraded_mode 应该返回 False
    try:
        import win32file  # noqa: F401
        # pywin32 存在，应该不是降级模式
        assert _is_degraded_mode() is False, (
            "Windows 上安装了 pywin32 时，不应该是降级模式"
        )
    except ImportError:
        # pywin32 不存在，但这不应该发生
        # 因为修复后导入时就应该抛出错误了
        # 如果能运行到这里，说明降级模式仍然存在（不安全）
        assert False, (
            "Issue #559: Windows 上 pywin32 缺失时应该抛出 ImportError，"
            "而不是允许进入降级模式运行。降级模式缺少文件锁定，"
            "在多实例并发时会导致数据损坏。"
        )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
