"""测试 _AsyncCompatibleLock 在同步上下文中的死循环风险修复 (Issue #1102)

Issue #1102: 当前的 __enter__ 实现创建了一个新的事件循环。
如果在现有异步循环的线程中调用此同步方法，会导致线程本地事件循环的冲突或死锁。

修复建议: 在 __enter__ 中，检测当前线程是否已有运行中的事件循环
(asyncio.get_running_loop)。如果有，抛出 RuntimeError 提示用户使用 async with。
"""

import asyncio
import pytest

from flywheel.storage import _AsyncCompatibleLock


class TestAsyncCompatibleLockDeadlockPrevention:
    """测试 _AsyncCompatibleLock 防止在同步上下文中出现死循环"""

    def test_sync_context_in_pure_sync_code(self):
        """测试在纯同步代码中使用同步接口应该正常工作"""
        lock = _AsyncCompatibleLock()

        # 在纯同步上下文中，应该能够正常使用
        with lock:
            # 锁应该被获取
            assert lock._sync_lock.locked()

        # 锁应该被释放
        assert not lock._sync_lock.locked()

    def test_sync_context_raises_error_in_async_context(self):
        """测试在异步上下文中使用同步接口应该抛出 RuntimeError

        这是 Issue #1102 的核心问题：在异步上下文中使用同步接口
        会导致死循环或事件循环冲突。修复后应该抛出清晰的错误。
        """
        lock = _AsyncCompatibleLock()

        async def attempt_sync_in_async():
            # 在异步上下文中使用同步接口应该抛出 RuntimeError
            with pytest.raises(RuntimeError) as exc_info:
                with lock:
                    pass

            # 验证错误消息提及了问题和解决方案
            error_msg = str(exc_info.value).lower()
            assert "async" in error_msg
            assert ("event loop" in error_msg or "running" in error_msg)

        # 运行测试
        asyncio.run(attempt_sync_in_async())

    def test_async_context_always_works(self):
        """测试异步接口在任何情况下都应该正常工作"""
        lock = _AsyncCompatibleLock()

        async def test_async_with():
            async with lock:
                # 锁应该被获取
                assert lock._async_lock.locked()

            # 锁应该被释放
            assert not lock._async_lock.locked()

        asyncio.run(test_async_with())

    def test_no_event_loop_created_in_sync_context(self):
        """测试在同步上下文中不会创建新的事件循环

        Issue #1102: 原始实现在 __enter__ 中创建新的事件循环，
        这会导致与现有异步上下文的冲突。
        """
        lock = _AsyncCompatibleLock()

        # 在没有事件循环的情况下使用锁
        with lock:
            # 验证锁已获取
            assert lock._sync_lock.locked()

        # 验证锁已释放
        assert not lock._sync_lock.locked()

        # 验证没有创建新的事件循环（通过检查没有残留的事件循环）
        try:
            # 如果有事件循环在运行，这个调用会成功
            loop = asyncio.get_running_loop()
            # 如果到了这里，说明有问题 - 不应该在同步上下文中留下运行的事件循环
            pytest.fail("Unexpected running event loop after sync context usage")
        except RuntimeError:
            # 预期行为：没有运行的事件循环
            pass

    def test_get_running_loop_detection(self):
        """测试使用 asyncio.get_running_loop() 检测运行中的事件循环

        这是 Issue #1102 的建议修复方案。
        """
        lock = _AsyncCompatibleLock()

        async def test_detection():
            # 在有运行事件循环的上下文中
            current_loop = asyncio.get_running_loop()
            assert current_loop is not None

            # 尝试使用同步接口应该失败
            with pytest.raises(RuntimeError) as exc_info:
                with lock:
                    pass

            # 验证错误消息提到了问题
            assert "async" in str(exc_info.value).lower()

        asyncio.run(test_detection())

    def test_error_message_suggests_async_with(self):
        """测试错误消息提示使用 async with

        Issue #1102 要求错误消息应该提示用户使用 async with。
        """
        lock = _AsyncCompatibleLock()

        async def check_error_message():
            with pytest.raises(RuntimeError) as exc_info:
                with lock:
                    pass

            error_message = str(exc_info.value)
            # 错误消息应该提到 "async with" 作为解决方案
            assert "async with" in error_message.lower() or "async with" in error_message

        asyncio.run(check_error_message())
