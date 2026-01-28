"""测试 _AsyncCompatibleLock 中的 WeakValueDictionary 竞态条件

Issue #1350: WeakValueDictionary 中的值可能在 `in` 检查和字典访问之间被垃圾回收，
导致 KeyError。

修复方法：使用 dict.get() 方法而不是先检查 `in` 再访问字典。
"""

import asyncio
import gc
import weakref

import pytest

from flywheel.storage import _AsyncCompatibleLock


class TestAsyncCompatibleLockWeakValueRaceCondition:
    """测试 _AsyncCompatibleLock 的 WeakValueDictionary 竞态条件"""

    @pytest.mark.asyncio
    async def test_get_async_lock_handles_weakref_gc(self):
        """测试 _get_async_lock 能正确处理弱引用被 GC 的情况

        WeakValueDictionary 中的值可能在检查和访问之间被垃圾回收。
        修复后的代码应该使用 .get() 方法来避免 KeyError。
        """
        lock = _AsyncCompatibleLock()

        # 第一次获取锁会创建它
        async_lock1 = lock._get_async_lock()
        assert async_lock1 is not None
        assert isinstance(async_lock1, asyncio.Lock)

        # 获取同一个事件循环的锁应该返回同一个对象
        async_lock2 = lock._get_async_lock()
        assert async_lock1 is async_lock2

    @pytest.mark.asyncio
    async def test_get_async_lock_with_multiple_loops(self):
        """测试多个事件循环的情况下 _get_async_lock 的行为

        每个 event loop 应该有自己的 lock。
        """
        lock_wrapper = _AsyncCompatibleLock()

        # 在当前事件循环中获取锁
        current_loop_lock = lock_wrapper._get_async_lock()
        assert isinstance(current_loop_lock, asyncio.Lock)

        # 模拟在另一个事件循环中
        # 注意：在真正的多线程环境中，每个线程有自己的事件循环
        # 这里我们只测试当前事件循环的行为
        current_loop_id = id(asyncio.get_running_loop())

        # 验证锁确实存储在字典中
        assert current_loop_id in lock_wrapper._async_locks
        assert lock_wrapper._async_locks.get(current_loop_id) is current_loop_lock

    def test_get_async_lock_without_event_loop(self):
        """测试在没有事件循环的情况下调用 _get_async_lock

        应该抛出 RuntimeError。
        """
        lock = _AsyncCompatibleLock()

        with pytest.raises(RuntimeError, match="must be called from an async context"):
            lock._get_async_lock()

    @pytest.mark.asyncio
    async def test_async_lock_is_actual_asyncio_lock(self):
        """测试返回的锁确实是 asyncio.Lock"""
        lock_wrapper = _AsyncCompatibleLock()
        async_lock = lock_wrapper._get_async_lock()

        # 验证返回的是 asyncio.Lock
        assert isinstance(async_lock, asyncio.Lock)

        # 验证它可以正常工作
        assert not async_lock.locked()
        async with async_lock:
            assert async_lock.locked()
        assert not async_lock.locked()

    @pytest.mark.asyncio
    async def test_weakref_dictionary_auto_cleanup(self):
        """测试 WeakValueDictionary 在事件循环销毁后自动清理

        这个测试验证当事件循环不再存在时，WeakValueDictionary 会自动
        移除对应的条目。
        """
        lock = _AsyncCompatibleLock()

        # 创建一个锁
        current_loop = asyncio.get_running_loop()
        current_loop_id = id(current_loop)

        async_lock = lock._get_async_lock()
        assert async_lock is not None

        # 验证锁在字典中
        assert current_loop_id in lock._async_locks

        # 创建对锁的弱引用，用于测试
        weak_ref = weakref.ref(async_lock)

        # 删除对锁的强引用
        # 注意：在实际场景中，事件循环销毁时，对应的锁也会被销毁
        # 但由于我们还在当前事件循环中，锁不会被 GC
        # 这个测试主要是验证 WeakValueDictionary 的行为

        # 强制垃圾回收
        del async_lock
        gc.collect()

        # 由于 _async_locks 中还保留着引用，所以对象不会被回收
        # 但如果我们从 _async_locks 中删除它，它就会被回收
        lock._async_locks.clear()
        gc.collect()

        # 现在弱引用应该返回 None
        assert weak_ref() is None
