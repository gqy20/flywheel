"""测试线程安全问题 - Issue #666

验证代码正确使用锁：
- threading.Lock 用于同步操作
- asyncio.Lock 用于异步操作
"""
import asyncio
import threading
import pytest
from flywheel.storage import FileStorage
import tempfile
import os


class TestThreadLockIssue666:
    """测试 Issue #666 - 验证锁的正确使用"""

    def test_has_both_locks(self):
        """验证同时存在同步锁和异步锁"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = os.path.join(tmpdir, "test.json")
            storage = FileStorage(storage_path)

            # 验证 _lock 是 threading.Lock（用于同步操作）
            assert hasattr(storage, '_lock'), "应该有 _lock 属性"
            assert isinstance(storage._lock, threading.Lock), \
                "self._lock 应该是 threading.Lock 实例"

            # 验证 _async_lock 是 asyncio.Lock（用于异步操作）
            assert hasattr(storage, '_async_lock'), "应该有 _async_lock 属性"
            assert isinstance(storage._async_lock, asyncio.Lock), \
                "self._async_lock 应该是 asyncio.Lock 实例"

    def test_async_lock_supports_async_with(self):
        """验证 _async_lock 支持 async with"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = os.path.join(tmpdir, "test.json")
            storage = FileStorage(storage_path)

            # asyncio.Lock 应该有 __aenter__ 和 __aexit__
            assert hasattr(storage._async_lock, '__aenter__'), \
                "asyncio.Lock 应该有 __aenter__ 方法（支持 async with）"
            assert hasattr(storage._async_lock, '__aexit__'), \
                "asyncio.Lock 应该有 __aexit__ 方法（支持 async with）"

    def test_async_with_async_lock_works(self):
        """验证 async with _async_lock 可以正常工作"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = os.path.join(tmpdir, "test.json")
            storage = FileStorage(storage_path)

            # 尝试使用 async with self._async_lock 应该正常工作
            async def try_async_with_lock():
                async with storage._async_lock:
                    # 这个代码块被锁保护
                    assert True

            # 应该没有异常
            asyncio.run(try_async_with_lock())

    def test_sync_with_lock_works(self):
        """验证 with _lock 可以正常工作"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = os.path.join(tmpdir, "test.json")
            storage = FileStorage(storage_path)

            # 同步 with 语句应该正常工作
            with storage._lock:
                # 这个代码块被锁保护
                assert True

    def test_concurrent_async_operations_thread_safe(self):
        """测试异步并发操作时的线程安全"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = os.path.join(tmpdir, "test.json")
            storage = FileStorage(storage_path)

            results = []
            errors = []

            async def concurrent_add(task_id):
                """并发添加任务的函数"""
                try:
                    # 使用异步锁保护操作
                    async with storage._async_lock:
                        # 模拟一些操作
                        storage._todos.append({"id": task_id})
                        results.append(task_id)
                        # 模拟一些处理时间
                        await asyncio.sleep(0.01)
                except Exception as e:
                    errors.append(e)

            async def run_concurrent():
                """运行多个并发任务"""
                tasks = [concurrent_add(i) for i in range(10)]
                await asyncio.gather(*tasks)

            # 运行并发任务
            asyncio.run(run_concurrent())

            # 验证没有错误
            assert len(errors) == 0, f"并发操作出现错误: {errors}"
            assert len(results) == 10, f"应该有10个结果，实际: {len(results)}"
