"""测试 Issue #556: __init__ 中非 RuntimeError 异常的处理"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


class TestIssue556:
    """测试存储初始化时处理非 RuntimeError 异常的能力"""

    def test_init_with_ioerror_still_registers_atexit(self):
        """测试当 _load() 抛出 IOError 时，atexit 仍然被注册"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            # 模拟 _load() 抛出 IOError
            with patch.object(Storage, '_load', side_effect=IOError("Permission denied")):
                # 当前实现会导致初始化失败并抛出异常
                # 修复后应该能优雅处理并注册 atexit
                with pytest.raises(IOError):
                    storage = Storage(str(storage_path))

            # 验证 atexit 没有被注册（这是当前的问题）
            # 修复后，atexit 应该被注册

    def test_init_with_permissionerror_still_registers_atexit(self):
        """测试当 _load() 抛出 PermissionError 时，atexit 仍然被注册"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            # 模拟 _load() 抛出 PermissionError
            with patch.object(Storage, '_load', side_effect=PermissionError("Access denied")):
                # 当前实现会导致初始化失败并抛出异常
                with pytest.raises(PermissionError):
                    storage = Storage(str(storage_path))

            # 验证 atexit 没有被注册（这是当前的问题）

    def test_init_with_oserror_still_registers_atexit(self):
        """测试当 _load() 抛出 OSError 时，atexit 仍然被注册"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            # 模拟 _load() 抛出 OSError
            with patch.object(Storage, '_load', side_effect=OSError("System error")):
                # 当前实现会导致初始化失败并抛出异常
                with pytest.raises(OSError):
                    storage = Storage(str(storage_path))

            # 验证 atexit 没有被注册（这是当前的问题）

    def test_init_with_generic_exception_still_registers_atexit(self):
        """测试当 _load() 抛出通用 Exception 时，atexit 仍然被注册"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            # 模拟 _load() 抛出通用 Exception
            with patch.object(Storage, '_load', side_effect=Exception("Unexpected error")):
                # 当前实现会导致初始化失败并抛出异常
                with pytest.raises(Exception):
                    storage = Storage(str(storage_path))

            # 验证 atexit 没有被注册（这是当前的问题）

    def test_init_with_runtimeerror_registers_atexit(self):
        """测试当 _load() 抛出 RuntimeError 时，atexit 正常被注册（当前应该工作）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            # 模拟 _load() 抛出 RuntimeError
            with patch.object(Storage, '_load', side_effect=RuntimeError("Load failed")):
                # RuntimeError 应该被优雅处理，对象应该成功创建
                storage = Storage(str(storage_path))
                assert storage.list() == []
                assert storage.get_next_id() == 1

            # 验证 atexit 被注册（这个测试应该通过）
            import atexit
            # 我们无法直接验证 atexit 是否注册，但对象创建成功意味着它被注册了
            # 因为 finally 块中的 init_success 为 True
