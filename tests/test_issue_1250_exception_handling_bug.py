"""测试 Issue #1250 - __enter__ 方法中的异常处理bug

当前代码在 __enter__ 方法中有严重的异常处理bug：
- 第 222 行调用 asyncio.get_running_loop() 可能抛出 RuntimeError（正常情况：没有运行中的循环）
- 第 226 行也会抛出 RuntimeError（错误情况：在异步上下文中误用同步接口）
- 第 232 行的 except 块捕获了这两种 RuntimeError，导致应该抛出的错误被静默吞掉

修复方法：只捕获来自 asyncio.get_running_loop() 的 RuntimeError，
而不是我们主动抛出的 RuntimeError。
"""

import asyncio
import pytest

from flywheel.storage import _AsyncCompatibleLock


class TestIssue1250ExceptionHandlingBug:
    """测试 Issue #1250 - 异常处理bug"""

    def test_sync_context_should_raise_error_in_async_context(self):
        """测试在异步上下文中使用同步接口应该抛出 RuntimeError

        这是 Issue #1250 的核心问题：当前代码的第 232 行 except 块
        会捕获第 226 行主动抛出的 RuntimeError，导致错误被静默吞掉。

        修复后，这个测试应该通过（抛出预期的错误）。
        """
        lock = _AsyncCompatibleLock()

        async def test_in_async_context():
            # 在异步上下文中使用同步接口应该抛出 RuntimeError
            with pytest.raises(RuntimeError) as exc_info:
                with lock:
                    pass  # 不应该执行到这里

            # 验证错误消息包含 "async" 或 "event loop"
            error_msg = str(exc_info.value).lower()
            assert "async" in error_msg or "event loop" in error_msg

        # 运行测试
        asyncio.run(test_in_async_context())

    def test_sync_context_should_work_in_non_async_context(self):
        """测试在非异步上下文中使用同步接口应该正常工作"""
        lock = _AsyncCompatibleLock()

        # 这应该正常工作，没有运行的事件循环
        with lock:
            # 锁应该被获取
            assert lock._lock.locked()

        # 锁应该被释放
        assert not lock._lock.locked()

    def test_async_context_always_works(self):
        """测试异步接口在任何情况下都应该正常工作"""
        lock = _AsyncCompatibleLock()

        async def test_async_with():
            async with lock:
                assert lock._lock.locked()

            assert not lock._lock.locked()

        asyncio.run(test_async_with())
