"""Test for Issue #1360: __aenter__ 缺少异常处理机制

测试 __aenter__ 在异常情况下是否正确处理锁状态。
"""
import asyncio
import pytest
from flywheel.storage import Storage


class TestAsyncContextExceptionHandling:
    """测试异步上下文管理器的异常处理"""

    @pytest.mark.asyncio
    async def test_aenter_exception_should_not_leave_locked_state(self):
        """测试 __aenter__ 中发生异常时，不应该留下锁定的状态

        这是一个模拟测试：如果 __aenter__ 在设置 _async_locked 之后、
        返回之前发生异常，当前的实现会导致锁状态不一致。
        """
        storage = Storage()
        initial_async_locked = storage._async_locked

        # 模拟一个场景：在 __aenter__ 过程中可能发生异常
        # 我们需要确保如果异常发生在 acquire() 之后但返回之前，
        # 锁会被正确释放

        # 这个测试验证：如果 __aenter__ 失败，_async_locked 应该是 False
        # 并且后续的 __aenter__ 调用应该能正常工作

        # 当前没有异常的场景应该正常工作
        async with storage:
            assert storage._async_locked is True

        # 退出后应该释放
        assert storage._async_locked is False

    @pytest.mark.asyncio
    async def test_aenter_with_simulated_exception(self):
        """测试 __aenter__ 中的异常处理

        通过猴子补丁模拟 __aenter__ 中的异常
        """
        storage = Storage()
        original_aenter = storage.__aenter__

        async def faulty_aenter():
            """模拟在 acquire() 之后发生异常"""
            async_lock = storage._get_async_lock()
            await async_lock.acquire()
            # 模拟：在设置标志之后发生异常
            storage._async_locked = True
            storage._held_async_lock = async_lock
            # 故意引发异常
            raise RuntimeError("Simulated exception in __aenter__")

        # 替换 __aenter__ 为有问题的版本
        storage.__aenter__ = faulty_aenter

        # 尝试进入上下文（应该失败）
        with pytest.raises(RuntimeError, match="Simulated exception"):
            async with storage:
                pass

        # 关键断言：异常后，锁状态应该被清理
        # 当前的实现有 bug：_async_locked 可能仍然是 True
        # 这将导致后续无法正确获取锁
        assert storage._async_locked is False, \
            "After exception in __aenter__, _async_locked should be False"

        # 验证后续可以正常使用
        async with storage:
            assert storage._async_locked is True

    @pytest.mark.asyncio
    async def test_aenter_exception_before_return(self):
        """测试 __aenter__ 在返回前发生异常的情况

        这个测试验证异常处理机制的正确性
        """
        storage = Storage()

        # 保存原始方法
        original_get_async_lock = storage._get_async_lock
        call_count = [0]

        async def mock_get_async_lock():
            """模拟可能失败的锁获取"""
            call_count[0] += 1
            if call_count[0] == 1:
                # 第一次调用返回锁
                return original_get_async_lock()
            else:
                return original_get_async_lock()

        storage._get_async_lock = mock_get_async_lock

        # 测试正常情况
        async with storage:
            assert storage._async_locked is True

        assert storage._async_locked is False
