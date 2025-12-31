"""测试 Windows 权限回退机制 (Issue #214).

这个测试验证在 Windows 系统上（os.fchmod 不可用时），
临时文件的权限也能被正确设置为 0o600。
"""

import json
import os
import tempfile
import unittest.mock as mock
from pathlib import Path

import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


@pytest.fixture
def temp_storage(tmp_path):
    """创建临时存储实例用于测试."""
    storage_path = tmp_path / "test_issue_214.json"
    storage = Storage(str(storage_path))
    yield storage
    # 清理
    if storage_path.exists():
        storage_path.unlink()


def test_windows_fchmod_fallback(temp_storage, tmp_path):
    """测试 Windows 上 fchmod 不可用时的权限回退机制.

    场景：
    1. 模拟 os.fchmod 不可用（Windows 环境）
    2. 添加一个 todo
    3. 验证临时文件的权限设置为 0o600

    期望：
    - 即使 os.fchmod 不可用，也应该使用 os.chmod 回退方案
    - 临时文件应该具有 0o600 权限（所有者读写）
    """
    # 创建一个 todo 用于测试
    test_todo = Todo(id=1, title="Test Windows permission fallback")

    # 模拟 os.fchmod 不可用（Windows 环境）
    # 同时跟踪是否调用了 os.chmod
    with mock.patch('os.fchmod', side_effect=AttributeError("os.fchmod not available")) as mock_fchmod:
        with mock.patch('os.chmod') as mock_chmod:
            # 添加 todo，触发 _save 操作
            temp_storage.add(test_todo)

            # 验证 fchmod 确实被调用并失败
            assert mock_fchmod.called

            # 验证 os.chmod 被调用作为回退方案
            assert mock_chmod.called, "os.chmod 应该被调用作为 Windows 上的回退方案"

            # 验证 chmod 被调用时使用了正确的权限 (0o600)
            call_args = mock_chmod.call_args
            assert call_args is not None
            # call_args[0][1] 是第二个参数（权限）
            assert call_args[0][1] == 0o600, f"权限应该是 0o600，但得到了 {oct(call_args[0][1])}"


def test_windows_permission_actual_file(tmp_path):
    """测试在模拟 Windows 环境下实际文件的权限.

    这个测试创建一个实际的临时文件，验证 chmod 回退机制
    在真实文件系统上是否正确工作。
    """
    storage_path = tmp_path / "test_windows_actual.json"

    # 模拟 Windows 环境
    original_fchmod = os.fchmod if hasattr(os, 'fchmod') else None

    def fchmod_side_effect(fd, mode):
        """模拟 fchmod 不可用."""
        raise AttributeError("os.fchmod not available")

    with mock.patch('os.fchmod', side_effect=fchmod_side_effect):
        storage = Storage(str(storage_path))

        # 添加一个 todo
        test_todo = Todo(id=1, title="Test actual file permissions")
        storage.add(test_todo)

        # 验证文件已创建
        assert storage_path.exists()

        # 在非 Windows 系统上，我们可以验证权限
        # 在 Windows 上，chmod 不起作用，所以我们只验证代码执行不出错
        if os.name != 'nt':
            # 获取文件权限
            file_stat = os.stat(storage_path)
            file_mode = file_stat.st_mode & 0o777

            # 验证权限是 0o600
            assert file_mode == 0o600, f"文件权限应该是 0o600，但得到了 {oct(file_mode)}"


def test_tempfile_created_with_restrictive_permissions(tmp_path):
    """测试临时文件在创建后被赋予限制性权限.

    这个测试模拟了一个宽松的 umask（例如 0o022），
    验证即使在这种情况下，临时文件也会被赋予 0o600 权限。
    """
    storage_path = tmp_path / "test_restrictive_perms.json"

    # 保存原始 umask
    original_umask = os.umask(0o022)  # 设置宽松的 umask

    try:
        # 模拟 Windows 环境（fchmod 不可用）
        with mock.patch('os.fchmod', side_effect=AttributeError):
            storage = Storage(str(storage_path))

            # 添加一个 todo
            test_todo = Todo(id=1, title="Test restrictive permissions")
            storage.add(test_todo)

            # 在非 Windows 系统上验证权限
            if os.name != 'nt':
                file_stat = os.stat(storage_path)
                file_mode = file_stat.st_mode & 0o777

                # 文件应该有 0o600 权限，而不是继承 umask 的 0o644
                assert file_mode == 0o600, f"即使 umask 是 0o022，文件权限应该是 0o600，但得到了 {oct(file_mode)}"
    finally:
        # 恢复原始 umask
        os.umask(original_umask)
