"""测试 Issue #1255 - 验证代码完整性

Issue #1255 声称代码在第 236 行截断，声称 `except RuntimeError as e:` 后面缺少代码。
经过详细检查，该 issue 是一个误报。

实际验证结果：
- 第 232-239 行的 except 块是完整的，包含了正确的错误处理逻辑
- __enter__ 方法（第 198-316 行）完整实现
- __exit__ 方法（第 318-369 行）完整实现
- __aenter__ 方法（第 371-388 行）完整实现
- __aexit__ 方法（第 390+ 行）完整实现

此测试验证所有上下文管理器方法都已正确实现且功能正常。
"""

import pytest
import asyncio
from flywheel.storage import _AsyncCompatibleLock


def test_async_compatible_lock_has_context_managers():
    """验证 _AsyncCompatibleLock 实现了所有必需的上下文管理器方法"""
    lock = _AsyncCompatibleLock()

    # 验证所有必需的方法都存在
    assert hasattr(lock, '__enter__'), "缺少 __enter__ 方法"
    assert hasattr(lock, '__exit__'), "缺少 __exit__ 方法"
    assert hasattr(lock, '__aenter__'), "缺少 __aenter__ 方法"
    assert hasattr(lock, '__aexit__'), "缺少 __aexit__ 方法"

    # 验证方法是可调用的
    assert callable(lock.__enter__), "__enter__ 不是可调用的"
    assert callable(lock.__exit__), "__exit__ 不是可调用的"
    assert callable(lock.__aenter__), "__aenter__ 不是可调用的"
    assert callable(lock.__aexit__), "__aexit__ 不是可调用的"


def test_async_compatible_lock_sync_context_manager():
    """测试同步上下文管理器功能"""
    lock = _AsyncCompatibleLock()

    # 测试 with 语句可以正常工作
    with lock:
        # 锁已获取
        assert lock._locked is True

    # 锁已释放
    assert lock._locked is False


def test_async_compatible_lock_async_context_manager():
    """测试异步上下文管理器功能"""
    lock = _AsyncCompatibleLock()

    async def acquire_and_release():
        async with lock:
            # 锁已获取
            assert lock._locked is True
        # 锁已释放
        assert lock._locked is False

    # 运行异步测试
    asyncio.run(acquire_and_release())


def test_code_syntax_is_valid():
    """验证 storage.py 文件的语法是正确的"""
    import ast
    import os

    storage_path = os.path.join(
        os.path.dirname(__file__),
        '..',
        'src',
        'flywheel',
        'storage.py'
    )

    with open(storage_path, 'r') as f:
        source = f.read()

    # 尝试解析文件 - 如果语法错误会抛出 SyntaxError
    try:
        ast.parse(source)
    except SyntaxError as e:
        pytest.fail(f"storage.py 存在语法错误: {e}")


def test_line_236_code_is_complete():
    """验证第 236 行周围的代码逻辑是完整的

    Issue #1255 声称第 236 行 `except RuntimeError as e:` 后面代码截断。
    此测试验证 except 块的错误处理逻辑是正确的：
    1. 如果错误包含 "async"，说明是我们主动抛出的错误，需要重新抛出
    2. 否则，说明是 "no running event loop" 错误，可以继续执行
    """
    lock = _AsyncCompatibleLock()

    # 测试场景 1: 在没有事件循环的线程中使用 with 语句
    # 应该正常工作，因为没有运行的事件循环
    with lock:
        assert lock._locked is True

    assert lock._locked is False


def test_enter_async_error_detection():
    """测试 __enter__ 方法正确检测异步上下文错误

    验证第 226-237 行的错误检测和重抛逻辑：
    - 当在异步上下文中使用同步 with 语句时，应该抛出 RuntimeError
    - 错误消息包含 "async"，会被 except 块捕获并重新抛出
    """
    import asyncio

    lock = _AsyncCompatibleLock()

    async def try_sync_with_in_async_context():
        # 在异步上下文中尝试使用同步 with 语句
        # 应该抛出 RuntimeError 并包含 "async" 关键字
        with pytest.raises(RuntimeError) as exc_info:
            with lock:
                pass

        # 验证错误消息包含预期的内容
        assert "async" in str(exc_info.value).lower()
        assert "Cannot use synchronous context manager" in str(exc_info.value)

    # 运行异步测试
    asyncio.run(try_sync_with_in_async_context())


def test_enter_method_completes():
    """验证 __enter__ 方法可以正常完成执行"""
    lock = _AsyncCompatibleLock()

    # 调用 __enter__ 应该返回 self
    result = lock.__enter__()
    assert result is lock
    assert lock._locked is True

    # 清理
    lock.__exit__(None, None, None)
    assert lock._locked is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
