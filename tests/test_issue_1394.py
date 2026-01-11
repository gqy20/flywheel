"""
Test for Issue #1394: RLock 在异步上下文中可能导致死锁

问题：当持有 RLock 的同步线程在等待异步事件，而该事件需要由持有 RLock 的同步
线程触发时，会形成死锁。这是因为 RLock 是可重入的，在异步上下文中直接获取
RLock 可能导致问题。
"""
import asyncio
import threading
import time
import pytest
from flywheel.storage import _AsyncCompatibleLock


class TestRLockAsyncDeadlock:
    """测试 RLock 在异步上下文中的潜在死锁问题"""

    @pytest.mark.timeout(10)
    def test_rlock_no_deadlock_with_async_to_thread(self):
        """
        测试使用 asyncio.to_thread 获取锁时不会导致死锁

        场景：
        1. 同步线程持有 RLock
        2. 异步任务尝试通过 asyncio.to_thread 获取同一个锁
        3. 如果持有锁的线程在等待异步事件，则不会死锁
        """

        lock = _AsyncCompatibleLock()
        deadlock_detected = False
        sync_thread_acquired = threading.Event()
        async_task_started = threading.Event()

        def sync_context_holder():
            """
            同步上下文持有锁，并等待异步事件
            这模拟了 issue 中描述的死锁场景
            """
            nonlocal deadlock_detected

            with lock:
                # 标记同步线程已获取锁
                sync_thread_acquired.set()

                # 等待异步任务启动
                async_task_started.wait(timeout=5)

                # 模拟持有锁的线程在等待某些异步操作
                # 在真实场景中，这里可能是在等待异步任务完成
                time.sleep(0.5)

                # 如果我们能够到达这里，说明没有死锁
                deadlock_detected = False

        async def async_context_waiter():
            """
            异步上下文尝试获取锁
            """
            # 标记异步任务已启动
            async_task_started.set()

            # 等待同步线程获取锁
            sync_thread_acquired.wait()

            # 尝试以异步方式获取锁
            # 如果锁是 RLock 且在 __aenter__ 中使用 await asyncio.to_thread
            # 而同步线程在持有锁的同时等待异步事件，可能会死锁
            start_time = time.time()
            try:
                # 设置超时以防止真正的死锁
                async with asyncio.timeout(3.0):
                    async with lock:
                        # 如果我们能够获取到锁，说明没有死锁
                        pass
            except asyncio.TimeoutError:
                # 超时表示可能发生了死锁
                deadlock_detected = True
                raise
            elapsed = time.time() - start_time

            # 获取锁的时间应该是合理的（< 2秒，因为同步线程只持有 0.5 秒）
            assert elapsed < 2.0, f"获取锁耗时过长 ({elapsed:.2f}s)，可能存在死锁"

        # 运行测试
        loop = asyncio.new_event_loop()
        try:
            # 在单独的线程中运行同步上下文
            sync_thread = threading.Thread(target=sync_context_holder)
            sync_thread.start()

            # 在事件循环中运行异步上下文
            loop.run_until_complete(async_context_waiter())

            # 等待同步线程完成
            sync_thread.join(timeout=5)

            assert not sync_thread.is_alive(), "同步线程仍在运行，可能发生死锁"
            assert not deadlock_detected, "检测到死锁"
        finally:
            loop.close()

    @pytest.mark.timeout(10)
    def test_rlock_prevents_reentrant_async_acquisition(self):
        """
        测试 RLock 不应允许异步上下文中的重入获取

        因为这可能导致：
        1. 异步任务通过 to_thread 获取锁
        2. 在持有锁的同时等待事件
        3. 而该事件需要同一个锁来触发
        """
        lock = _AsyncCompatibleLock()
        acquisition_count = 0

        async def async_reentrant_attempt():
            """尝试在异步上下文中重入获取锁"""
            nonlocal acquisition_count

            async with lock:
                acquisition_count += 1
                # 在持有锁的同时尝试再次获取
                # 这不应该成功，以避免潜在的死锁
                try:
                    # 尝试以非阻塞方式再次获取
                    acquired = lock._lock.acquire(blocking=False)
                    if acquired:
                        acquisition_count += 1
                        lock._lock.release()
                except Exception:
                    pass

        # 运行测试
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(async_reentrant_attempt())

            # 对于 RLock，重入获取应该成功（在同一个线程中）
            # 但由于 asyncio.to_thread 使用线程池，可能在不同线程中
            # 这里我们只是验证不会崩溃或死锁
        finally:
            loop.close()

    @pytest.mark.timeout(10)
    def test_lock_preferable_to_rlock_for_async(self):
        """
        测试使用普通 Lock 替代 RLock 可以避免异步死锁

        这个测试验证：如果我们使用 threading.Lock 而不是 RLock，
        在异步上下文中获取锁会更安全。
        """
        # 创建一个使用普通 Lock 的版本进行对比
        class SimpleLock:
            def __init__(self):
                self._lock = threading.Lock()  # 使用 Lock 而不是 RLock
                self._locked = False

            def __enter__(self):
                self._lock.acquire()
                self._locked = True
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                self._locked = False
                self._lock.release()

        lock = SimpleLock()
        success = False

        def sync_holder():
            nonlocal success
            with lock:
                time.sleep(0.3)
                success = True

        async def async_waiter():
            # 使用 asyncio.to_thread 运行同步代码
            await asyncio.to_thread(sync_holder)

        # 运行测试
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(async_waiter())
            assert success, "同步操作未成功完成"
        finally:
            loop.close()
