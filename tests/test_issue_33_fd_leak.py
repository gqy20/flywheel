"""测试文件描述符泄漏修复 (Issue #33).

这个测试验证在写入失败时文件描述符是否会被正确关闭。
"""
import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_file_descriptor_closed_on_write_error():
    """测试写入失败时文件描述符是否正确关闭.

    这个测试模拟在 os.write 过程中发生异常，验证文件描述符
    是否会在 finally 块中被正确关闭，避免资源泄漏。
    """
    # 使用临时目录进行测试
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # 创建 Storage 实例并添加一个 todo
        storage = Storage(str(storage_path))
        storage.add(Todo(title="Test todo"))
        storage.close()

        # 获取当前进程的文件描述符数量
        initial_fd_count = len(os.listdir("/proc/self/fd"))

        # 模拟 os.write 失败的情况
        original_write = os.write
        call_count = [0]  # 使用列表来跟踪调用次数（可变对象）

        def mock_write(fd, data):
            """模拟写入失败."""
            call_count[0] += 1
            # 让第一次写入成功，第二次失败（模拟真实场景）
            if call_count[0] == 1:
                return original_write(fd, data)
            # 第二次调用时抛出异常
            raise OSError("Simulated write error")

        # 尝试保存数据，这会触发 mock_write 的异常
        storage2 = Storage(str(storage_path))
        with patch('os.write', side_effect=mock_write):
            with pytest.raises(OSError, match="Simulated write error"):
                storage2.add(Todo(title="Another todo"))

        # 验证文件描述符数量没有增加（没有泄漏）
        # 稍等一下让系统清理资源
        import gc
        gc.collect()

        final_fd_count = len(os.listdir("/proc/self/fd"))

        # 允许少量的 FD 差异（因为测试过程本身可能会打开/关闭一些文件）
        # 但不应该有持续增长的泄漏
        assert final_fd_count <= initial_fd_count + 3, \
            f"File descriptor leak detected: {final_fd_count - initial_fd_count} leaked"


def test_file_descriptor_closed_on_successful_write():
    """测试成功写入时文件描述符是否正确关闭.

    这个测试验证在正常情况下文件描述符是否会被正确关闭。
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # 获取初始文件描述符数量
        initial_fd_count = len(os.listdir("/proc/self/fd"))

        # 创建多个 Storage 实例并进行多次写入操作
        for i in range(10):
            storage = Storage(str(storage_path))
            storage.add(Todo(title=f"Todo {i}"))
            storage.close()

        # 验证文件描述符数量没有显著增加
        import gc
        gc.collect()

        final_fd_count = len(os.listdir("/proc/self/fd"))
        assert final_fd_count <= initial_fd_count + 5, \
            f"File descriptor leak detected: {final_fd_count - initial_fd_count} leaked"


def test_file_descriptor_closed_on_os_fchmod_failure():
    """测试 os.fchmod 失败时文件描述符是否正确关闭.

    这个测试验证在 os.fchmod 抛出 AttributeError 时（Windows 场景），
    文件描述符是否仍会被正确关闭。
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        initial_fd_count = len(os.listdir("/proc/self/fd"))

        # 模拟 os.fchmod 抛出 AttributeError（Windows 场景）
        storage = Storage(str(storage_path))
        with patch('os.fchmod', side_effect=AttributeError("fchmod not available")):
            # 即使 fchmod 失败，保存操作仍应成功，且 FD 应被正确关闭
            storage.add(Todo(title="Test todo"))
        storage.close()

        import gc
        gc.collect()

        final_fd_count = len(os.listdir("/proc/self/fd"))
        assert final_fd_count <= initial_fd_count + 3, \
            f"File descriptor leak detected after fchmod error: {final_fd_count - initial_fd_count} leaked"
