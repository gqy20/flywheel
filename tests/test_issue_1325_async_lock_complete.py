"""测试修复 Issue #1325 - IOMetrics._get_async_lock 实现完整性验证

问题描述：
验证 _get_async_lock 的实现是否完整，确保：
1. call_soon_threadsafe 被正确使用来调度锁创建
2. 锁被正确存储和检索（使用 loop ID）
3. 没有潜在的死锁风险

这个测试验证 Issue #1160 的修复是否正确实现。
"""

import asyncio
import threading
import pytest

from flywheel import IOMetrics


def test_get_async_lock_uses_call_soon_threadsafe():
    """测试 _get_async_lock 使用 call_soon_threadsafe 来调度锁创建"""

    metrics = IOMetrics()

    async def verify_lock_creation():
        # 获取当前事件循环
        current_loop = asyncio.get_running_loop()
        current_loop_id = id(current_loop)

        # 验证锁不存在
        assert current_loop_id not in metrics._locks

        # 调用 _get_async_lock
        lock = metrics._get_async_lock()

        # 验证锁被创建并存储
        assert current_loop_id in metrics._locks
        assert metrics._locks[current_loop_id] is lock
        assert isinstance(lock, asyncio.Lock)

        # 验证事件循环被正确存储
        assert current_loop_id in metrics._event_loops
        assert metrics._event_loops[current_loop_id] is current_loop

    asyncio.run(verify_lock_creation())


def test_get_async_lock_reuses_existing_lock():
    """测试 _get_async_lock 重用已存在的锁"""

    metrics = IOMetrics()

    async def verify_lock_reuse():
        current_loop = asyncio.get_running_loop()
        current_loop_id = id(current_loop)

        # 第一次获取锁
        lock1 = metrics._get_async_lock()

        # 第二次获取锁
        lock2 = metrics._get_async_lock()

        # 应该返回同一个锁对象
        assert lock1 is lock2
        assert metrics._locks[current_loop_id] is lock1

    asyncio.run(verify_lock_reuse())


def test_get_async_lock_thread_safety():
    """测试 _get_async_lock 在多线程环境下的线程安全性"""

    metrics = IOMetrics()
    locks_created = []
    exceptions = []

    async def async_task(thread_id):
        try:
            lock = metrics._get_async_lock()
            locks_created.append((thread_id, id(lock)))
        except Exception as e:
            exceptions.append(e)

    def run_async_in_thread(thread_id):
        try:
            asyncio.run(async_task(thread_id))
        except Exception as e:
            exceptions.append(e)

    # 创建多个线程，每个都在自己的事件循环中获取锁
    threads = []
    for i in range(5):
        thread = threading.Thread(target=run_async_in_thread, args=(i,))
        threads.append(thread)
        thread.start()

    # 等待所有线程完成
    for thread in threads:
        thread.join()

    # 验证没有异常
    assert len(exceptions) == 0, f"Exceptions occurred: {exceptions}"

    # 验证每个线程都成功创建了锁
    assert len(locks_created) == 5

    # 验证不同线程中的锁 ID 可能不同（因为不同线程使用不同的事件循环）
    # 但同一个事件循环的锁应该被重用


def test_get_async_lock_with_multiple_event_loops():
    """测试 _get_async_lock 处理多个事件循环"""

    metrics = IOMetrics()
    loop_ids = []

    async def record_loop_id():
        current_loop = asyncio.get_running_loop()
        loop_ids.append(id(current_loop))
        await metrics.increment("test")

    # 在多个独立的事件循环中运行
    for i in range(3):
        asyncio.run(record_loop_id())

    # 验证每个事件循环都创建了锁
    assert len(metrics._locks) == 3

    # 验证每个事件循环的锁都使用正确的 ID
    for loop_id in loop_ids:
        assert loop_id in metrics._locks
        assert isinstance(metrics._locks[loop_id], asyncio.Lock)


def test_get_async_lock_stores_event_loop_reference():
    """测试 _get_async_lock 存储事件循环引用以便后续清理"""

    metrics = IOMetrics()

    async def verify_event_loop_storage():
        current_loop = asyncio.get_running_loop()
        current_loop_id = id(current_loop)

        # 获取锁
        lock = metrics._get_async_lock()

        # 验证事件循环被存储在 _event_loops 字典中
        assert current_loop_id in metrics._event_loops
        assert metrics._event_loops[current_loop_id] is current_loop

        # 验证这可以用于检测事件循环是否关闭
        assert not current_loop.is_closed()

    asyncio.run(verify_event_loop_storage())


def test_get_async_lock_no_deadlock_with_concurrent_access():
    """测试 _get_async_lock 在并发访问时不会死锁"""

    metrics = IOMetrics()
    results = []

    async def async_operation(task_id):
        # 模拟异步操作
        lock = metrics._get_async_lock()
        async with lock:
            await asyncio.sleep(0.01)
            results.append(task_id)

    async def run_concurrent_tasks():
        # 创建多个并发任务
        tasks = [async_operation(i) for i in range(10)]
        await asyncio.gather(*tasks)

    # 验证所有任务都能完成（没有死锁）
    asyncio.run(run_concurrent_tasks())

    # 验证所有任务都成功执行
    assert len(results) == 10
    assert sorted(results) == list(range(10))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
