"""验证 Issue #1434 - 确认上下文管理器方法完整存在

Issue #1434 报告说代码片段在类定义中间截断，`__exit__` 方法的文档字符串
和实现不完整，且缺少 `__aenter__` 和 `__aexit__` 的实现。

本测试验证所有方法都完整存在且可以正常工作。
"""

import asyncio
import inspect
from unittest.mock import Mock, patch

import pytest

from flywheel.storage import FileStorage


class TestIssue1434:
    """验证 Issue #1434 - 上下文管理器方法完整性"""

    def test_async_compatible_lock_has_exit(self):
        """验证 _AsyncCompatibleLock 有完整的 __exit__ 方法"""
        storage = FileStorage()

        # 检查 __exit__ 方法存在
        assert hasattr(storage._lock, "__exit__"), "_AsyncCompatibleLock 应该有 __exit__ 方法"

        # 检查 __exit__ 方法是可调用的
        assert callable(storage._lock.__exit__), "__exit__ 应该是可调用的"

        # 检查方法签名 (exc_type, exc_val, exc_tb)
        sig = inspect.signature(storage._lock.__exit__)
        params = list(sig.parameters.keys())
        assert params == ["exc_type", "exc_val", "exc_tb"], f"__exit__ 参数应该是 ['exc_type', 'exc_val', 'exc_tb'], 实际是 {params}"

        # 检查文档字符串存在且不是空的
        assert storage._lock.__exit__.__doc__ is not None, "__exit__ 应该有文档字符串"
        doc = storage._lock.__exit__.__doc__.strip()
        assert len(doc) > 0, "__exit__ 文档字符串不应该是空的"
        # 检查文档字符串包含关键内容
        assert "Release lock" in doc or "release lock" in doc, "文档字符串应该提到释放锁"

    def test_async_compatible_lock_has_aenter(self):
        """验证 _AsyncCompatibleLock 有完整的 __aenter__ 方法"""
        storage = FileStorage()

        # 检查 __aenter__ 方法存在
        assert hasattr(storage._lock, "__aenter__"), "_AsyncCompatibleLock 应该有 __aenter__ 方法"

        # 检查 __aenter__ 方法是可调用的
        assert callable(storage._lock.__aenter__), "__aenter__ 应该是可调用的"

        # 检查方法是协程函数
        assert inspect.iscoroutinefunction(storage._lock.__aenter__), "__aenter__ 应该是协程函数"

        # 检查文档字符串存在且不是空的
        assert storage._lock.__aenter__.__doc__ is not None, "__aenter__ 应该有文档字符串"
        doc = storage._lock.__aenter__.__doc__.strip()
        assert len(doc) > 0, "__aenter__ 文档字符串不应该是空的"
        # 检查文档字符串包含关键内容
        assert "Support asynchronous" in doc or "async context" in doc.lower(), "文档字符串应该提到异步上下文"

    def test_async_compatible_lock_has_aexit(self):
        """验证 _AsyncCompatibleLock 有完整的 __aexit__ 方法"""
        storage = FileStorage()

        # 检查 __aexit__ 方法存在
        assert hasattr(storage._lock, "__aexit__"), "_AsyncCompatibleLock 应该有 __aexit__ 方法"

        # 检查 __aexit__ 方法是可调用的
        assert callable(storage._lock.__aexit__), "__aexit__ 应该是可调用的"

        # 检查方法是协程函数
        assert inspect.iscoroutinefunction(storage._lock.__aexit__), "__aexit__ 应该是协程函数"

        # 检查文档字符串存在且不是空的
        assert storage._lock.__aexit__.__doc__ is not None, "__aexit__ 应该有文档字符串"
        doc = storage._lock.__aexit__.__doc__.strip()
        assert len(doc) > 0, "__aexit__ 文档字符串不应该是空的"
        # 检查文档字符串包含关键内容
        assert "Release lock" in doc or "release lock" in doc, "文档字符串应该提到释放锁"

    def test_sync_context_manager_works(self):
        """验证同步上下文管理器可以正常工作"""
        storage = FileStorage()

        # 使用 with 语句应该能正常工作
        try:
            with storage._lock:
                # 在锁保护下执行操作
                pass
            # 如果能正常执行，说明 __enter__ 和 __exit__ 都工作正常
            assert True
        except Exception as e:
            pytest.fail(f"同步上下文管理器失败: {e}")

    @pytest.mark.asyncio
    async def test_async_context_manager_works(self):
        """验证异步上下文管理器可以正常工作"""
        storage = FileStorage()

        # 使用 async with 语句应该能正常工作
        try:
            async with storage._lock:
                # 在锁保护下执行操作
                pass
            # 如果能正常执行，说明 __aenter__ 和 __aexit__ 都工作正常
            assert True
        except Exception as e:
            pytest.fail(f"异步上下文管理器失败: {e}")

    def test_exit_method_implementation_complete(self):
        """验证 __exit__ 方法的实现是完整的"""
        storage = FileStorage()

        # 获取 __exit__ 方法的源代码
        source = inspect.getsource(storage._lock.__exit__)

        # 验证源代码包含关键的实现元素
        assert "return False" in source or "return" in source, "__exit__ 应该有返回语句"
        assert "release" in source.lower() or "set()" in source, "__exit__ 应该包含释放锁或设置事件的代码"

    @pytest.mark.asyncio
    async def test_aexit_method_implementation_complete(self):
        """验证 __aexit__ 方法的实现是完整的"""
        storage = FileStorage()

        # 获取 __aexit__ 方法的源代码
        source = inspect.getsource(storage._lock.__aexit__)

        # 验证源代码包含关键的实现元素
        assert "return False" in source or "return" in source, "__aexit__ 应该有返回语句"
        assert "release" in source.lower() or "set()" in source, "__aexit__ 应该包含释放锁或设置事件的代码"
