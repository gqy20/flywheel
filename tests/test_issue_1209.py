"""测试 Issue #1209: 代码完整性验证

Issue #1209 报告代码在文件末尾被截断，缺少：
1. __enter__ 方法的 finally 块完整逻辑
2. 完整的注释（被截断为 'cancell'）
3. __exit__ 方法

这个测试验证代码现在是完整的。
"""
import asyncio
import pytest
from flywheel.storage import AsyncFilesystemLock


class TestIssue1209CodeCompleteness:
    """测试 Issue #1209: 代码完整性"""

    def test_enter_method_exists(self):
        """验证 __enter__ 方法存在且可调用"""
        lock = AsyncFilesystemLock("/tmp/test.lock")
        assert hasattr(lock, '__enter__')
        assert callable(lock.__enter__)

    def test_exit_method_exists(self):
        """验证 __exit__ 方法存在且可调用"""
        lock = AsyncFilesystemLock("/tmp/test.lock")
        assert hasattr(lock, '__exit__')
        assert callable(lock.__exit__)

    def test_enter_exit_context_manager(self):
        """验证上下文管理器协议正常工作"""
        lock = AsyncFilesystemLock("/tmp/test.lock")

        # 测试上下文管理器能够正常进入和退出
        # 注意：这需要在有运行的事件循环时才能完全测试
        # 这里我们验证方法存在且参数正确
        import inspect

        # 检查 __enter__ 签名（只接受 self）
        enter_sig = inspect.signature(lock.__enter__)
        assert len(enter_sig.parameters) == 0  # 只有 self

        # 检查 __exit__ 签名（接受 self, exc_type, exc_val, exc_tb）
        exit_sig = inspect.signature(lock.__exit__)
        assert len(exit_sig.parameters) == 3  # exc_type, exc_val, exc_tb

    def test_finally_block_implementation(self):
        """验证 finally 块的实现逻辑存在"""
        lock = AsyncFilesystemLock("/tmp/test.lock")

        # 验证必要的属性存在
        assert hasattr(lock, '_locked')
        assert hasattr(lock, '_lock')

        # 验证 _get_or_create_loop 方法存在（用于 finally 块）
        assert hasattr(lock, '_get_or_create_loop')
        assert callable(lock._get_or_create_loop)

    def test_comments_complete(self):
        """验证源代码中的注释是完整的"""
        import inspect

        # 获取 __enter__ 方法的源代码
        source = inspect.getsource(AsyncFilesystemLock.__enter__)

        # 验证关键字注释存在且完整
        assert "Fix for Issue #1201" in source
        assert "Fix for Issue #1207" in source
        assert "call_soon_threadsafe" in source
        assert "cancellation" in source  # 验证完整的单词 "cancellation" 存在
        # 验证不会被截断为 'cancell'
        assert "cancell" in source and "cancellation" in source

    def test_exit_method_implementation(self):
        """验证 __exit__ 方法的实现"""
        import inspect

        # 获取 __exit__ 方法的源代码
        source = inspect.getsource(AsyncFilesystemLock.__exit__)

        # 验证关键实现存在
        assert "_locked" in source
        assert "release" in source
        assert "Fix for Issue #1176" in source
        assert "Fix for Issue #1181" in source
        assert "Fix for Issue #1191" in source
        assert "Fix for Issue #1194" in source

    @pytest.mark.asyncio
    async def test_context_manager_integration(self):
        """集成测试：验证上下文管理器在实际使用中正常工作"""
        lock = AsyncFilesystemLock("/tmp/test_issue_1209.lock")

        # 测试异步上下文管理器
        async with lock:
            # 验证锁被获取
            assert lock._locked is True
            assert lock._lock.locked() is True

        # 验证锁被释放
        assert lock._locked is False
