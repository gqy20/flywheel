"""测试 _AsyncCompatibleLock 在同步上下文中的死锁风险修复 (Issue #1107)"""

import asyncio
import pytest

from flywheel.storage import _AsyncCompatibleLock


class TestAsyncCompatibleLockSyncContext:
    """测试 _AsyncCompatibleLock 在同步上下文中的行为"""

    def test_sync_context_in_non_async_context(self):
        """测试在非异步上下文中使用同步接口应该正常工作"""
        lock = _AsyncCompatibleLock()

        # 这应该正常工作
        with lock:
            # 锁应该被获取
            assert lock._lock.locked()

        # 锁应该被释放
        assert not lock._lock.locked()

    def test_sync_context_in_running_event_loop(self):
        """测试在已有运行事件循环的上下文中使用同步接口

        这是 Issue #1107 的核心问题：当在一个已经有运行事件循环的
        上下文中（如 Jupyter Notebook 或异步 Web 框架）使用同步接口
        时，会创建新的事件循环导致错误或死锁。
        """
        lock = _AsyncCompatibleLock()

        # 模拟在已有运行事件循环的上下文中
        async def test_in_async_context():
            # 在异步上下文中，我们不应该使用同步接口
            # 但如果误用，应该抛出清晰的错误而不是死锁
            with pytest.raises(RuntimeError) as exc_info:
                with lock:
                    pass

            # 验证错误消息是友好的
            assert "async" in str(exc_info.value).lower() or "event loop" in str(exc_info.value).lower()

        # 运行测试
        asyncio.run(test_in_async_context())

    def test_async_context_always_works(self):
        """测试异步接口在任何情况下都应该正常工作"""
        lock = _AsyncCompatibleLock()

        async def test_async_with():
            async with lock:
                assert lock._lock.locked()

            assert not lock._lock.locked()

        asyncio.run(test_async_with())

    def test_nested_sync_context_in_async(self):
        """测试在异步上下文中嵌套使用同步接口的错误处理"""
        lock = _AsyncCompatibleLock()

        async def run_sync_in_async():
            # 尝试在异步上下文中使用同步接口
            try:
                with lock:
                    # 如果我们到了这里，说明有问题
                    assert False, "应该在进入时就抛出异常"
            except RuntimeError as e:
                # 预期会抛出 RuntimeError
                assert "async" in str(e).lower() or "event loop" in str(e).lower()

        asyncio.run(run_sync_in_async())
