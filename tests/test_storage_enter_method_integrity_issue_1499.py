"""
测试 __enter__ 方法的完整性 (Issue #1499)

验证 AI 扫描器报告的代码截断问题实际上是误报。
测试验证：
1. __enter__ 方法包含所有必要的常量定义 (MAX_RETRIES, BASE_DELAY, MAX_DELAY)
2. 包含完整的重试循环逻辑
3. 包含锁获取逻辑 (self._lock.acquire())
4. 包含 return self 语句
5. 包含指数退避机制
"""

import pytest
import time
import threading
from pathlib import Path

from flywheel.storage import FileStorage, StorageTimeoutError


class TestEnterMethodIntegrity:
    """测试 __enter__ 方法的完整性"""

    def test_enter_has_all_constants(self):
        """验证 __enter__ 方法包含所有必要的常量"""
        storage = FileStorage()

        # 检查 __enter__ 方法的源代码是否包含所有必要的常量
        import inspect
        source = inspect.getsource(storage.__enter__)

        assert 'MAX_RETRIES = 3' in source, "缺少 MAX_RETRIES 常量定义"
        assert 'BASE_DELAY = 0.0' in source, "缺少 BASE_DELAY 常量定义"
        assert 'MAX_DELAY = 0.1' in source, "缺少 MAX_DELAY 常量定义"

    def test_enter_has_retry_loop(self):
        """验证 __enter__ 方法包含重试循环"""
        storage = FileStorage()

        import inspect
        source = inspect.getsource(storage.__enter__)

        assert 'for attempt in range(MAX_RETRIES):' in source, "缺少重试循环"
        assert 'self._lock.acquire(timeout=' in source, "缺少锁获取逻辑"

    def test_enter_has_return_self(self):
        """验证 __enter__ 方法包含 return self 语句"""
        storage = FileStorage()

        import inspect
        source = inspect.getsource(storage.__enter__)

        assert 'return self' in source, "缺少 return self 语句"

    def test_enter_has_exponential_backoff(self):
        """验证 __enter__ 方法包含指数退避机制"""
        storage = FileStorage()

        import inspect
        source = inspect.getsource(storage.__enter__)

        assert 'exponential backoff' in source.lower() or 'backoff' in source.lower(), \
            "缺少指数退避注释或文档"
        assert '2 ** attempt' in source, "缺少指数退避计算逻辑"
        assert 'time.sleep(' in source, "缺少延迟逻辑"

    def test_enter_functional_basic(self):
        """功能测试：验证 __enter__ 方法正常工作"""
        storage = FileStorage()

        # 测试基本功能
        with storage as s:
            assert s is storage, "__enter__ 应该返回 self"

    def test_enter_returns_self(self):
        """验证 __enter__ 返回 storage 实例本身"""
        storage = FileStorage()

        result = storage.__enter__()
        assert result is storage, "__enter__ 应该返回 storage 实例本身"

        # 清理
        storage.__exit__(None, None, None)

    def test_enter_lock_timeout_with_retry(self):
        """测试锁超时后的重试机制（指数退避）"""
        storage = FileStorage(lock_timeout=0.1)  # 100ms 超时

        # 在另一个线程中获取锁
        lock_acquired = threading.Event()
        lock_released = threading.Event()

        def hold_lock():
            with storage._lock:
                lock_acquired.set()
                # 持有锁足够长的时间，导致主线程的第一次尝试超时
                time.sleep(0.3)

        thread = threading.Thread(target=hold_lock)
        thread.start()

        # 等待另一个线程获取锁
        lock_acquired.wait(timeout=1.0)

        try:
            # 尝试进入上下文 - 应该重试多次（最多 3 次）
            # 第一次尝试会超时，然后应该指数退避重试
            start_time = time.time()

            with pytest.raises(StorageTimeoutError) as exc_info:
                with storage:
                    pass

            elapsed = time.time() - start_time

            # 验证：
            # 1. 抛出了正确的异常类型
            assert isinstance(exc_info.value, StorageTimeoutError)

            # 2. 错误消息包含重试信息
            error_msg = str(exc_info.value)
            assert "after 3 attempts" in error_msg, "错误消息应包含重试次数"
            assert "MAX_RETRIES" not in error_msg, "错误消息不应包含常量名称"

            # 3. 总耗时应该超过单次超时时间（因为重试了多次）
            # 最少：0.1s (第一次超时) + 退避延迟
            assert elapsed >= 0.1, f"总耗时 {elapsed}s 应该超过单次超时时间 0.1s"

        finally:
            thread.join(timeout=2.0)

    def test_enter_successful_on_first_try(self):
        """测试在没有竞争时，第一次尝试就成功获取锁"""
        storage = FileStorage(lock_timeout=1.0)

        start_time = time.time()

        with storage:
            elapsed = time.time() - start_time
            # 应该立即成功，不应该有明显延迟
            assert elapsed < 0.1, f"无竞争时获取锁应该很快，实际耗时 {elapsed}s"

    def test_retry_with_exponential_backoff_timing(self):
        """测试指数退避的时间间隔是否正确"""
        storage = FileStorage(lock_timeout=0.05)  # 50ms 超时

        # 在另一个线程中持有锁
        def hold_lock():
            with storage._lock:
                time.sleep(0.5)  # 持有锁足够长，确保所有重试都超时

        thread = threading.Thread(target=hold_lock)
        thread.start()

        # 等待锁被获取
        time.sleep(0.01)

        try:
            start_time = time.time()

            with pytest.raises(StorageTimeoutError):
                with storage:
                    pass

            elapsed = time.time() - start_time

            # 验证总时间：
            # - 第一次尝试：0.05s 超时
            # - 第一次退避：random.uniform(0, 0.1 * 2^0) = random.uniform(0, 0.1)
            # - 第二次尝试：0.05s 超时
            # - 第二次退避：random.uniform(0, 0.1 * 2^1) = random.uniform(0, 0.2)
            # - 第三次尝试：0.05s 超时
            # - 然后抛出异常
            # 最少：0.05 * 3 = 0.15s（三次超时）
            # 最多：0.05 * 3 + 0.1 + 0.2 = 0.45s
            assert 0.15 <= elapsed <= 0.6, \
                f"总耗时 {elapsed:.3f}s 应该在合理范围内（考虑指数退避）"

        finally:
            thread.join(timeout=2.0)
