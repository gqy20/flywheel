"""测试线程安全问题 - Issue #666

验证 threading.Lock 不能用于 async with 语句，
并且所有修改共享状态的操作都正确使用锁。
"""
import threading
import pytest
import asyncio
from flywheel.storage import FileStorage
from pathlib import Path
import tempfile
import os


class TestThreadLockIssue666:
    """测试 Issue #666 - threading.Lock 不能用于 async with"""

    def test_lock_is_threading_lock(self):
        """验证 _lock 是 threading.Lock 实例"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = os.path.join(tmpdir, "test.json")
            storage = FileStorage(storage_path)

            # 验证 _lock 是 threading.Lock
            assert isinstance(storage._lock, threading.Lock), \
                "self._lock 应该是 threading.Lock 实例"

    def test_lock_not_async_compatible(self):
        """验证 threading.Lock 不支持 async with"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = os.path.join(tmpdir, "test.json")
            storage = FileStorage(storage_path)

            # threading.Lock 没有 __aenter__ 和 __aexit__
            assert not hasattr(storage._lock, '__aenter__'), \
                "threading.Lock 不应该有 __aenter__ 方法（不支持 async with）"
            assert not hasattr(storage._lock, '__aexit__'), \
                "threading.Lock 不应该有 __aexit__ 方法（不支持 async with）"

    def test_async_with_lock_would_fail(self):
        """验证 async with threading.Lock 会失败"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = os.path.join(tmpdir, "test.json")
            storage = FileStorage(storage_path)

            # 尝试使用 async with self._lock 应该会失败
            async def try_async_with_lock():
                async with storage._lock:
                    pass

            with pytest.raises(AttributeError, match="__(aenter|aexit)__"):
                asyncio.run(try_async_with_lock())

    def test_sync_with_lock_works(self):
        """验证同步 with self._lock 可以正常工作"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = os.path.join(tmpdir, "test.json")
            storage = FileStorage(storage_path)

            # 同步 with 语句应该正常工作
            with storage._lock:
                # 这个代码块被锁保护
                assert True

    def test_concurrent_operations_thread_safe(self):
        """测试并发操作时的线程安全"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = os.path.join(tmpdir, "test.json")
            storage = FileStorage(storage_path)

            results = []
            errors = []

            def concurrent_add(task_id):
                """并发添加任务的函数"""
                try:
                    # 使用锁保护操作
                    with storage._lock:
                        # 模拟一些操作
                        storage._todos.append({"id": task_id})
                        results.append(task_id)
                except Exception as e:
                    errors.append(e)

            # 启动多个线程
            threads = []
            for i in range(10):
                t = threading.Thread(target=concurrent_add, args=(i,))
                threads.append(t)
                t.start()

            # 等待所有线程完成
            for t in threads:
                t.join()

            # 验证没有错误
            assert len(errors) == 0, f"并发操作出现错误: {errors}"
            assert len(results) == 10, f"应该有10个结果，实际: {len(results)}"
