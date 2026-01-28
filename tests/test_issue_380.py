"""测试 Issue #380 - 验证 _release_file_lock 方法完整性

这个测试验证：
1. _release_file_lock 方法存在且完整
2. 方法包含正确的解锁逻辑（Windows 和 Unix）
3. 文件锁可以正确获取和释放
"""

import os
import tempfile
from pathlib import Path

import pytest

from flywheel.storage import Storage


class TestReleaseFileLockCompleteness:
    """测试 _release_file_lock 方法的完整性。"""

    def test_release_file_lock_method_exists(self):
        """验证 _release_file_lock 方法存在。"""
        storage = Storage()
        assert hasattr(storage, '_release_file_lock')
        assert callable(storage._release_file_lock)

    def test_release_file_lock_has_windows_logic(self):
        """验证 _release_file_lock 包含 Windows 解锁逻辑。"""
        import inspect
        storage = Storage()

        # 获取方法源代码
        source = inspect.getsource(storage._release_file_lock)

        # 验证包含 Windows 解锁的关键代码
        if os.name == 'nt':
            assert 'msvcrt.locking' in source
            assert 'LK_UNLCK' in source
            assert 'file_handle.seek(0)' in source
        else:
            # Unix 系统不需要 Windows 特定的代码
            pass

    def test_release_file_lock_has_unix_logic(self):
        """验证 _release_file_lock 包含 Unix 解锁逻辑。"""
        import inspect
        storage = Storage()

        # 获取方法源代码
        source = inspect.getsource(storage._release_file_lock)

        # 验证包含 Unix 解锁的关键代码
        if os.name != 'nt':
            assert 'fcntl.flock' in source
            assert 'LOCK_UN' in source
        else:
            # Windows 系统不需要 Unix 特定的代码
            pass

    def test_acquire_and_release_file_lock(self):
        """验证文件锁可以正确获取和释放。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test_lock.txt"
            test_file.write_text("test content")

            storage = Storage()

            # 测试获取和释放锁
            with test_file.open('r') as f:
                # 获取锁
                storage._acquire_file_lock(f)

                # 验证锁已缓存
                if os.name == 'nt':
                    assert storage._lock_range > 0
                else:
                    assert storage._lock_range == 0

                # 释放锁
                storage._release_file_lock(f)

                # 验证可以再次获取锁（证明锁已释放）
                storage._acquire_file_lock(f)
                storage._release_file_lock(f)

    def test_lock_range_cached_consistently(self):
        """验证锁范围在获取和释放时是一致的。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test_consistency.txt"
            test_file.write_text("test content for lock range")

            storage = Storage()

            with test_file.open('r') as f:
                # 获取锁
                storage._acquire_file_lock(f)
                lock_range_acquire = storage._lock_range

                # 释放锁
                storage._release_file_lock(f)

                # 再次获取锁并验证范围一致
                storage._acquire_file_lock(f)
                lock_range_second = storage._lock_range

                # 两次获取的锁范围应该相同
                assert lock_range_acquire == lock_range_second

                # 清理
                storage._release_file_lock(f)

    def test_release_file_lock_docstring_complete(self):
        """验证 _release_file_lock 方法的文档字符串是完整的。"""
        import inspect
        storage = Storage()

        # 获取文档字符串
        docstring = storage._release_file_lock.__doc__

        # 验证文档字符串存在且完整
        assert docstring is not None
        assert 'Release a file lock' in docstring
        assert 'Args:' in docstring
        assert 'Raises:' in docstring
        assert 'Note:' in docstring

        # 验证包含相关的 issue 引用（说明文档是完整的）
        assert 'Issue #268' in docstring  # Multi-process safety
        assert 'Issue #271' in docstring or 'Issue #351' in docstring  # Lock range

    def test_method_signature_correct(self):
        """验证 _release_file_lock 方法签名正确。"""
        import inspect
        storage = Storage()

        # 获取方法签名
        sig = inspect.signature(storage._release_file_lock)
        params = list(sig.parameters.keys())

        # 验证参数
        assert params == ['file_handle']
        assert sig.return_annotation == None.__class__  # NoneType

    def test_release_without_acquire_raises_error(self):
        """验证未获取锁就释放会抛出错误（锁范围验证）。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test_error.txt"
            test_file.write_text("test")

            storage = Storage()

            # 重置锁范围（模拟未获取锁的状态）
            storage._lock_range = -1

            with test_file.open('r') as f:
                # 在 Windows 上，这应该抛出 RuntimeError
                # 在 Unix 上，fcntl.flock 不使用锁范围，所以可能不会失败
                if os.name == 'nt':
                    with pytest.raises(RuntimeError, match="Invalid lock range"):
                        storage._release_file_lock(f)
                else:
                    # Unix 系统允许释放（flock 是引用计数）
                    storage._release_file_lock(f)
